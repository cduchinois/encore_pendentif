//  RecognitionStage.swift
//  Encore
//
//  Owns the two independent capture pipelines and their audio sources:
//  - pendant: UDP frames from the pendant -> `pendant` pipeline
//  - phone:   iPhone mic (AVAudioEngine)  -> `phone` pipeline
//  Each pipeline has its own SHSession and journal; they only share the
//  custom catalog. The pendant timeline shows nothing unless the pendant
//  streams, the phone timeline nothing unless the mic listens.

import Foundation
import Combine
import AVFoundation

final class RecognitionStage: ObservableObject {
    let receiver = UDPAudioReceiver()
    let pendant = CapturePipeline()
    let phone = CapturePipeline()

    @Published var matcherReady = false
    @Published var privacy = false

    private let format = AVAudioFormat(standardFormatWithSampleRate: 16000, channels: 1)!
    private let chunkSamples = 8000        // 0.5 s @ 16 kHz
    private var pendantPending: [Int16] = []

    func start() {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self, let built = ShazamCatalogBuilder.build() else { return }
            self.pendant.attach(catalog: built.catalog, format: self.format)
            self.phone.attach(catalog: built.catalog, format: self.format)
            DispatchQueue.main.async { self.matcherReady = true }
        }

        pendant.onConfirmed = { [weak self] _ in
            self?.receiver.sendLED(.flashOnce, r: 80, g: 0, b: 255)
        }

        receiver.onAudioFrame = { [weak self] pcm in self?.ingestPendant(pcm) }
        receiver.onEvent = { [weak self] ev in self?.handlePendantEvent(ev) }
        receiver.start()
    }

    // MARK: Pendant source (UDP receive queue)

    private func ingestPendant(_ pcm: [Int16]) {
        // Protocol invariant: a pendant in privacy sends HEARTBEAT only.
        // Audio frames flowing = privacy is off — auto-clear a stale latch
        // (e.g. PRIVACY_ON received before a reflash that disabled the gesture).
        if privacy {
            DispatchQueue.main.async { if self.privacy { self.privacy = false } }
        }
        guard matcherReady else { return }
        pendantPending.append(contentsOf: pcm)
        guard pendantPending.count >= chunkSamples else { return }
        let chunk = pendantPending; pendantPending.removeAll(keepingCapacity: true)
        if let (buf, rms) = Self.makeBuffer(chunk, format: format) {
            pendant.ingest(buf, rms: rms)
        }
    }

    private func handlePendantEvent(_ ev: PendantEvent) {
        switch ev {
        case .pin:
            pendant.pin(trackID: nil)
        case .privacyOn:
            // pendantPending is owned by the UDP queue — never touch it here
            // (main thread); a stale half-second of buffer is harmless.
            privacy = true
            pendant.journal.append(.privacy_on)
        case .privacyOff:
            privacy = false
            pendant.journal.append(.privacy_off)
        }
    }

    static func makeBuffer(_ chunk: [Int16], format: AVAudioFormat) -> (AVAudioPCMBuffer, Float)? {
        guard let buf = AVAudioPCMBuffer(pcmFormat: format,
                                         frameCapacity: AVAudioFrameCount(chunk.count)) else { return nil }
        buf.frameLength = AVAudioFrameCount(chunk.count)
        let ch = buf.floatChannelData![0]
        var acc: Float = 0
        for i in 0..<chunk.count {
            let f = Float(chunk[i]) / 32768
            ch[i] = f; acc += f * f
        }
        return (buf, (acc / Float(chunk.count)).squareRoot())
    }

    // MARK: Phone source (iPhone mic; also works in the simulator = Mac mic)

    @Published var micActive = false
    @Published var micRMS: [Float] = []

    private let engine = AVAudioEngine()
    private var micConverter: AVAudioConverter?

    func startMic() {
        guard !micActive else { return }
        AVAudioApplication.requestRecordPermission { [weak self] granted in
            guard granted else { print("mic permission denied"); return }
            DispatchQueue.main.async { self?.beginMicCapture() }
        }
    }

    func stopMic() {
        guard micActive else { return }
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        try? AVAudioSession.sharedInstance().setActive(false)
        micActive = false
    }

    private func beginMicCapture() {
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(.record, mode: .measurement)
            try session.setActive(true)
        } catch {
            print("audio session: \(error)"); return
        }
        let input = engine.inputNode
        let inFormat = input.outputFormat(forBus: 0)
        guard let conv = AVAudioConverter(from: inFormat, to: format) else { return }
        micConverter = conv
        input.installTap(onBus: 0, bufferSize: 8192, format: inFormat) { [weak self] buf, _ in
            self?.feedMic(buf)
        }
        do { try engine.start(); micActive = true }
        catch { print("audio engine: \(error)") }
    }

    private func feedMic(_ buf: AVAudioPCMBuffer) {
        guard matcherReady, let conv = micConverter else { return }
        let ratio = format.sampleRate / buf.format.sampleRate
        let capacity = AVAudioFrameCount(Double(buf.frameLength) * ratio) + 16
        guard let out = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: capacity) else { return }
        var err: NSError?
        var consumed = false
        conv.convert(to: out, error: &err) { _, status in
            if consumed { status.pointee = .noDataNow; return nil }
            consumed = true; status.pointee = .haveData; return buf
        }
        guard err == nil, out.frameLength > 0 else { return }
        let ch = out.floatChannelData![0]
        var acc: Float = 0
        for i in 0..<Int(out.frameLength) { acc += ch[i] * ch[i] }
        let rms = (acc / Float(out.frameLength)).squareRoot()
        phone.ingest(out, rms: rms)
        DispatchQueue.main.async {
            self.micRMS.append(rms)
            if self.micRMS.count > 150 { self.micRMS.removeFirst(self.micRMS.count - 150) }
        }
    }
}
