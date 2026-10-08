//  PendantBLEClient.swift
//  Encore
//
//  CoreBluetooth central for pendant protocol v2 (contracts/pendant_protocol.md):
//  finds the "Encore" peripheral, subscribes to TX (μ-law audio, events,
//  heartbeats), writes CMD_LED to RX. Remembers the pendant and reconnects
//  on its own; state restoration keeps it alive in the background.
//  Delegate callbacks run on main (the project's default isolation); decoded
//  audio is handed off on a dedicated serial queue.

import Foundation
import Combine
import CoreBluetooth

enum PendantEvent: UInt8 {
    case pin = 1
    case privacyOn = 2
    case privacyOff = 3
}

enum LEDMode: UInt8 {
    case off = 0, solid = 1, pulse = 2, flashOnce = 3
}

final class PendantBLEClient: NSObject, ObservableObject, CBCentralManagerDelegate, CBPeripheralDelegate {
    static let serviceUUID = CBUUID(string: "3CFBCA53-0D19-4150-ACD2-BE1D3F437C06")
    static let txUUID = CBUUID(string: "A162065A-4A0F-4FE9-B1B6-EEBF575E7B88")
    static let rxUUID = CBUUID(string: "EA5DDF58-2E12-4CBE-934E-18D24A0A6CB4")
    static let packetSamples = 160   // 10 ms @ 16 kHz mono, μ-law
    static let audioPacketSize = 3 + packetSamples

    enum State {
        case off, unauthorized, scanning, connecting, connected
    }

    // Stats for the UI (main thread).
    @Published private(set) var state: State = .off
    @Published private(set) var pendantName: String? = nil
    @Published private(set) var framesPerSecond = 0
    @Published private(set) var lostFrames = 0
    @Published private(set) var batteryPct: Int = -1
    @Published private(set) var rssi: Int = 0
    @Published private(set) var lastPacketAt: Date? = nil
    @Published private(set) var rmsHistory: [Float] = []   // one value per 20 ms, last ~3 s

    /// Called on `audioQueue` with each 160-sample PCM frame.
    var onAudioFrame: (([Int16]) -> Void)?
    /// Called on the main thread.
    var onEvent: ((PendantEvent) -> Void)?
    /// Called on the main thread once TX notifications are flowing.
    var onReady: (() -> Void)?

    let audioQueue = DispatchQueue(label: "encore.pendant.audio")
    private var central: CBCentralManager?
    private var peripheral: CBPeripheral?
    private var rxChar: CBCharacteristic?
    private var lastSeq: UInt16? = nil
    private var framesThisSecond = 0
    private var rmsAcc: Float = 0
    private var rmsPackets = 0
    private var fpsTimer: Timer?

    private static let knownPendantKey = "pendant_peripheral_id"
    private static let restoreID = "encore.pendant.central"

    /// G.711 μ-law -> int16, bit-identical to pipeline/tools/pendant_codec.py.
    static let ulawTable: [Int16] = (0...255).map { i in
        let u = ~UInt8(i)
        var t = (Int(u & 0x0F) << 3) + 0x84
        t <<= Int((u & 0x70) >> 4)
        return Int16(u & 0x80 != 0 ? 0x84 - t : t - 0x84)
    }

