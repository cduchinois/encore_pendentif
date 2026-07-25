//  UDPAudioReceiver.swift
//  Encore
//
//  Listens on UDP :7777 for pendant protocol v1 packets
//  (contracts/pendant_protocol.md) and republishes audio frames, events
//  and heartbeats. Also sends CMD_LED back to the pendant.

import Foundation
import Combine
import Network

enum PendantEvent: UInt8 {
    case pin = 1
    case privacyOn = 2
    case privacyOff = 3
}

enum LEDMode: UInt8 {
    case off = 0, solid = 1, pulse = 2, flashOnce = 3
}

final class UDPAudioReceiver: ObservableObject {
    static let port: UInt16 = 7777
    static let frameSamples = 320   // 20 ms @ 16 kHz mono int16
    static let audioPacketSize = 1 + 2 + 4 + frameSamples * 2

    // Stats for the debug UI (main-thread published).
    @Published var isListening = false
    @Published var framesPerSecond = 0
    @Published var lostFrames = 0
    @Published var batteryPct: Int = -1
    @Published var rssi: Int = 0
    @Published var lastPacketAt: Date? = nil
    @Published var rmsHistory: [Float] = []   // one RMS value per frame, last ~3 s

    /// Called on the receive queue with each 320-sample PCM frame.
    var onAudioFrame: (([Int16]) -> Void)?
    /// Called on the main thread.
    var onEvent: ((PendantEvent) -> Void)?

    private let queue = DispatchQueue(label: "encore.udp")
    private var listener: NWListener?
    private var pendantConnection: NWConnection?
    private var lastSeq: UInt16? = nil
    private var framesThisSecond = 0
    private var fpsTimer: Timer?

    func start() {
        guard listener == nil else { return }
        do {
            let params = NWParameters.udp
            params.allowLocalEndpointReuse = true
            let l = try NWListener(using: params, on: NWEndpoint.Port(rawValue: Self.port)!)
            l.newConnectionHandler = { [weak self] connection in
                guard let self else { return }
                self.pendantConnection = connection
                connection.start(queue: self.queue)
                self.receiveLoop(connection)
            }
            l.stateUpdateHandler = { [weak self] state in
                DispatchQueue.main.async { self?.isListening = (state == .ready) }
            }
            l.start(queue: queue)
            listener = l
        } catch {
            print("UDP listener failed: \(error)")
        }
        fpsTimer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            guard let self else { return }
            self.framesPerSecond = self.framesThisSecond
            self.framesThisSecond = 0
        }
    }

    func stop() {
        listener?.cancel(); listener = nil
        pendantConnection?.cancel(); pendantConnection = nil
        fpsTimer?.invalidate(); fpsTimer = nil
        DispatchQueue.main.async { self.isListening = false }
    }

    /// CMD_LED 0x10: mode + RGB, 5 bytes. flashOnce overlays the ambiance for 300 ms.
    func sendLED(_ mode: LEDMode, r: UInt8, g: UInt8, b: UInt8) {
        guard let conn = pendantConnection else { return }
        let pkt = Data([0x10, mode.rawValue, r, g, b])
        conn.send(content: pkt, completion: .contentProcessed { _ in })
    }

    private func receiveLoop(_ connection: NWConnection) {
        connection.receiveMessage { [weak self] data, _, _, error in
            guard let self else { return }
            if let data, !data.isEmpty { self.handle([UInt8](data)) }
            if error == nil { self.receiveLoop(connection) }
        }
    }

    private func handle(_ b: [UInt8]) {
        switch b[0] {
        case 0x01 where b.count == Self.audioPacketSize:
            let seq = UInt16(b[1]) | (UInt16(b[2]) << 8)
            if let last = lastSeq {
                let gap = Int(seq &- last) - 1
                if gap > 0 && gap < 1000 {
                    DispatchQueue.main.async { self.lostFrames += gap }
                }
            }
            lastSeq = seq
            var pcm = [Int16](repeating: 0, count: Self.frameSamples)
            for i in 0..<Self.frameSamples {
                pcm[i] = Int16(bitPattern: UInt16(b[7 + i * 2]) | (UInt16(b[7 + i * 2 + 1]) << 8))
            }
            onAudioFrame?(pcm)
            framesThisSecond += 1
            var acc: Float = 0
            for s in pcm { let f = Float(s) / 32768; acc += f * f }
            let rms = (acc / Float(Self.frameSamples)).squareRoot()
            DispatchQueue.main.async {
                self.lastPacketAt = Date()
                self.rmsHistory.append(rms)
                if self.rmsHistory.count > 150 { self.rmsHistory.removeFirst(self.rmsHistory.count - 150) }
            }
        case 0x02 where b.count == 6:
            if let ev = PendantEvent(rawValue: b[5]) {
                DispatchQueue.main.async { self.onEvent?(ev) }
            }
        case 0x03 where b.count == 3:
            let bat = Int(b[1]); let rssi = Int(Int8(bitPattern: b[2]))
            DispatchQueue.main.async {
                self.batteryPct = bat; self.rssi = rssi; self.lastPacketAt = Date()
            }
        default:
            break
        }
    }
}
