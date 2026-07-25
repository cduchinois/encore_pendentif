//  ShazamKitMatcher.swift
//  Encore
//
//  Builds the shared SHCustomCatalog from the bundled reference signatures.
//  Each CapturePipeline opens its own SHSession against this one catalog —
//  the catalog is immutable and safe to share; sessions are not.

import Foundation
import ShazamKit

struct EncoreMatch {
    let trackID: Int
    let title: String
    let artist: String
    let offset: TimeInterval
}

enum ShazamCatalogBuilder {
    static let trackIDProperty = SHMediaItemProperty("encore_track_id")

    /// ~388 signatures, a few seconds; call off-main once at launch.
    static func build() -> (catalog: SHCustomCatalog, count: Int)? {
        let catalog = SHCustomCatalog()
        var loaded = 0
        for url in CatalogStore.signatureURLs() {
            guard let id = Int(url.deletingPathExtension().lastPathComponent),
                  let data = try? Data(contentsOf: url),
                  let sig = try? SHSignature(dataRepresentation: data) else { continue }
            let meta = CatalogStore.shared.track(id)
            let item = SHMediaItem(properties: [
                .title: meta?.title ?? "Track \(id)",
                .artist: meta?.artist ?? "",
                trackIDProperty: id,
            ])
            do {
                try catalog.addReferenceSignature(sig, representing: [item])
                loaded += 1
            } catch {
                print("Catalog: signature \(id) rejected: \(error)")
            }
        }
        print("Catalog: \(loaded) reference signatures loaded")
        return loaded > 0 ? (catalog, loaded) : nil
    }
}
