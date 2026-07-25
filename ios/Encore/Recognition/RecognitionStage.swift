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
