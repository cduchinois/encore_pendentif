// Encore pendant firmware — XIAO ESP32-S3 Sense
// Capture PDM mic -> UDP audio frames; touch gestures; WS2812B ambiance LED.
// Protocol: see contracts/pendant_protocol.md (v1). Keep them in sync.
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <driver/i2s.h>
#include <Adafruit_NeoPixel.h>

// ---------- config ----------
static const char* WIFI_SSID = "encore-hotspot";   // iPhone hotspot
static const char* WIFI_PASS = "CHANGE_ME";
static const char* PHONE_IP  = "172.20.10.1";      // default iPhone hotspot gateway
static const uint16_t PORT   = 7777;

// XIAO ESP32-S3 Sense PDM mic
static const int PDM_CLK = 42;
static const int PDM_DATA = 41;
static const int SAMPLE_RATE = 16000;
static const int FRAME_SAMPLES = 320;              // 20 ms

static const int PIN_TOUCH = T1;                   // copper pad on GPIO1
static const int PIN_LED   = 2;                    // WS2812B data

Adafruit_NeoPixel led(1, PIN_LED, NEO_GRB + NEO_KHZ800);
WiFiUDP udp;
uint16_t seq = 0;
bool privacyMode = false;

void setupMic() {
  i2s_config_t cfg = {};
  cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX | I2S_MODE_PDM);
  cfg.sample_rate = SAMPLE_RATE;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
  cfg.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;
  cfg.dma_buf_count = 4; cfg.dma_buf_len = FRAME_SAMPLES;
  i2s_driver_install(I2S_NUM_0, &cfg, 0, nullptr);
  i2s_pin_config_t pins = {};
  pins.mck_io_num = I2S_PIN_NO_CHANGE; pins.bck_io_num = I2S_PIN_NO_CHANGE;
  pins.ws_io_num = PDM_CLK; pins.data_in_num = PDM_DATA;
  pins.data_out_num = I2S_PIN_NO_CHANGE;
  i2s_set_pin(I2S_NUM_0, &pins);
}

void sendAudioFrame(int16_t* pcm) {
  uint8_t pkt[1 + 2 + 4 + FRAME_SAMPLES * 2];
  pkt[0] = 0x01;
  memcpy(pkt + 1, &seq, 2); seq++;
  uint32_t ts = millis(); memcpy(pkt + 3, &ts, 4);
  memcpy(pkt + 7, pcm, FRAME_SAMPLES * 2);
  udp.beginPacket(PHONE_IP, PORT); udp.write(pkt, sizeof(pkt)); udp.endPacket();
}

void sendEvent(uint8_t code) {
  uint8_t pkt[6]; pkt[0] = 0x02;
  uint32_t ts = millis(); memcpy(pkt + 1, &ts, 4); pkt[5] = code;
  udp.beginPacket(PHONE_IP, PORT); udp.write(pkt, sizeof(pkt)); udp.endPacket();
}

// TODO(day-of): touch gesture detection (double tap window ~400 ms, long press > 1.2 s)
// TODO(day-of): handle CMD_LED (0x10) incoming packets -> ambiance color / pulse / pin flash
// TODO(day-of): HEARTBEAT every 5 s with battery estimate

void setup() {
  Serial.begin(115200);
  led.begin(); led.setPixelColor(0, led.Color(0, 0, 40)); led.show();
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(200); Serial.print("."); }
  Serial.printf("\nwifi ok %s\n", WiFi.localIP().toString().c_str());
  udp.begin(PORT);
  setupMic();
}

void loop() {
  static int16_t pcm[FRAME_SAMPLES];
  size_t got = 0;
  i2s_read(I2S_NUM_0, pcm, sizeof(pcm), &got, portMAX_DELAY);
  if (!privacyMode && got == sizeof(pcm)) sendAudioFrame(pcm);
  // touch + led handling: see TODOs
}
