//  CatalogStore.swift
//  Encore
//
//  In-memory index of the bundled catalog.json (generated from Mathieu's
//  catalog.sqlite — see data/catalog_manifest.md). Keyed by the same id
//  that names each signatures/<id>.shazamsignature file.

import Foundation

struct CatalogTrack: Codable, Identifiable {
    let id: Int
    let title: String
    let artist: String
    let album: String?
    let duration: Double?
    let bpm: Double?
}

final class CatalogStore {
    static let shared = CatalogStore()

    private(set) var tracks: [Int: CatalogTrack] = [:]

    private init() {
        guard let url = Bundle.main.url(forResource: "catalog", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let list = try? JSONDecoder().decode([CatalogTrack].self, from: data) else {
            print("CatalogStore: catalog.json missing from bundle")
            return
        }
        tracks = Dictionary(uniqueKeysWithValues: list.map { ($0.id, $0) })
        print("CatalogStore: \(tracks.count) tracks")
    }

    func track(_ id: Int) -> CatalogTrack? { tracks[id] }

    /// All bundled reference signatures, whether Xcode flattened the folder or kept it.
    static func signatureURLs() -> [URL] {
        let flat = Bundle.main.urls(forResourcesWithExtension: "shazamsignature", subdirectory: nil) ?? []
        if !flat.isEmpty { return flat }
        return Bundle.main.urls(forResourcesWithExtension: "shazamsignature", subdirectory: "signatures") ?? []
    }
}
