//  ClipPlayer.swift
//  Encore
//
//  Plays back a captured unknown-track excerpt from a setlist card.
//  Playback needs the .playback session category — incompatible with the
//  Phone mic capture, so we broadcast .encoreClipWillPlay and the stage
//  stops the mic first (also kills the replay->mic feedback loop).

import SwiftUI
import AVFoundation
import Combine

extension Notification.Name {
    static let encoreClipWillPlay = Notification.Name("encore.clipWillPlay")
}

final class ClipPlayer: NSObject, ObservableObject, AVAudioPlayerDelegate {
    static let shared = ClipPlayer()

    @Published var playingURL: URL? = nil
    private var player: AVAudioPlayer?

    func toggle(_ url: URL) {
        if playingURL == url { stop(); return }
        stop()
        // Synchronous on the main thread: the stage's mic capture stops
        // before we reconfigure the session.
        NotificationCenter.default.post(name: .encoreClipWillPlay, object: nil)
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(.playback)
            try session.setActive(true)
        } catch {
            print("ClipPlayer session error: \(error)")
        }
        do {
            let p = try AVAudioPlayer(contentsOf: url)
            p.delegate = self
            p.volume = 1
            player = p
            print("ClipPlayer: playing \(url.lastPathComponent), \(String(format: "%.1f", p.duration))s")
            p.play()
            playingURL = url
        } catch {
            print("ClipPlayer failed to open \(url.lastPathComponent): \(error)")
        }
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
