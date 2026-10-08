//  CapturePipeline.swift
//  Encore
//
//  One independent capture chain (pendant OR phone mic): its own SHSession
//  against Shazam's cloud catalog, its own journal, its own current track and
//  unknown-track detection. What one source captures never leaks into the
//  other's timeline.

import Foundation
import AVFoundation
import Combine
import ShazamKit

final class CapturePipeline: NSObject, ObservableObject, SHSessionDelegate {
    @Published var currentTrack: MatchedTrack? = nil
    @Published var isMusic = false
    /// Last ShazamKit failure (auth, App Service not enabled, network), nil
    /// after a successful match. Shown in the page header.
    @Published var matchError: String? = nil

    let journal = SessionStore()
    /// Fired on a confirmed NEW track (used for the pendant LED flash).
    var onConfirmed: ((MatchedTrack) -> Void)?
    /// Network reachability, read on the audio queue (set by RecognitionStage).
    var isOnline: () -> Bool = { true }

    private let session = SHSession()          // no custom catalog = Shazam catalog
    private let detector = MusicDetector()

    /// The audio queue (ingest) and ShazamKit's delegate queue both touch
    /// the state below.
    private let lock = NSLock()
    /// Raw Shazam answers -> confirmed songs (votes, same-title versions).
    private var voter = MatchVoter()
    /// 0.5 s chunks of music heard since the last match.
    private var musicChunksUnmatched = 0
    private var unknownOpen = false
    /// ~20 s of unmatched music before we journal an unknown track; while an
    /// unknown is already open, ~45 s more of unmatched music opens the next
    /// one (chained unknown tracks in a set).
    private let unknownAfterChunks = 40
    private let unknownRearmChunks = 90
    /// Consecutive non-music chunks; ~6 (3 s) = track boundary.
    private var nonMusicChunks = 0

    func attach(format: AVAudioFormat) {
        session.delegate = self
        detector.start(format: format)
    }

    /// Called on the source's audio queue with 0.5 s @ 16 kHz mono buffers.
    func ingest(_ buffer: AVAudioPCMBuffer, rms: Float) {
        journal.appendEnergy(Double(rms) * 3)
        detector.analyze(buffer)
        let music = detector.isMusic
        DispatchQueue.main.async { self.isMusic = music }
        session.matchStreamingBuffer(buffer, at: nil)

        lock.lock()
        // A ~3 s break in the music (manual song switch, DJ hard cut) is a
        // track boundary: close the open unknown so the next unknown song
        // opens its own row after its own 20 s.
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
        var openUnknown = false
        if music {
            musicChunksUnmatched += 1
            let threshold = unknownOpen ? unknownRearmChunks : unknownAfterChunks
            if musicChunksUnmatched >= threshold {
                musicChunksUnmatched = 0
                unknownOpen = true
                voter.clear()               // the same song matching later = a new row
                openUnknown = true
            }
        }
        lock.unlock()

        if openUnknown {
            // "offline" tells the UI why: no network, not "Shazam doesn't know it".
            journal.append(.track_match, source: .world_catalog,
                           note: isOnline() ? "unknown" : "offline")
            DispatchQueue.main.async { self.currentTrack = nil }
        }
    }

    /// Pin from the UI (tap on a setlist card) or from the pendant gesture.
    /// nil = a moment with no identified song.
    func pin(_ track: MatchedTrack?) {
        journal.append(.pin, track: track)
    }

    // MARK: SHSessionDelegate

    func session(_ session: SHSession, didFind match: SHMatch) {
        guard let item = match.mediaItems.first else { return }

        // One answer is not enough: Shazam often returns a cover or a
        // look-alike for a few seconds. MatchVoter waits for agreement.
        lock.lock()
        musicChunksUnmatched = 0
        let wasPlaying = voter.confirmed != nil
        let confirmed = voter.add(MatchedTrack(item))
        if confirmed != nil { unknownOpen = false }
        lock.unlock()
        guard let track = confirmed else { return }

        journal.append(.track_match, track: track, source: .world_catalog)
        if wasPlaying { journal.append(.transition, track: track, source: .world_catalog) }
        onConfirmed?(track)
        DispatchQueue.main.async {
            self.currentTrack = track
            self.matchError = nil
        }
    }

    func session(_ session: SHSession, didNotFindMatchFor signature: SHSignature, error: Error?) {
        // No match is frequent between tracks; the unknown logic runs on music
        // time, not here. An error is different: a failed request (no network,
        // ShazamKit App Service not enabled) and must be visible.
        // Post-MVP: queue the signature while offline and match it when the
        // network returns (docs/MVP_PRD.md section 6).
        guard let error else { return }
        print("ShazamKit match failed: \(error)")
        let message = error.localizedDescription
        DispatchQueue.main.async { self.matchError = message }
    }
}
