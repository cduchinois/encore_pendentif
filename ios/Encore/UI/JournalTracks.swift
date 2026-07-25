//  JournalTracks.swift
//  Encore
//
//  Bridge between the journal (contracts/journal.schema.json) and the
//  setlist UI model: track_match events become PlaylistTrack rows, shared by
//  PendantPage and PhonePage.

import Foundation

extension SessionStore {
    /// journal track_match events -> the model SetlistTimeline renders.
    /// Pinned = a pin event references the same track; playing = last match.
    var playlistTracks: [PlaylistTrack] {
        let pinnedIDs = Set(events.filter { $0.kind == .pin }.compactMap(\.track_id))
        let matches = events.filter { $0.kind == .track_match }
        return matches.enumerated().map { i, ev in
            let meta = ev.track_id.flatMap { CatalogStore.shared.track($0) }
            return PlaylistTrack(
                index: i + 1,
                title: meta?.title ?? "Titre inconnu",
                artist: meta?.artist ?? "",
                timestamp: Self.mmss(ev.ts_ms),
                duration: nil,
                bpm: meta?.bpm.map { Int($0) },
                isPinned: ev.track_id.map { pinnedIDs.contains($0) } ?? false,
                isPlaying: i == matches.count - 1
            )
        }
    }

    private static func mmss(_ ms: Int) -> String {
        let s = ms / 1000
        return String(format: "%02d:%02d", s / 60, s % 60)
    }
}
