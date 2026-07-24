//  EncoreApp.swift
//  Encore
//
//  App entry point — launches PagePlaylist inside the forest backdrop
//  container.

import SwiftUI

@main
struct EncoreApp: App {
    var body: some Scene {
        WindowGroup {
            PlaylistPreviewContainer {
                PagePlaylist()
            }
        }
    }
}
