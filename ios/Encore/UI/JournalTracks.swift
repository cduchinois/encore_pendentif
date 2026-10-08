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
    /// track == nil = music Shazam couldn't name ("unknown", or "offline" when
    /// the phone had no network); pinned = a pin event references the same
    /// song; playing = last row.
    var playlistTracks: [PlaylistTrack] {
        let pinnedKeys = Set(events.filter { $0.kind == .pin }.compactMap { $0.track?.key })
        // Collapse consecutive rows of the same song: one row per continuous
        // play. Unknown rows stay separate: the pipeline already decides when
        // a new unknown song starts.
        var matches: [JournalEvent] = []
        for ev in events where ev.kind == .track_match {
            if let key = ev.track?.key, matches.last?.track?.key == key { continue }
            matches.append(ev)
        }
        return matches.enumerated().map { i, ev in
            PlaylistTrack(
                index: i + 1,
                title: ev.track?.title ?? "Titre inconnu",
                artist: ev.track?.artist
                    ?? (ev.note == "offline" ? "pas de réseau" : "non reconnu par Shazam"),
                timestamp: clock(ev.ts_ms),
                duration: nil,
                bpm: nil,
                isPinned: ev.track.map { pinnedKeys.contains($0.key) } ?? false,
                isPlaying: i == matches.count - 1,
                track: ev.track
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
