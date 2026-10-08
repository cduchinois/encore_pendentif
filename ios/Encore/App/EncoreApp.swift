//  EncoreApp.swift
//  Encore
//
//  App entry point. Pendant = live capture via the pendant's BLE stream,
//  Phone = recognition via the iPhone mic (no pendant), Demo = the design
//  mockup until the journal wires into it, Settings = app preferences.

import SwiftUI

@main
struct EncoreApp: App {
    @StateObject private var stage: RecognitionStage

    /// Started here, not in onAppear: a background relaunch for BLE state
    /// restoration shows no scene, but the central must still be recreated.
    init() {
        let s = RecognitionStage()
        s.start()
        _stage = StateObject(wrappedValue: s)
    }

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
                SettingsView(receiver: stage.receiver)
                    .tabItem { Label("Settings", systemImage: "gearshape") }
            }
        }
    }
}
