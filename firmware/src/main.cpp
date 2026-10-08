// Encore pendant firmware — XIAO ESP32-S3 Sense
// Capture PDM mic -> μ-law audio notifications over BLE to the iPhone; touch
// gestures; WS2812B ambiance LED driven by CMD_LED writes.
// Protocol: contracts/pendant_protocol.md (v2, BLE).
#include <Arduino.h>
#include <NimBLEDevice.h>
#include <driver/i2s.h>
#include <driver/touch_sensor.h>
#include <Adafruit_NeoPixel.h>

// ---------- protocol v2 ----------
static const char* SERVICE_UUID = "3cfbca53-0d19-4150-acd2-be1d3f437c06";
static const char* TX_UUID      = "a162065a-4a0f-4fe9-b1b6-eebf575e7b88";  // notify
static const char* RX_UUID      = "ea5ddf58-2e12-4cbe-934e-18d24a0a6cb4";  // write
static const int   PKT_SAMPLES  = 160;             // 10 ms of μ-law per AUDIO_ULAW packet
enum : uint8_t {
  MSG_EVENT = 0x02, MSG_HEARTBEAT = 0x03, MSG_AUDIO_ULAW = 0x04, MSG_CMD_LED = 0x10,
  EV_PIN = 1, EV_PRIVACY_ON = 2, EV_PRIVACY_OFF = 3,
  LED_OFF = 0, LED_SOLID = 1, LED_PULSE = 2, LED_FLASH_ONCE = 3,
};

// ---------- hardware ----------
static const int PDM_CLK = 42;                     // Sense on-board PDM mic
static const int PDM_DATA = 41;
static const int SAMPLE_RATE = 16000;
static const int FRAME_SAMPLES = 320;              // 20 ms per I2S read = 2 packets
static const int PIN_TOUCH = T1;                   // copper pad on GPIO1
static const int PIN_LED   = 2;                    // WS2812B data
static const int PIN_VBAT  = A2;                   // GPIO3/D2 — 2x220k divider from BAT+

// ---------- gestures ----------
#define TOUCH_DEBUG 0                              // 1 = print touch readings every 500 ms
#define PRIVACY_GESTURE 0                          // 0 = long press disabled: grabbing the
                                                   // pendant reads as a long press and kept
                                                   // muting the capture. Re-enable (=1) only
                                                   // if the privacy gesture returns to the demo.
static const uint32_t TAP_MAX_MS    = 350;
static const uint32_t DOUBLE_TAP_MS = 400;
static const uint32_t LONG_PRESS_MS = 1200;

Adafruit_NeoPixel led(1, PIN_LED, NEO_GRB + NEO_KHZ800);
NimBLEServer* bleServer = nullptr;
NimBLECharacteristic* txChar = nullptr;
volatile bool subscribed = false;                  // phone listens to TX = stream audio
uint16_t seq = 0;
bool privacyMode = false;
uint32_t sendOk = 0, sendBusy = 0, sendDropped = 0; // per-5s-window audio stats

// Audio packets wait here when the BLE stack is busy (notify() fails while its
// buffers are full) and are retried next loop instead of being lost.
// 24 packets = 240 ms of slack; on overflow the oldest packet is dropped.
static const int TXQ_LEN = 24;
uint8_t txq[TXQ_LEN][3 + PKT_SAMPLES];
int txqHead = 0, txqCount = 0;

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

// G.711 μ-law, bit-identical to pipeline/tools/pendant_codec.py (tested there).
uint8_t ulawEncode(int16_t pcm) {
  const int BIAS = 0x84, CLIP = 32635;
  int s = pcm;
  uint8_t sign = 0;
  if (s < 0) { sign = 0x80; s = -s; }
  if (s > CLIP) s = CLIP;
  s += BIAS;
  int exponent = 7;
  for (int mask = 0x4000; exponent > 0 && !(s & mask); mask >>= 1) exponent--;
  int mantissa = (s >> (exponent + 3)) & 0x0F;
  return ~(sign | (exponent << 4) | mantissa);
}

