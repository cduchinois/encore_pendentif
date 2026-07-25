//  SessionStore.swift
//  Encore
//
//  The journal of the night, per contracts/journal.schema.json — field names
//  must stay identical to the schema (snake_case, same enums).

import Foundation
import Combine

/// contracts/id_card.schema.json — field names must match exactly.
/// bpm and ts_start_ms are injected (DSP + journal clock), never model output;
/// decoding tolerates their absence since the model's raw JSON won't have them.
struct IDCard: Codable {
    var genre: String
    var description: String
    var has_vocals: Bool
    var confidence: Double
    var ts_start_ms: Int
    var lyrics_snippet: String?
    var bpm: Double?
    var key: String?
    var clip_ref: String?

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        genre = try c.decode(String.self, forKey: .genre)
        description = try c.decode(String.self, forKey: .description)
        has_vocals = try c.decode(Bool.self, forKey: .has_vocals)
        confidence = try c.decode(Double.self, forKey: .confidence)
        ts_start_ms = try c.decodeIfPresent(Int.self, forKey: .ts_start_ms) ?? 0
        lyrics_snippet = try c.decodeIfPresent(String.self, forKey: .lyrics_snippet)
        bpm = try c.decodeIfPresent(Double.self, forKey: .bpm)
        key = try c.decodeIfPresent(String.self, forKey: .key)
        clip_ref = try c.decodeIfPresent(String.self, forKey: .clip_ref)
    }
}

struct JournalEvent: Codable, Identifiable {
    var id: Int { ts_ms }
    let ts_ms: Int
    let kind: Kind
    var track_id: Int? = nil
    var source: Source? = nil
    var transition_style: String? = nil
    var note: String? = nil
    var id_card: IDCard? = nil

    enum Kind: String, Codable {
        case track_match, id_card, pin, moment, transition, privacy_on, privacy_off
    }
    enum Source: String, Codable {
        case local_catalog, embedding, world_catalog, gemma
    }
}

struct EnergyPoint: Codable {
    let ts_ms: Int
    let level: Double   // 0...1
}

final class SessionStore: ObservableObject {
    @Published private(set) var events: [JournalEvent] = []
    @Published private(set) var energy: [EnergyPoint] = []

    let sessionID = UUID().uuidString
    let startedAt = Date()

    private var fileURL: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("journal-\(sessionID).json")
    }

    var msSinceStart: Int { Int(Date().timeIntervalSince(startedAt) * 1000) }

    func append(_ kind: JournalEvent.Kind, trackID: Int? = nil,
                source: JournalEvent.Source? = nil, note: String? = nil,
                idCard: IDCard? = nil) {
        let ev = JournalEvent(ts_ms: msSinceStart, kind: kind,
                              track_id: trackID, source: source, note: note,
                              id_card: idCard)
        DispatchQueue.main.async {
            self.events.append(ev)
            self.persist()
        }
    }

    func appendEnergy(_ level: Double) {
        DispatchQueue.main.async {
            self.energy.append(EnergyPoint(ts_ms: self.msSinceStart,
                                           level: min(max(level, 0), 1)))
        }
    }

    private func persist() {
        struct Journal: Codable {
            let session_id: String
            let started_at: String
            let events: [JournalEvent]
            let energy: [EnergyPoint]
        }
        let j = Journal(session_id: sessionID,
                        started_at: ISO8601DateFormatter().string(from: startedAt),
                        events: events, energy: energy)
        if let data = try? JSONEncoder().encode(j) {
            try? data.write(to: fileURL, options: .atomic)
        }
    }
}
