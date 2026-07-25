//  ShazamKitMatcher.swift
//  Encore
//
//  Stage 1 of the recognition ladder: offline SHCustomCatalog built from the
//  bundled reference signatures. Match results carry the catalog.sqlite id.

import Foundation
import AVFoundation
import ShazamKit

struct EncoreMatch {
    let trackID: Int
    let title: String
    let artist: String
    let offset: TimeInterval
}

final class ShazamKitMatcher: NSObject, SHSessionDelegate {
    static let trackIDProperty = SHMediaItemProperty("encore_track_id")

    /// Called on an arbitrary ShazamKit queue.
    var onMatch: ((EncoreMatch) -> Void)?
    var onNoMatch: (() -> Void)?

    private var session: SHSession?
    private(set) var referenceCount = 0

    /// Build the custom catalog from the bundle. ~388 signatures, a few seconds; call off-main once.
    func loadCatalog() {
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
                Self.trackIDProperty: id,
            ])
            do {
                try catalog.addReferenceSignature(sig, representing: [item])
                loaded += 1
            } catch {
                print("Matcher: signature \(id) rejected: \(error)")
            }
        }
        referenceCount = loaded
        print("Matcher: \(loaded) reference signatures loaded")
        let s = SHSession(catalog: catalog)
        s.delegate = self
        session = s
    }

    func match(buffer: AVAudioPCMBuffer) {
        session?.matchStreamingBuffer(buffer, at: nil)
    }

    // MARK: SHSessionDelegate

    func session(_ session: SHSession, didFind match: SHMatch) {
        guard let item = match.mediaItems.first,
              let id = item[Self.trackIDProperty] as? Int else { return }
        onMatch?(EncoreMatch(trackID: id,
                             title: item.title ?? "?",
                             artist: item.artist ?? "?",
                             offset: item.predictedCurrentMatchOffset))
    }

    func session(_ session: SHSession, didNotFindMatchFor signature: SHSignature, error: Error?) {
        onNoMatch?()
    }
}