    func start() {
        guard central == nil else { return }
        central = CBCentralManager(delegate: self, queue: nil,
                                   options: [CBCentralManagerOptionRestoreIdentifierKey: Self.restoreID])
        fpsTimer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            guard let self else { return }
            self.framesPerSecond = self.framesThisSecond
            self.framesThisSecond = 0
        }
    }

    /// Drop the remembered pendant and look for any Encore pendant again.
    func forget() {
        UserDefaults.standard.removeObject(forKey: Self.knownPendantKey)
        if let p = peripheral { central?.cancelPeripheralConnection(p) }
        peripheral = nil
        rxChar = nil
        pendantName = nil
        connectOrScan()
    }

    /// CMD_LED 0x10: mode + RGB, 5 bytes. flashOnce overlays the ambiance for 300 ms.
    /// Safe from any thread.
    func sendLED(_ mode: LEDMode, r: UInt8, g: UInt8, b: UInt8) {
        DispatchQueue.main.async {
            guard let p = self.peripheral, p.state == .connected, let rx = self.rxChar else { return }
            p.writeValue(Data([0x10, mode.rawValue, r, g, b]), for: rx, type: .withoutResponse)
        }
    }

    // MARK: Connection

    private func connectOrScan() {
        guard let central, central.state == .poweredOn else { return }
        if peripheral == nil,
           let s = UserDefaults.standard.string(forKey: Self.knownPendantKey),
           let id = UUID(uuidString: s) {
            peripheral = central.retrievePeripherals(withIdentifiers: [id]).first
        }
        if peripheral == nil {
            peripheral = central.retrieveConnectedPeripherals(withServices: [Self.serviceUUID]).first
        }
        guard let p = peripheral else {
            state = .scanning
            central.scanForPeripherals(withServices: [Self.serviceUUID], options: nil)
            return
        }
        p.delegate = self
        if p.state == .connected {
            didConnect(p)
        } else {
            // A pending connect never times out: it completes whenever the
            // pendant comes back in range, also while the app is backgrounded.
            state = .connecting
            central.connect(p, options: nil)
        }
    }

    private func didConnect(_ p: CBPeripheral) {
        UserDefaults.standard.set(p.identifier.uuidString, forKey: Self.knownPendantKey)
        state = .connected
        pendantName = p.name ?? "Encore"
        audioQueue.async { self.lastSeq = nil }
        p.discoverServices([Self.serviceUUID])
    }

    // MARK: CBCentralManagerDelegate

    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        switch central.state {
        case .poweredOn: connectOrScan()
        case .unauthorized: state = .unauthorized
        default: state = .off
        }
    }

    func centralManager(_ central: CBCentralManager, willRestoreState dict: [String: Any]) {
        if let restored = dict[CBCentralManagerRestoredStatePeripheralsKey] as? [CBPeripheral],
           let p = restored.first {
            peripheral = p
            p.delegate = self
        }
    }

    func centralManager(_ central: CBCentralManager, didDiscover peripheral: CBPeripheral,
                        advertisementData: [String: Any], rssi RSSI: NSNumber) {
        central.stopScan()
        self.peripheral = peripheral
        peripheral.delegate = self
        state = .connecting
        central.connect(peripheral, options: nil)
    }

    func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
        didConnect(peripheral)
    }

    func centralManager(_ central: CBCentralManager, didFailToConnect peripheral: CBPeripheral,
                        error: Error?) {
        print("BLE connect failed: \(error?.localizedDescription ?? "?")")
        connectOrScan()
    }

    func centralManager(_ central: CBCentralManager, didDisconnectPeripheral peripheral: CBPeripheral,
                        error: Error?) {
        rxChar = nil
        guard peripheral == self.peripheral else { return }   // forget() already moved on
        print("BLE disconnected: \(error?.localizedDescription ?? "by request")")
        connectOrScan()
    }

    // MARK: CBPeripheralDelegate

    func peripheral(_ peripheral: CBPeripheral, didDiscoverServices error: Error?) {
        guard let s = peripheral.services?.first(where: { $0.uuid == Self.serviceUUID }) else { return }
        peripheral.discoverCharacteristics([Self.txUUID, Self.rxUUID], for: s)
    }

    func peripheral(_ peripheral: CBPeripheral, didDiscoverCharacteristicsFor service: CBService,
                    error: Error?) {
        for ch in service.characteristics ?? [] {
            if ch.uuid == Self.txUUID { peripheral.setNotifyValue(true, for: ch) }
            if ch.uuid == Self.rxUUID { rxChar = ch }
        }
    }

    func peripheral(_ peripheral: CBPeripheral, didUpdateNotificationStateFor characteristic: CBCharacteristic,
                    error: Error?) {
        if characteristic.uuid == Self.txUUID, characteristic.isNotifying { onReady?() }
    }

    func peripheral(_ peripheral: CBPeripheral, didUpdateValueFor characteristic: CBCharacteristic,
                    error: Error?) {
        guard characteristic.uuid == Self.txUUID, let data = characteristic.value, !data.isEmpty else { return }
        handle([UInt8](data))
    }

    func peripheral(_ peripheral: CBPeripheral, didReadRSSI RSSI: NSNumber, error: Error?) {
        if error == nil { rssi = RSSI.intValue }
    }

    // MARK: Packets (main thread)

    private func handle(_ b: [UInt8]) {
        switch b[0] {
        case 0x04 where b.count == Self.audioPacketSize:
            lastPacketAt = Date()
            framesThisSecond += 1
            var pcm = [Int16](repeating: 0, count: Self.packetSamples)
            var acc: Float = 0
            for i in 0..<Self.packetSamples {
                let s = Self.ulawTable[Int(b[3 + i])]
                pcm[i] = s
                let f = Float(s) / 32768
                acc += f * f
            }
            rmsAcc += acc
            rmsPackets += 1
            if rmsPackets == 2 {   // one waveform bar per 20 ms, like protocol v1
                rmsHistory.append((rmsAcc / Float(2 * Self.packetSamples)).squareRoot())
                if rmsHistory.count > 150 { rmsHistory.removeFirst(rmsHistory.count - 150) }
                rmsAcc = 0; rmsPackets = 0
            }
            let seq = UInt16(b[1]) | (UInt16(b[2]) << 8)
            audioQueue.async {
                if let last = self.lastSeq {
                    let gap = Int(seq &- last) - 1
                    if gap > 0 && gap < 1000 {
                        DispatchQueue.main.async { self.lostFrames += gap }
                    }
                }
                self.lastSeq = seq
                self.onAudioFrame?(pcm)
            }
        case 0x02 where b.count == 6:
            if let ev = PendantEvent(rawValue: b[5]) { onEvent?(ev) }
        case 0x03 where b.count == 3:
            batteryPct = Int(b[1])
            lastPacketAt = Date()
            peripheral?.readRSSI()
        default:
            break
        }
    }
}
