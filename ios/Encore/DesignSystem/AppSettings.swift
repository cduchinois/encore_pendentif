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

    private var fileURL: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("custom_background.jpg")
    }

    private init() {
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