bool notify(const uint8_t* pkt, size_t len) {
  if (!subscribed) return false;
  return txChar->notify(pkt, len);
}

// Send queued audio in order until the stack says busy; the rest waits for the next loop.
void drainAudio() {
  if (!subscribed) { txqCount = 0; return; }       // nobody listening: stale audio is useless
  while (txqCount > 0) {
    if (!notify(txq[txqHead], sizeof(txq[0]))) { sendBusy++; return; }
    txqHead = (txqHead + 1) % TXQ_LEN; txqCount--; sendOk++;
  }
}

// One 20 ms I2S read -> two 10 ms AUDIO_ULAW packets (163 bytes, fits the MTU iOS negotiates).
void sendAudioFrame(const int16_t* pcm) {
  for (int half = 0; half < FRAME_SAMPLES / PKT_SAMPLES; half++) {
    if (txqCount == TXQ_LEN) {                     // queue full: drop the oldest
      txqHead = (txqHead + 1) % TXQ_LEN; txqCount--; sendDropped++;
    }
    uint8_t* pkt = txq[(txqHead + txqCount) % TXQ_LEN];
    txqCount++;
    pkt[0] = MSG_AUDIO_ULAW;
    memcpy(pkt + 1, &seq, 2); seq++;
    for (int i = 0; i < PKT_SAMPLES; i++) pkt[3 + i] = ulawEncode(pcm[half * PKT_SAMPLES + i]);
  }
  drainAudio();
}

void sendEvent(uint8_t code) {
  uint8_t pkt[6]; pkt[0] = MSG_EVENT;
  uint32_t ts = millis(); memcpy(pkt + 1, &ts, 4); pkt[5] = code;
  notify(pkt, sizeof(pkt));
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
  uint8_t pkt[3] = { MSG_HEARTBEAT, batteryPct(), 0 };   // rssi: the phone measures it
  notify(pkt, sizeof(pkt));
#if TOUCH_DEBUG
  Serial.printf("battery %u%% (%lu mV)\n", pkt[1], (unsigned long)batteryMilliVolts());
#endif
}

void startFlash(uint8_t r, uint8_t g, uint8_t b) {
  flashR = r; flashG = g; flashB = b;
  flashUntil = millis() + 300;
}

void setIdleLed() { ambMode = LED_PULSE; ambR = 0; ambG = 0; ambB = 40; }  // blue = waiting for the app

// ---------- BLE ----------
class ServerCallbacks : public NimBLEServerCallbacks {
  void onConnect(NimBLEServer* s, NimBLEConnInfo& info) override {
    // 15-30 ms interval, no latency, 4 s timeout: inside Apple's accessory rules.
    s->updateConnParams(info.getConnHandle(), 12, 24, 0, 400);
    Serial.printf("ble connected %s\n", info.getAddress().toString().c_str());
  }
  void onDisconnect(NimBLEServer* s, NimBLEConnInfo& info, int reason) override {
    subscribed = false;
    setIdleLed();
    Serial.printf("ble disconnected (reason %d), advertising\n", reason);  // NimBLE restarts it
  }
  void onMTUChange(uint16_t mtu, NimBLEConnInfo& info) override {
    Serial.printf("ble mtu %u\n", mtu);
  }
};

class TxCallbacks : public NimBLECharacteristicCallbacks {
  void onSubscribe(NimBLECharacteristic* c, NimBLEConnInfo& info, uint16_t subValue) override {
    subscribed = (subValue & 0x0001) != 0;         // bit 0 = notifications
    Serial.printf("ble %s\n", subscribed ? "subscribed, streaming" : "unsubscribed");
  }
};

class RxCallbacks : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic* c, NimBLEConnInfo& info) override {
    NimBLEAttValue v = c->getValue();
    const uint8_t* pkt = v.data();
    if (v.size() == 5 && pkt[0] == MSG_CMD_LED) {
      if (pkt[1] == LED_FLASH_ONCE) startFlash(pkt[2], pkt[3], pkt[4]);
      else { ambMode = pkt[1]; ambR = pkt[2]; ambG = pkt[3]; ambB = pkt[4]; }
    }
  }
};

