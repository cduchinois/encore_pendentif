//  EncoreBackground.swift
//  Encore
//
//  Warm photographic backdrop with a gradient veil, used behind the playlist
//  page. Standalone: only depends on Theme + the "BackgroundImage" asset.

import SwiftUI

struct EncoreBackground: View {
    var darken: Bool

    var body: some View {
        // GeometryReader with `.ignoresSafeArea()` on the outside reports the
        // full window size (safe-area extension included). We set the image
        // frame to that explicit height so `.aspectRatio(.fill)` scales based
        // on the full screen height — the width overshoots for tall
        // containers and gets clipped. Fits background to full height, lets
        // the width bleed off-screen.
        GeometryReader { proxy in
            Image("BackgroundImage")
                .resizable()
                .aspectRatio(contentMode: .fill)
                .frame(width: proxy.size.width, height: proxy.size.height)
                .frame(width: proxy.size.width, height: proxy.size.height, alignment: .center)
                .clipped()
                .background(Theme.Palette.cream)
                .overlay(
                    LinearGradient(
                        stops: [
                            .init(color: Color(hex: 0xFFFAE4).opacity(0.30), location: 0),
                            .init(color: .white.opacity(0), location: 0.24),
                            .init(color: Color(hex: 0x163026).opacity(0.04), location: 0.62),
                            .init(color: Color(hex: 0x163026).opacity(0.20), location: 1),
                        ],
                        startPoint: .top, endPoint: .bottom)
                )
                .overlay(
                    darken
                        ? LinearGradient(
                            stops: [
                                .init(color: Color(hex: 0x12281C).opacity(0.55), location: 0),
                                .init(color: Color(hex: 0x142A1E).opacity(0.34), location: 0.4),
                                .init(color: Color(hex: 0x102419).opacity(0.52), location: 1),
                            ],
                            startPoint: .top, endPoint: .bottom)
                        : nil
                )
        }
        .ignoresSafeArea()
    }
}
