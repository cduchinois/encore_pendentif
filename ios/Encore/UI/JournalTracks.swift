//  JournalTracks.swift
//  Encore
//
//  Bridge between a journal (contracts/journal.schema.json) and the setlist
//  UI model: track_match events become PlaylistTrack rows, shared by
//  PendantPage and PhonePage. Timestamps are wall-clock (22:41), not
//  elapsed time.

import Foundation

extension SessionStore {
    /// journal track_match events -> the model SetlistTimeline renders.
    /// track_id == nil = unmatched music ("unknown"); pinned = a pin event
    /// references the same track; playing = last row.
    var playlistTracks: [PlaylistTrack] {
        let pinnedIDs = Set(events.filter { $0.kind == .pin }.compactMap(\.track_id))
        let matches = events.filter { $0.kind == .track_match }
        return matches.enumerated().map { i, ev in
            let meta = ev.track_id.flatMap { CatalogStore.shared.track($0) }
            return PlaylistTrack(
                index: i + 1,
                title: meta?.title ?? "Titre inconnu",
                artist: meta?.artist ?? "en attente d'identification",
                timestamp: clock(ev.ts_ms),
                duration: nil,
                bpm: meta?.bpm.map { Int($0) },
                isPinned: ev.track_id.map { pinnedIDs.contains($0) } ?? false,
                isPlaying: i == matches.count - 1,
                catalogID: ev.track_id
            )
        }
    }

    /// Wall-clock "HH:mm" of session start + ts_ms.
    private func clock(_ ms: Int) -> String {
        let date = startedAt.addingTimeInterval(Double(ms) / 1000)
        let f = DateFormatter()
        f.dateFormat = "HH:mm"
        return f.string(from: date)
    }
}
