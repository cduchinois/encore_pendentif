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
        // Collapse consecutive rows of the same track: one row per continuous
        // play, however many times the matcher re-confirmed it. Unknown rows
        // (track_id nil) collapse together the same way.
        var matches: [JournalEvent] = []
        for ev in events where ev.kind == .track_match {
            if let last = matches.last, last.track_id == ev.track_id { continue }
            matches.append(ev)
        }
        let idCards: [(ts: Int, card: IDCard)] = events.compactMap { ev in
            guard ev.kind == .id_card, let c = ev.id_card else { return nil }
            return (ev.ts_ms, c)
        }
        return matches.enumerated().map { i, ev in
            let meta = ev.track_id.flatMap { CatalogStore.shared.track($0) }
            // Unknown row: dress it with the first ID card issued after it —
            // genre, BPM, description, heard lyrics, and the captured excerpt.
            var unknownArtist = "en attente d'identification"
            var unknownBPM: Int? = nil
            var detail: String? = nil
            var lyrics: String? = nil
            var clipURL: URL? = nil
            if ev.track_id == nil,
               let card = idCards.first(where: { $0.ts >= ev.ts_ms })?.card {
                unknownArtist = card.genre
                unknownBPM = card.bpm.map { Int($0) }
                detail = card.description
                lyrics = card.lyrics_snippet
                if let ref = card.clip_ref {
                    let u = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
                        .appendingPathComponent("unknown_clips").appendingPathComponent(ref)
                    if FileManager.default.fileExists(atPath: u.path) { clipURL = u }
                }
            }
            return PlaylistTrack(
                index: i + 1,
                title: meta?.title ?? "Titre inconnu",
                artist: meta?.artist ?? unknownArtist,
                timestamp: clock(ev.ts_ms),
                duration: nil,
                bpm: meta?.bpm.map { Int($0) } ?? unknownBPM,
                isPinned: ev.track_id.map { pinnedIDs.contains($0) } ?? false,
                isPlaying: i == matches.count - 1,
                catalogID: ev.track_id,
                detail: detail,
                lyrics: lyrics,
                clipURL: clipURL
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
