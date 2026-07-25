//  EncoreTheme.swift
//  Encore
//
//  Design tokens (typography, radii, spacing, palette) used by the playlist
//  page. Ported to a standalone codebase with no external dependencies.

import SwiftUI

enum Theme {

    // MARK: - Palette

    enum Palette {
        /// Warm creamy off-white — used only as a fallback if the background
        /// image is missing.
        static let cream = Color(hex: 0xFAF9F5)

        /// Light green accent used as a tint on the summary card.
        static let accentGreen = Color(hex: 0x93D76E)
    }

    // MARK: - Corner radii

    enum Radius {
        static let card: CGFloat = 20
        static let action: CGFloat = 26
    }

    // MARK: - Spacing scale

    enum Space {
        static let screenH: CGFloat = 24
        static let screenTop: CGFloat = 10
    }

    // MARK: - Typography

    enum Font {
        static func display(_ size: CGFloat) -> SwiftUI.Font {
            .system(size: size, weight: .bold, design: .rounded).leading(.tight)
        }
        static func title(_ size: CGFloat) -> SwiftUI.Font {
            .system(size: size, weight: .semibold, design: .rounded)
        }
        static func body(_ size: CGFloat, weight: SwiftUI.Font.Weight = .regular) -> SwiftUI.Font {
            .system(size: size, weight: weight, design: .rounded)
        }
        static func label(_ size: CGFloat, weight: SwiftUI.Font.Weight = .semibold) -> SwiftUI.Font {
            .system(size: size, weight: weight, design: .rounded)
        }
    }
}

// MARK: - Hex convenience

extension Color {
    /// Build a color from a 0xRRGGBB integer.
    init(hex: UInt32, opacity: Double = 1) {
        let r = Double((hex >> 16) & 0xFF) / 255
        let g = Double((hex >> 8) & 0xFF) / 255
        let b = Double(hex & 0xFF) / 255
        self = Color(.sRGB, red: r, green: g, blue: b, opacity: opacity)
    }
}
