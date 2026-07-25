//  ClipPlayer.swift
//  Encore
//
//  Plays back a captured unknown-track excerpt from a setlist card. One clip
//  at a time; .playAndRecord keeps the mic path alive if Phone is listening
//  (heads-up: the mic will hear the excerpt — pause Listen while replaying).

import SwiftUI
import AVFoundation
import Combine

final class ClipPlayer: NSObject, ObservableObject, AVAudioPlayerDelegate {
    static let shared = ClipPlayer()

    @Published var playingURL: URL? = nil
    private var player: AVAudioPlayer?

    func toggle(_ url: URL) {
        if playingURL == url { stop(); return }
        stop()
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.playAndRecord, options: [.defaultToSpeaker])
        try? session.setActive(true)
        guard let p = try? AVAudioPlayer(contentsOf: url) else { return }
        p.delegate = self
        player = p
        p.play()
        playingURL = url
    }

    func stop() {
        player?.stop()
        player = nil
        playingURL = nil
    }

    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        DispatchQueue.main.async { self.stop() }
    }
}

/// Small glass pill inside an unknown card — play/stop the captured excerpt.
struct PlayClipButton: View {
    let url: URL
    @ObservedObject private var player = ClipPlayer.shared

    private var isPlaying: Bool { player.playingURL == url }

    var body: some View {
        Button {
            player.toggle(url)
        } label: {
            HStack(spacing: 6) {
                Image(systemName: isPlaying ? "stop.fill" : "play.fill")
                    .font(.system(size: 10, weight: .semibold))
                Text(isPlaying ? "Stop" : "Écouter l'extrait")
                    .font(Theme.Font.label(11, weight: .semibold))
            }
            .foregroundStyle(.white.opacity(0.9))
            .padding(.horizontal, 12)
            .padding(.vertical, 7)
            .background(.white.opacity(isPlaying ? 0.18 : 0.10), in: Capsule())
        }
        .buttonStyle(.plain)
    }
}
