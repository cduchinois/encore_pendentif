// Encore pendant firmware — XIAO ESP32-S3 Sense
// Capture PDM mic -> UDP audio frames to the iPhone hotspot; touch gestures;
// WS2812B ambiance LED driven by CMD_LED. Protocol: contracts/pendant_protocol.md (v1).
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <driver/i2s.h>
#include <driver/touch_sensor.h>
#include <Adafruit_NeoPixel.h>

#if !__has_include("secrets.h")
#error "Create firmware/src/secrets.h from secrets.h.example (hotspot credentials)"
#endif
#include "secrets.h"

// ---------- protocol v1 ----------
#ifndef ENCORE_PHONE_IP                            // override in secrets.h to stream to a Mac for tests
#define ENCORE_PHONE_IP "172.20.10.1"              // iPhone hotspot gateway, always this IP
#endif
static const char*    PHONE_IP = ENCORE_PHONE_IP;
static const uint16_t PORT     = 7777;
enum : uint8_t {
  MSG_AUDIO = 0x01, MSG_EVENT = 0x02, MSG_HEARTBEAT = 0x03, MSG_CMD_LED = 0x10,
  EV_PIN = 1, EV_PRIVACY_ON = 2, EV_PRIVACY_OFF = 3,
  LED_OFF = 0, LED_SOLID = 1, LED_PULSE = 2, LED_FLASH_ONCE = 3,
};

// ---------- hardware ----------
static const int PDM_CLK = 42;                     // Sense on-board PDM mic
static const int PDM_DATA = 41;
static const int SAMPLE_RATE = 16000;
static const int FRAME_SAMPLES = 320;              // 20 ms
static const int PIN_TOUCH = T1;                   // copper pad on GPIO1
static const int PIN_LED   = 2;                    // WS2812B data
static const int PIN_VBAT  = A2;                   // GPIO3/D2 — 2x220k divider from BAT+

// ---------- gestures ----------
#define TOUCH_DEBUG 0                              // 1 = print touch readings every 500 ms
static const uint32_t TAP_MAX_MS    = 350;
static const uint32_t DOUBLE_TAP_MS = 400;
static const uint32_t LONG_PRESS_MS = 1200;

Adafruit_NeoPixel led(1, PIN_LED, NEO_GRB + NEO_KHZ800);
WiFiUDP udp;
uint16_t seq = 0;
bool privacyMode = false;

// ambiance state set by CMD_LED; flash overlays it briefly
uint8_t ambMode = LED_OFF, ambR = 0, ambG = 0, ambB = 0;
uint8_t flashR = 0, flashG = 0, flashB = 0;
uint32_t flashUntil = 0;

uint32_t touchBaseline = 0;                        // S3: touchRead rises when touched

bool micOk = false;

bool setupMic() {
  i2s_config_t cfg = {};
  cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX | I2S_MODE_PDM);
  cfg.sample_rate = SAMPLE_RATE;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
  cfg.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;
  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  cfg.dma_buf_count = 4; cfg.dma_buf_len = FRAME_SAMPLES;
  esp_err_t err = i2s_driver_install(I2S_NUM_0, &cfg, 0, nullptr);
  if (err != ESP_OK) { Serial.printf("MIC DEAD: i2s_driver_install err %d\n", err); return false; }
  i2s_pin_config_t pins = {};
  pins.mck_io_num = I2S_PIN_NO_CHANGE; pins.bck_io_num = I2S_PIN_NO_CHANGE;
  pins.ws_io_num = PDM_CLK; pins.data_in_num = PDM_DATA;
  pins.data_out_num = I2S_PIN_NO_CHANGE;
  err = i2s_set_pin(I2S_NUM_0, &pins);
  if (err != ESP_OK) { Serial.printf("MIC DEAD: i2s_set_pin err %d\n", err); return false; }
  return true;
}

void sendAudioFrame(int16_t* pcm) {
  uint8_t pkt[1 + 2 + 4 + FRAME_SAMPLES * 2];
  pkt[0] = MSG_AUDIO;
  memcpy(pkt + 1, &seq, 2); seq++;
  uint32_t ts = millis(); memcpy(pkt + 3, &ts, 4);
  memcpy(pkt + 7, pcm, FRAME_SAMPLES * 2);
  udp.beginPacket(PHONE_IP, PORT); udp.write(pkt, sizeof(pkt)); udp.endPacket();
}

