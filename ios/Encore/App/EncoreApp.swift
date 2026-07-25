//  EncoreApp.swift
//  Encore
//
//  App entry point. Pendant = live capture via the pendant stream,
//  Phone = recognition via the iPhone mic (no pendant), Demo = the design
//  mockup until the journal wires into it, Settings = app preferences.

import SwiftUI

@main
struct EncoreApp: App {
    @StateObject private var stage = RecognitionStage()

    var body: some Scene {
        WindowGroup {
            TabView {
                PendantPage(stage: stage)
                    .tabItem { Label("Pendant", systemImage: "waveform") }
                PhonePage(stage: stage)
                    .tabItem { Label("Phone", systemImage: "iphone") }
                PlaylistPreviewContainer {
                    DemoPage()
                }
                .tabItem { Label("Demo", systemImage: "music.note.list") }
                SettingsView()
                    .tabItem { Label("Settings", systemImage: "gearshape") }
            }
            .onAppear { stage.start() }
        }
    }
}
