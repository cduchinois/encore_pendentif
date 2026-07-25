//  PlaylistTrack.swift
//  Encore
//
//  Model + demo dataset consumed by DemoPage (and the live setlists).

import Foundation

struct PlaylistTrack: Identifiable, Hashable {
    let id = UUID()
    let index: Int
    let title: String
    let artist: String
    let timestamp: String
    let duration: String?
    let bpm: Int?
    /// When true, the timeline dot renders with a rotating aurora rainbow halo.
    var isPinned: Bool = false
    /// When true, the timeline dot renders with a "live" pulsing sonar animation.
    var isPlaying: Bool = false
    /// catalog.sqlite id for live rows (nil for demo data and unknown tracks);
    /// used by tap-to-pin.
    var catalogID: Int? = nil
    /// Unknown-track enrichment from the Gemma ID card.
    var detail: String? = nil          // one-sentence description
    var lyrics: String? = nil          // heard lyrics snippet
    var clipURL: URL? = nil            // captured excerpt, playable in the row
}

enum PlaylistDemoData {
    static let label = "ENCORE"
    static let title = "One More Time"
    static let subtitle = "DJ Set · 1 h 24 min"
    static let venue = "Paris · 24 Jul 2026"
    static let averageBPM = 125

    static let tracks: [PlaylistTrack] = [
        .init(index: 1,  title: "One More Time",                 artist: "Daft Punk",           timestamp: "00:00", duration: "5:20", bpm: 123),
        .init(index: 2,  title: "Music Sounds Better With You",  artist: "Stardust",            timestamp: "04:12", duration: "7:03", bpm: 122, isPinned: true),
        .init(index: 3,  title: "Lady (Hear Me Tonight)",        artist: "Modjo",               timestamp: "08:47", duration: "5:00", bpm: 126),
        .init(index: 4,  title: "Finally",                       artist: "Kings of Tomorrow",   timestamp: "13:26", duration: "8:22", bpm: 121),
        .init(index: 5,  title: "You Don\u{2019}t Know Me",      artist: "Armand Van Helden",   timestamp: "18:05", duration: "5:12", bpm: 124),
        .init(index: 6,  title: "Sing It Back",                  artist: "Moloko",              timestamp: "23:10", duration: "5:31", bpm: 125),
        .init(index: 7,  title: "Lola\u{2019}s Theme",           artist: "The Shapeshifters",   timestamp: "28:42", duration: "5:20", bpm: 127),
        .init(index: 8,  title: "Make Luv",                      artist: "Room 5",              timestamp: "34:18", duration: "5:11", bpm: 128),
        .init(index: 9,  title: "Insomnia",                      artist: "Faithless",           timestamp: "39:50", duration: "5:39", bpm: 128),
        .init(index: 10, title: "Around the World",              artist: "Daft Punk",           timestamp: "45:31", duration: "7:09", bpm: 121),
        .init(index: 11, title: "Gypsy Woman",                   artist: "Crystal Waters",      timestamp: "52:14", duration: "6:22", bpm: 124),
        .init(index: 12, title: "Free From Desire",              artist: "Gala",                timestamp: "58:37", duration: "6:15", bpm: 128, isPlaying: true),
    ]
}
