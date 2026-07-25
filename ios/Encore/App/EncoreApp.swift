//  EncoreApp.swift
//  Encore
//
//  App entry point. "Live" is the working session (receiver + recognition),
//  "Playlist" is the design mockup until the journal wires into it.

import SwiftUI

@main
struct EncoreApp: App {
    @StateObject private var stage = RecognitionStage()

    var body: some Scene {
        WindowGroup {
            TabView {
                LiveSessionView(stage: stage)
                    .tabItem { Label("Live", systemImage: "waveform") }
                MicListenView(stage: stage)
                    .tabItem { Label("Listen", systemImage: "mic") }
                PlaylistPreviewContainer {
                    PagePlaylist()
                }
                .tabItem { Label("Playlist", systemImage: "music.note.list") }
                SettingsView()
                    .tabItem { Label("Settings", systemImage: "gearshape") }
            }
            .onAppear { stage.start() }
        }
    }
}