void setupBle() {
  NimBLEDevice::init("Encore");
  NimBLEDevice::setMTU(247);
  bleServer = NimBLEDevice::createServer();
  bleServer->setCallbacks(new ServerCallbacks());
  NimBLEService* svc = bleServer->createService(SERVICE_UUID);
  txChar = svc->createCharacteristic(TX_UUID, NIMBLE_PROPERTY::NOTIFY);
  txChar->setCallbacks(new TxCallbacks());
  NimBLECharacteristic* rx = svc->createCharacteristic(
      RX_UUID, NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR);
  rx->setCallbacks(new RxCallbacks());
  svc->start();
  NimBLEAdvertising* adv = NimBLEDevice::getAdvertising();
  adv->addServiceUUID(SERVICE_UUID);
  adv->setName("Encore");
  adv->enableScanResponse(true);
  adv->start();
  Serial.println("ble advertising as \"Encore\"");
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
  // Slow baseline tracking: USB ground, surfaces and humidity shift the pad's
  // idle level and the boot-time baseline goes stale (phantom PIN storms).
  // Adapt ~1/256 of the gap per 20 ms loop (~5 s time constant), never while
  // pressed so real touches don't get absorbed.
  if (!pressed) touchBaseline += ((int32_t)raw - (int32_t)touchBaseline) / 256;
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
    longFired = true;                              // long grab must never count as a tap
#if PRIVACY_GESTURE
    if (privacyMode) { privacyMode = false; sendEvent(EV_PRIVACY_OFF); }
    else { sendEvent(EV_PRIVACY_ON); privacyMode = true; }
    Serial.printf("privacy %s\n", privacyMode ? "ON" : "OFF");
#endif
  }

  if (!pressed && down) {
    down = false;
    if (!longFired && now - downAt < TAP_MAX_MS) {
      if (now - lastTapAt <= DOUBLE_TAP_MS) {
        lastTapAt = 0;
        static uint32_t lastPinAt = 0;             // 3 s cooldown: one moment = one pin
        if (!privacyMode && now - lastPinAt >= 3000) {
          lastPinAt = now;
          sendEvent(EV_PIN);
          startFlash(255, 255, 255);               // instant local feedback
          Serial.println("PIN");
        }
      } else lastTapAt = now;
    }
  }
}

void setup() {
  Serial.begin(115200);
  led.begin();
  setupBle();
  micOk = setupMic();
  if (!micOk) Serial.println("running WITHOUT audio (touch/LED/heartbeat still up)");
  calibrateTouch();
  Serial.printf("touch baseline %lu\n", (unsigned long)touchBaseline);
  Serial.println("ready — double tap = PIN, long press = privacy toggle");
  setIdleLed();                                    // idle blue until the app takes over
}

void loop() {
  static int16_t pcm[FRAME_SAMPLES];
  static uint32_t lastHb = 0;

  size_t got = 0;
  if (micOk) i2s_read(I2S_NUM_0, pcm, sizeof(pcm), &got, portMAX_DELAY);  // paces the loop at 20 ms
  else delay(20);
  if (micOk && subscribed && !privacyMode && got == sizeof(pcm)) sendAudioFrame(pcm);
  else drainAudio();

  pollTouch();
  if (millis() - lastHb >= 5000) {
    lastHb = millis();
    sendHeartbeat();
    // Self-diagnosis: one status line per window beats catching the boot log.
    // ~500 ok per window while streaming. busy = stack full, packet kept and
    // retried (harmless); dropped = queue overflowed, audio really lost.
    Serial.printf("ble: %s ok=%lu busy=%lu dropped=%lu queued=%d\n",
                  subscribed ? "streaming" : "waiting", (unsigned long)sendOk,
                  (unsigned long)sendBusy, (unsigned long)sendDropped, txqCount);
    sendOk = sendBusy = sendDropped = 0;
  }
  renderLed();
}
