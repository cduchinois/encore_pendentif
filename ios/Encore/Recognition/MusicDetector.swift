//  MusicDetector.swift
//  Encore
//
//  Music vs speech/noise, on-device, via Apple's built-in sound classifier
//  (SoundAnalysis, ~300 classes). Answers one question per audio chunk:
//  "is what we hear actually music?" — gates the unknown-track logic so
//  conversations and crowd noise never create journal entries.

import Foundation
import AVFoundation
import SoundAnalysis

final class MusicDetector: NSObject, SNResultsObserving {
    private var analyzer: SNAudioStreamAnalyzer?
    private var framePosition: AVAudioFramePosition = 0
    private var recentMusic: [Double] = []

    /// Smoothed decision over the last few windows (hysteresis against
    /// one-off classifier blips).
    var isMusic: Bool {
        guard !recentMusic.isEmpty else { return false }
        return recentMusic.reduce(0, +) / Double(recentMusic.count) > 0.45
    }

    func start(format: AVAudioFormat) {
        let a = SNAudioStreamAnalyzer(format: format)
        do {
            let request = try SNClassifySoundRequest(classifierIdentifier: .version1)
            try a.add(request, withObserver: self)
            analyzer = a
        } catch {
            print("MusicDetector unavailable (\(error)) — treating everything as music")
            recentMusic = [1]
        }
    }

    func analyze(_ buffer: AVAudioPCMBuffer) {
        analyzer?.analyze(buffer, atAudioFramePosition: framePosition)
        framePosition += AVAudioFramePosition(buffer.frameLength)
    }

    // MARK: SNResultsObserving

    func request(_ request: SNRequest, didProduce result: SNResult) {
        guard let r = result as? SNClassificationResult else { return }
        let music = r.classification(forIdentifier: "music")?.confidence ?? 0
        recentMusic.append(music)
        if recentMusic.count > 4 { recentMusic.removeFirst(recentMusic.count - 4) }
    }

    func request(_ request: SNRequest, didFailWithError error: Error) {
        print("MusicDetector error: \(error)")
    }
}
