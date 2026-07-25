//  AppSettings.swift
//  Encore
//
//  App-wide user preferences. For now: an optional custom background image
//  that replaces the bundled "BackgroundImage" asset everywhere
//  EncoreBackground is used. Persisted in Documents so it survives relaunch.

import SwiftUI
import Combine

final class AppSettings: ObservableObject {
    static let shared = AppSettings()

    @Published private(set) var customBackground: UIImage?

    // MARK: Gemma ID-card backend (never in git — UserDefaults only)

    @Published var gemmaBackendRaw: String {
        didSet { UserDefaults.standard.set(gemmaBackendRaw, forKey: "gemma_backend") }
    }
    @Published var gemmaServerURL: String {
        didSet { UserDefaults.standard.set(gemmaServerURL, forKey: "gemma_server_url") }
    }
    @Published var geminiKey: String {
        didSet { UserDefaults.standard.set(geminiKey, forKey: "gemini_api_key") }
    }
    var gemmaBackend: GemmaBackend { GemmaBackend(rawValue: gemmaBackendRaw) ?? .off }

    private var fileURL: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("custom_background.jpg")
    }

    private init() {
        let d = UserDefaults.standard
        gemmaBackendRaw = d.string(forKey: "gemma_backend") ?? GemmaBackend.off.rawValue
        gemmaServerURL = d.string(forKey: "gemma_server_url") ?? "http://172.20.10.2:8080"
        geminiKey = d.string(forKey: "gemini_api_key") ?? ""
        if let data = try? Data(contentsOf: fileURL) {
            customBackground = UIImage(data: data)
        }
    }

    func setBackground(_ data: Data) {
        guard let img = UIImage(data: data) else { return }
        customBackground = img
        try? data.write(to: fileURL, options: .atomic)
    }

    func resetBackground() {
        customBackground = nil
        try? FileManager.default.removeItem(at: fileURL)
    }
}