void sendEvent(uint8_t code) {
  uint8_t pkt[6]; pkt[0] = MSG_EVENT;
  uint32_t ts = millis(); memcpy(pkt + 1, &ts, 4); pkt[5] = code;
  udp.beginPacket(PHONE_IP, PORT); udp.write(pkt, sizeof(pkt)); udp.endPacket();
}

uint32_t batteryMilliVolts() {
  uint32_t mv = 0;
  for (int i = 0; i < 8; i++) mv += analogReadMilliVolts(PIN_VBAT);
  return (mv / 8) * 2;                             // divider halves VBAT
}

uint8_t batteryPct() {
  uint32_t mv = batteryMilliVolts();
  if (mv < 2500) return 100;                       // divider not wired yet -> stub
  // LiPo curve approximated linearly: 4.2 V full, 3.3 V empty — plenty for a demo gauge
  long pct = ((long)mv - 3300) * 100 / (4200 - 3300);
  return (uint8_t)constrain(pct, 0, 100);
}

void sendHeartbeat() {
  uint8_t pkt[3] = { MSG_HEARTBEAT, batteryPct(), (uint8_t)(int8_t)WiFi.RSSI() };
  udp.beginPacket(PHONE_IP, PORT); udp.write(pkt, sizeof(pkt)); udp.endPacket();
#if TOUCH_DEBUG
  Serial.printf("battery %u%% (%lu mV)\n", pkt[1], (unsigned long)batteryMilliVolts());
#endif
}

void startFlash(uint8_t r, uint8_t g, uint8_t b) {
  flashR = r; flashG = g; flashB = b;
  flashUntil = millis() + 300;
}

void pollUdp() {
  int len = udp.parsePacket();
  if (len <= 0) return;
  uint8_t pkt[8];
  len = udp.read(pkt, sizeof(pkt));
  if (len == 5 && pkt[0] == MSG_CMD_LED) {
    if (pkt[1] == LED_FLASH_ONCE) startFlash(pkt[2], pkt[3], pkt[4]);
    else { ambMode = pkt[1]; ambR = pkt[2]; ambG = pkt[3]; ambB = pkt[4]; }
  }
}

void renderLed() {
  uint32_t now = millis();
  uint8_t r = 0, g = 0, b = 0;
  if (!privacyMode) {                              // privacy = LED off, unambiguous
    if (now < flashUntil) { r = flashR; g = flashG; b = flashB; }
    else if (ambMode == LED_SOLID) { r = ambR; g = ambG; b = ambB; }
    else if (ambMode == LED_PULSE) {
      float k = 0.5f + 0.5f * sinf(now * TWO_PI / 2000.0f);
      r = ambR * k; g = ambG * k; b = ambB * k;
    }
  }
  led.setPixelColor(0, led.Color(r, g, b));
  led.show();
}

void calibrateTouch() {
  uint64_t acc = 0;
  for (int i = 0; i < 32; i++) { acc += touchRead(PIN_TOUCH); delay(5); }
  touchBaseline = acc / 32;
}

