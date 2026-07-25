//  RecognitionStage.swift
//  Encore
//
//  Orchestrates the recognition ladder. Today only stage 1 (local custom
//  catalog) is active; the no-match hook is where embeddings / world catalog /
//  Gemma ID card plug in later.
//
//  Flow: UDPAudioReceiver frames -> 0.5 s Float32 buffers -> ShazamKitMatcher.
//  A track is confirmed after 2 consecutive identical matches, and journaled
//  only when it changes (source: local_catalog).

import Foundation
import Combine
import AVFoundation

final class RecognitionStage: ObservableObject {
    @Published var currentTrack: CatalogTrack? = nil
    @Published var lastMatchAt: Date? = nil
    @Published var privacy = false
    @Published var matcherReady = false

    let receiver = UDPAudioReceiver()
    let journal = SessionStore()
    private let matcher = ShazamKitMatcher()

    private let format = AVAudioFormat(standardFormatWithSampleRate: 16000, channels: 1)!
    private var pending: [Int16] = []
    private let chunkSamples = 8000        // 0.5 s @ 16 kHz
    private var candidateID: Int? = nil
    private var candidateHits = 0
    private var noMatchStreak = 0

    func start() {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self else { return }
            self.matcher.loadCatalog()
            DispatchQueue.main.async { self.matcherReady = true }
        }

        matcher.onMatch = { [weak self] m in self?.handleMatch(m) }
        matcher.onNoMatch = { [weak self] in self?.handleNoMatch() }
        receiver.onAudioFrame = { [weak self] pcm in self?.ingest(pcm) }
        receiver.onEvent = { [weak self] ev in self?.handleEvent(ev) }
        receiver.start()
    }

    // Called on the UDP receive queue.
    private func ingest(_ pcm: [Int16]) {
        guard !privacy else { return }
        pending.append(contentsOf: pcm)
        guard pending.count >= chunkSamples else { return }
        let chunk = pending; pending.removeAll(keepingCapacity: true)

        guard let buf = AVAudioPCMBuffer(pcmFormat: format,
                                         frameCapacity: AVAudioFrameCount(chunk.count)) else { return }
        buf.frameLength = AVAudioFrameCount(chunk.count)
        let ch = buf.floatChannelData![0]
        var acc: Float = 0
        for i in 0..<chunk.count {
            let f = Float(chunk[i]) / 32768
            ch[i] = f; acc += f * f
        }
        matcher.match(buffer: buf)
        journal.appendEnergy(Double((acc / Float(chunk.count)).squareRoot()) * 3)  // rough loudness 0-1
    }

    private func handleMatch(_ m: EncoreMatch) {
        noMatchStreak = 0
        if m.trackID == candidateID { candidateHits += 1 }
        else { candidateID = m.trackID; candidateHits = 1 }
        guard candidateHits >= 2, currentTrack?.id != m.trackID else {
            DispatchQueue.main.async { self.lastMatchAt = Date() }
            return
        }
        let wasPlaying = currentTrack != nil
        journal.append(.track_match, trackID: m.trackID, source: .local_catalog)
        if wasPlaying { journal.append(.transition, trackID: m.trackID, source: .local_catalog) }
        receiver.sendLED(.flashOnce, r: 80, g: 0, b: 255)   // visible "got it" on the pendant
        DispatchQueue.main.async {
            self.currentTrack = CatalogStore.shared.track(m.trackID)
                ?? CatalogTrack(id: m.trackID, title: m.title, artist: m.artist,
                                album: nil, duration: nil, bpm: nil)
            self.lastMatchAt = Date()
        }
    }

    private func handleNoMatch() {
        noMatchStreak += 1
        // TODO(gate 3): after ~30 s of no match (60 chunks), hand the audio to the
        // next ladder stages — embeddings, world catalog, then the Gemma ID card.
    }

    // MARK: - iPhone-mic mode (no pendant — Mathieu's rig; also works in the
    // simulator, where the Mac's mic is used)

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
        guard let conv = micConverter else { return }
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
        matcher.match(buffer: out)
        let ch = out.floatChannelData![0]
        var acc: Float = 0
        for i in 0..<Int(out.frameLength) { acc += ch[i] * ch[i] }
        let rms = (acc / Float(out.frameLength)).squareRoot()
        journal.appendEnergy(Double(rms) * 3)
        DispatchQueue.main.async {
            self.micRMS.append(rms)
            if self.micRMS.count > 150 { self.micRMS.removeFirst(self.micRMS.count - 150) }
        }
    }

    private func handleEvent(_ ev: PendantEvent) {
        switch ev {
        case .pin:
            journal.append(.pin, trackID: currentTrack?.id)
        case .privacyOn:
            privacy = true
            pending.removeAll()
            journal.append(.privacy_on)
        case .privacyOff:
            privacy = false
            journal.append(.privacy_off)
        }
    }
}
