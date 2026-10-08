//  ShazamKitMatcher.swift
//  Encore
//
//  Recognition = Shazam's own catalog (cloud) through ShazamKit: an
//  SHSession created without a custom catalog. Needs network at match time
//  and the ShazamKit App Service enabled on the App ID (docs/MVP_PRD.md).

import Foundation
import ShazamKit

extension MatchedTrack {
    init(_ item: SHMatchedMediaItem) {
        self.init(shazam_id: item.shazamID,
                  title: item.title ?? "Titre inconnu",
                  artist: item.artist ?? "",
                  isrc: item.isrc,
                  apple_music_id: item.appleMusicID,
                  artwork_url: item.artworkURL?.absoluteString,
                  apple_music_url: item.appleMusicURL?.absoluteString)
    }
}