void pollTouch() {
  static bool down = false; static bool longFired = false;
  static uint32_t downAt = 0, lastTapAt = 0;
  uint32_t now = millis();
  uint32_t raw = touchRead(PIN_TOUCH);
  // a live sensor always jitters; bit-identical reads for ~10 s = touch FSM stuck
  static uint32_t lastRaw = 0; static uint16_t sameCount = 0;
  if (raw == lastRaw) {
    if (++sameCount >= 500) {
      sameCount = 0;
      Serial.println("touch frozen — restarting touch FSM");
      touch_pad_fsm_stop(); touch_pad_fsm_start();
    }
  } else { lastRaw = raw; sameCount = 0; }
  bool pressed = raw > touchBaseline + (touchBaseline * 2) / 5;   // +40%, tuned on real pad
#if TOUCH_DEBUG
  static uint32_t lastDbg = 0;
  if (now - lastDbg >= 500) {
    lastDbg = now;
    Serial.printf("touch raw=%lu baseline=%lu threshold=%lu %s\n",
                  (unsigned long)raw, (unsigned long)touchBaseline,
                  (unsigned long)(touchBaseline + (touchBaseline * 2) / 5),
                  pressed ? "<== PRESSED" : "");
  }
#endif

  if (pressed && !down) { down = true; longFired = false; downAt = now; }

  if (pressed && down && !longFired && now - downAt >= LONG_PRESS_MS) {
    longFired = true;
    if (privacyMode) { privacyMode = false; sendEvent(EV_PRIVACY_OFF); }
    else { sendEvent(EV_PRIVACY_ON); privacyMode = true; }
    Serial.printf("privacy %s\n", privacyMode ? "ON" : "OFF");
  }

  if (!pressed && down) {
    down = false;
    if (!longFired && now - downAt < TAP_MAX_MS) {
      if (now - lastTapAt <= DOUBLE_TAP_MS) {
        lastTapAt = 0;
        if (!privacyMode) {
          sendEvent(EV_PIN);
          startFlash(255, 255, 255);               // instant local feedback
          Serial.println("PIN");
        }
      } else lastTapAt = now;
    }
  }
}

void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);                            // modem sleep causes UDP jitter
  WiFi.begin(ENCORE_WIFI_SSID, ENCORE_WIFI_PASS);
  Serial.printf("connecting to \"%s\"", ENCORE_WIFI_SSID);
  uint32_t start = millis();
  bool scanned = false;
  while (WiFi.status() != WL_CONNECTED) {
    if (!scanned && millis() - start > 15000) {
      scanned = true;
      Serial.println("\nstill not connected — 2.4 GHz networks I can actually see:");
      WiFi.disconnect();
      int n = WiFi.scanNetworks();
      for (int i = 0; i < n; i++)
        Serial.printf("  \"%s\" (%d dBm)\n", WiFi.SSID(i).c_str(), WiFi.RSSI(i));
      if (n <= 0) Serial.println("  (none — hotspot page closed, or 5 GHz only)");
      Serial.println("compare character-for-character with ENCORE_WIFI_SSID in secrets.h");
      WiFi.scanDelete();
      WiFi.begin(ENCORE_WIFI_SSID, ENCORE_WIFI_PASS);
      Serial.print("retrying");
    }
    // blue blink while connecting, red after 20 s (wrong creds / hotspot off / 5 GHz)
    bool late = millis() - start > 20000;
    led.setPixelColor(0, (millis() / 250) % 2 ? led.Color(late ? 60 : 0, 0, late ? 0 : 60) : 0);
    led.show();
    delay(200); Serial.print(".");
  }
  Serial.printf("\nwifi ok — pendant ip %s, rssi %d dBm\n",
                WiFi.localIP().toString().c_str(), WiFi.RSSI());
  Serial.printf("streaming AUDIO -> %s:%u (16 kHz mono, 20 ms frames)\n", PHONE_IP, PORT);
}

void setup() {
  Serial.begin(115200);
  led.begin();
  connectWifi();
  udp.begin(PORT);                                 // also our receive port for CMD_LED
  micOk = setupMic();
  if (!micOk) Serial.println("running WITHOUT audio (touch/LED/heartbeat still up)");
  calibrateTouch();
  Serial.printf("touch baseline %lu\n", (unsigned long)touchBaseline);
  Serial.println("ready — double tap = PIN, long press = privacy toggle");
  ambMode = LED_PULSE; ambR = 0; ambG = 0; ambB = 40; // idle blue until the app takes over
}

void loop() {
  static int16_t pcm[FRAME_SAMPLES];
  static uint32_t lastHb = 0;

  size_t got = 0;
  if (micOk) i2s_read(I2S_NUM_0, pcm, sizeof(pcm), &got, portMAX_DELAY);  // paces the loop at 20 ms
  else delay(20);
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("wifi lost, reconnecting");
    connectWifi();
  }
  if (micOk && !privacyMode && got == sizeof(pcm)) sendAudioFrame(pcm);

  pollTouch();
  pollUdp();
  if (millis() - lastHb >= 5000) { lastHb = millis(); sendHeartbeat(); }
  renderLed();
}
