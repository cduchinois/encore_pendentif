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
    /// Fired off-main with each frozen unknown clip + its ts_start_ms in the
    /// session clock — the Gemma ID card + SerpAPI resolve entry point.
    var onUnknownClip: ((UnknownClipRecorder.Clip, Int) -> Void)?

    private var session: SHSession?
    private let detector = MusicDetector()

    private var candidateID: Int? = nil
    private var candidateHits = 0
    /// Synchronous mirror of the confirmed track, checked on the delegate
    /// queue — currentTrack updates async on main, so guarding on it alone
    /// lets rapid successive matches through (one journal row per match).
    private var confirmedTrackID: Int? = nil
    /// 0.5 s chunks of music heard since the last confirmed match.
    private var musicChunksUnmatched = 0
    private var unknownOpen = false
    /// ~20 s of unmatched music before we journal an unknown track; while an
    /// unknown is already open, ~45 s more of unmatched music opens the next
    /// one (chained unknown tracks in a set).
    private let unknownAfterChunks = 40
    private let unknownRearmChunks = 90
    /// Consecutive non-music chunks; ~6 (3 s) = track boundary.
    private var nonMusicChunks = 0

    /// Rolling 30 s of audio + frozen clips of the unknowns (wav, ShazamKit
    /// signature, DSP BPM) — the payload for the Gemma ID card + SerpAPI.
    private let recorder = UnknownClipRecorder()
    @Published var unknownClips: [UnknownClipRecorder.Clip] = []

    func attach(catalog: SHCustomCatalog, format: AVAudioFormat) {
        let s = SHSession(catalog: catalog)
        s.delegate = self
        session = s
        detector.start(format: format)
    }

    /// Called on the source's audio queue with 0.5 s @ 16 kHz mono buffers.
    func ingest(_ buffer: AVAudioPCMBuffer, rms: Float) {
        journal.appendEnergy(Double(rms) * 3)
        recorder.push(buffer)
        detector.analyze(buffer)
        let music = detector.isMusic
        DispatchQueue.main.async { self.isMusic = music }
        session?.matchStreamingBuffer(buffer, at: nil)

        // A ~3 s break in the music (manual song switch, DJ hard cut) is a
        // track boundary: close the open unknown so the next unknown song
        // opens its own row after its own 20 s. Seamless blends between two
        // unknown tracks still merge — known limitation until we match
        // against our own unknown signatures.
        if !music {
            nonMusicChunks += 1
            if nonMusicChunks >= 6 && unknownOpen {
                unknownOpen = false
                musicChunksUnmatched = 0
            }
        } else {
            nonMusicChunks = 0
        }

        // Music-gated only: conversations and noise never advance this counter.
        if music {
            musicChunksUnmatched += 1
            let threshold = unknownOpen ? unknownRearmChunks : unknownAfterChunks
            if musicChunksUnmatched >= threshold {
                musicChunksUnmatched = 0
                unknownOpen = true
                confirmedTrackID = nil      // the same song matching later = a new row
                journal.append(.track_match, trackID: nil, source: .local_catalog,
                               note: "unknown")
                DispatchQueue.main.async { self.currentTrack = nil }
                let samples = recorder.snapshot()   // race-free: same queue as push()
                DispatchQueue.global(qos: .utility).async { [weak self] in
                    guard let self, let clip = self.recorder.freezeClip(from: samples) else { return }
                    let tsStart = max(0, self.journal.msSinceStart - Int(clip.duration * 1000))
                    DispatchQueue.main.async { self.unknownClips.append(clip) }
                    self.onUnknownClip?(clip, tsStart)
                }
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
        guard candidateHits >= 2, confirmedTrackID != m.trackID else { return }

        let wasPlaying = confirmedTrackID != nil
        confirmedTrackID = m.trackID
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
