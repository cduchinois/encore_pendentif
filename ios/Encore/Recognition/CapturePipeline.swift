//  CapturePipeline.swift
//  Encore
//
//  One independent capture chain (pendant OR phone mic): its own SHSession,
//  its own journal, its own current track and unknown-track detection.
//  Both pipelines share the SHCustomCatalog, nothing else — what one source
//  captures never leaks into the other's timeline.

import Foundation
import AVFoundation
import Combine
import ShazamKit

final class CapturePipeline: NSObject, ObservableObject, SHSessionDelegate {
    @Published var currentTrack: CatalogTrack? = nil
    @Published var isMusic = false

    let journal = SessionStore()
    /// Fired on a confirmed NEW track (used for the pendant LED flash).
    var onConfirmed: ((EncoreMatch) -> Void)?

    private var session: SHSession?
    private let detector = MusicDetector()

    private var candidateID: Int? = nil
    private var candidateHits = 0
    /// 0.5 s chunks of music heard since the last confirmed match.
    private var musicChunksUnmatched = 0
    private var unknownOpen = false
    /// ~20 s of unmatched music before we journal an unknown track.
    private let unknownAfterChunks = 40

    func attach(catalog: SHCustomCatalog, format: AVAudioFormat) {
        let s = SHSession(catalog: catalog)
        s.delegate = self
        session = s
        detector.start(format: format)
    }

    /// Called on the source's audio queue with 0.5 s @ 16 kHz mono buffers.
    func ingest(_ buffer: AVAudioPCMBuffer, rms: Float) {
        journal.appendEnergy(Double(rms) * 3)
        detector.analyze(buffer)
        let music = detector.isMusic
        DispatchQueue.main.async { self.isMusic = music }
        session?.matchStreamingBuffer(buffer, at: nil)

        if music {
            musicChunksUnmatched += 1
            if musicChunksUnmatched >= unknownAfterChunks && !unknownOpen {
                unknownOpen = true
                journal.append(.track_match, trackID: nil, source: .local_catalog,
                               note: "unknown")
                DispatchQueue.main.async { self.currentTrack = nil }
            }
        }
    }

    /// Pin from the UI (tap on a setlist card) or from the pendant gesture.
    func pin(trackID: Int?) {
        journal.append(.pin, trackID: trackID ?? currentTrack?.id)
    }

    // MARK: SHSessionDelegate

    func session(_ session: SHSession, didFind match: SHMatch) {
        guard let item = match.mediaItems.first,
              let id = item[ShazamCatalogBuilder.trackIDProperty] as? Int else { return }
        let m = EncoreMatch(trackID: id,
                            title: item.title ?? "?",
                            artist: item.artist ?? "?",
                            offset: item.predictedCurrentMatchOffset)
        musicChunksUnmatched = 0
        if m.trackID == candidateID { candidateHits += 1 }
        else { candidateID = m.trackID; candidateHits = 1 }
        guard candidateHits >= 2, currentTrack?.id != m.trackID else { return }

        let wasPlaying = currentTrack != nil
        unknownOpen = false
        journal.append(.track_match, trackID: m.trackID, source: .local_catalog)
        if wasPlaying { journal.append(.transition, trackID: m.trackID, source: .local_catalog) }
        onConfirmed?(m)
        DispatchQueue.main.async {
            self.currentTrack = CatalogStore.shared.track(m.trackID)
                ?? CatalogTrack(id: m.trackID, title: m.title, artist: m.artist,
                                album: nil, duration: nil, bpm: nil)
        }
    }

    func session(_ session: SHSession, didNotFindMatchFor signature: SHSignature, error: Error?) {
        // Frequent between tracks; the unknown logic runs on music time, not here.
        // TODO(gate 3): this is where the ladder hands off to embeddings /
        // world catalog / the Gemma ID card.
    }
}
