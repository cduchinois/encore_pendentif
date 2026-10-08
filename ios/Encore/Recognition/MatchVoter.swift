//  MatchVoter.swift
//  Encore
//
//  Turns ShazamKit's raw streaming answers into confirmed songs. A streaming
//  SHSession answers every few seconds, and Shazam's catalog is full of
//  covers, karaoke and remix versions: a single answer is often the right
//  title by the wrong artist, or a look-alike. So:
//  - versions of the same title count as the same song (no new row);
//  - a new song needs 2 agreeing answers (3 to replace a song already playing);
//  - the version reported most often in the vote is the one journaled.

import Foundation

struct MatchVoter {
    /// Song currently in the setlist.
    private(set) var confirmed: MatchedTrack? = nil

    private var candidate: MatchedTrack? = nil
    private var candidateHits = 0
    private var votes: [String: (track: MatchedTrack, count: Int)] = [:]
    private var lastCandidateHit = Date.distantPast

    /// Answers older than this no longer support a candidate.
    private let candidateWindow: TimeInterval = 20

    /// Feed one Shazam answer. Returns the song to journal when a NEW song is
    /// confirmed, nil otherwise.
    mutating func add(_ track: MatchedTrack, now: Date = Date()) -> MatchedTrack? {
        // The current song still playing (any version of it): nothing new,
        // and it interrupts any competing candidate.
        if let c = confirmed, Self.sameSong(track, c) {
            resetCandidate()
            return nil
        }
        if now.timeIntervalSince(lastCandidateHit) > candidateWindow { resetCandidate() }
        lastCandidateHit = now

        if let cand = candidate, Self.sameSong(track, cand) {
            candidateHits += 1
        } else {
            resetCandidate()
            candidate = track
            candidateHits = 1
        }
        votes[track.key, default: (track, 0)].count += 1

        let needed = confirmed == nil ? 2 : 3
        guard candidateHits >= needed,
              let best = votes.values.max(by: { $0.count < $1.count })?.track else { return nil }
        confirmed = best
        resetCandidate()
        return best
    }

    /// An unknown track opened: whatever plays next is a new row.
    mutating func clear() {
        confirmed = nil
        resetCandidate()
    }

    private mutating func resetCandidate() {
        candidate = nil
        candidateHits = 0
        votes = [:]
    }

    // MARK: Same song?

    /// Same Shazam ID, or the same title once versions are stripped
    /// ("One More Time (As Made Famous By Daft Punk)" == "One More Time").
    static func sameSong(_ a: MatchedTrack, _ b: MatchedTrack) -> Bool {
        if a.key == b.key { return true }
        let ta = normalizedTitle(a.title), tb = normalizedTitle(b.title)
        return !ta.isEmpty && ta == tb
    }

    /// Lowercase, no accents, no "(...)"/"[...]", no " - Radio Edit",
    /// no "feat. X", letters and digits only.
    static func normalizedTitle(_ title: String) -> String {
        var t = title.folding(options: [.caseInsensitive, .diacriticInsensitive], locale: nil)
        t = t.replacingOccurrences(of: #"\([^)]*\)|\[[^\]]*\]"#, with: " ", options: .regularExpression)
        for sep in [" - ", " feat. ", " feat ", " ft. ", " featuring "] {
            if let r = t.range(of: sep) { t = String(t[..<r.lowerBound]) }
        }
        return t.filter { $0.isLetter || $0.isNumber }
    }
}
