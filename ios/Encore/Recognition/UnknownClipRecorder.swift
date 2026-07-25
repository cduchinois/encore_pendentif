//  UnknownClipRecorder.swift
//  Encore
//
//  Rolling 30 s memory of the audio stream (dashcam-style ring buffer).
//  When a pipeline opens an "unknown track", we freeze the ring into:
//   - a 16 kHz mono WAV clip (the payload for the Gemma ID card + tests)
//   - a ShazamKit reference signature (local indexing of the unknown)
//   - a DSP tempo estimate (BPM is measured, never guessed by the model —
//     rule from contracts/id_card.schema.json)

import Foundation
import AVFoundation
import ShazamKit

final class UnknownClipRecorder {

    struct Clip: Identifiable {
        let id = UUID()
        let wavURL: URL
        let signatureURL: URL?
        let bpm: Double?
        let duration: Double
        let capturedAt: Date
    }

    /// 60 chunks of 0.5 s = 30 s, the max Gemma 4 accepts.
    private let capacityChunks = 60
    private var ring: [[Float]] = []
    private let sampleRate: Double = 16000

    private static let dir: URL = {
        let d = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("unknown_clips", isDirectory: true)
        try? FileManager.default.createDirectory(at: d, withIntermediateDirectories: true)
        return d
    }()

    /// Called on the audio queue with every 0.5 s chunk (music or not — the
    /// ring always rolls; only the freeze is music-gated by the pipeline).
    func push(_ buffer: AVAudioPCMBuffer) {
        guard let ch = buffer.floatChannelData else { return }
        ring.append(Array(UnsafeBufferPointer(start: ch[0], count: Int(buffer.frameLength))))
        if ring.count > capacityChunks { ring.removeFirst(ring.count - capacityChunks) }
    }

    /// Snapshot the ring — MUST be called on the same queue as push()
    /// (the source's audio queue) so the copy is race-free.
    func snapshot() -> [Float] { ring.flatMap { $0 } }

    /// Freeze a snapshot into wav + signature + bpm. Any queue; returns nil
    /// if the snapshot is (nearly) empty.
    func freezeClip(from samples: [Float]) -> Clip? {
        guard samples.count > Int(sampleRate) * 5 else { return nil }   // < 5 s = not worth it

        // Recording diagnosis: a silent capture is a capture bug, loud and clear.
        var peak: Float = 0; var acc: Float = 0
        for s in samples { peak = max(peak, abs(s)); acc += s * s }
        let rms = (acc / Float(samples.count)).squareRoot()
        print(String(format: "UnknownClip: freezing %.1fs, peak=%.3f rms=%.3f%@",
                     Double(samples.count) / sampleRate, peak, rms,
                     peak < 0.01 ? "  ⚠️ CLIP QUASI SILENCIEUX" : ""))

        let stamp = Int(Date().timeIntervalSince1970)
        let wavURL = Self.dir.appendingPathComponent("unknown_\(stamp).wav")
        guard let format = AVAudioFormat(standardFormatWithSampleRate: sampleRate, channels: 1),
              let buf = AVAudioPCMBuffer(pcmFormat: format,
                                         frameCapacity: AVAudioFrameCount(samples.count)) else { return nil }
        buf.frameLength = AVAudioFrameCount(samples.count)
        samples.withUnsafeBufferPointer { buf.floatChannelData![0].update(from: $0.baseAddress!, count: samples.count) }

        do {
            let settings: [String: Any] = [
                AVFormatIDKey: kAudioFormatLinearPCM,
                AVSampleRateKey: sampleRate,
                AVNumberOfChannelsKey: 1,
                AVLinearPCMBitDepthKey: 16,
                AVLinearPCMIsFloatKey: false,
            ]
            let file = try AVAudioFile(forWriting: wavURL, settings: settings,
                                       commonFormat: .pcmFormatFloat32, interleaved: false)
            try file.write(from: buf)
        } catch {
            print("UnknownClip: wav write failed: \(error)")
            return nil
        }

        var sigURL: URL? = nil
        do {
            let gen = SHSignatureGenerator()
            try gen.append(buf, at: nil)
            let sig = try gen.signature()
            let u = wavURL.deletingPathExtension().appendingPathExtension("shazamsignature")
            try sig.dataRepresentation.write(to: u)
            sigURL = u
        } catch {
            print("UnknownClip: signature failed: \(error)")
        }

        let clip = Clip(wavURL: wavURL, signatureURL: sigURL,
                        bpm: Self.estimateBPM(samples, sampleRate: sampleRate),
                        duration: Double(samples.count) / sampleRate,
                        capturedAt: Date())
        print("UnknownClip: \(String(format: "%.1f", clip.duration))s frozen -> \(wavURL.lastPathComponent), bpm ~\(clip.bpm.map { String(Int($0)) } ?? "?")")
        return clip
    }

    // MARK: - Tempo (autocorrelation of the onset envelope, 60-180 BPM)

    static func estimateBPM(_ samples: [Float], sampleRate: Double) -> Double? {
        let frame = 512, hop = 256
        guard samples.count > frame * 8 else { return nil }
        var energy: [Float] = []
        var i = 0
        while i + frame <= samples.count {
            var e: Float = 0
            for j in i..<(i + frame) { e += samples[j] * samples[j] }
            energy.append(e)
            i += hop
        }
        // Onset envelope: positive energy flux.
        var flux = [Float](repeating: 0, count: energy.count)
        for k in 1..<energy.count { flux[k] = max(0, energy[k] - energy[k - 1]) }
        let mean = flux.reduce(0, +) / Float(flux.count)
        for k in 0..<flux.count { flux[k] -= mean }

        let envRate = sampleRate / Double(hop)                  // 62.5 Hz
        let minLag = Int(envRate * 60 / 180)                    // 180 BPM
        let maxLag = Int(envRate * 60 / 60)                     // 60 BPM
        guard flux.count > maxLag * 2 else { return nil }

        var bestLag = 0; var bestScore: Float = 0
        for lag in minLag...maxLag {
            var s: Float = 0
            for k in 0..<(flux.count - lag) { s += flux[k] * flux[k + lag] }
            if s > bestScore { bestScore = s; bestLag = lag }
        }
        guard bestLag > 0, bestScore > 0 else { return nil }
        return (60 * envRate / Double(bestLag)).rounded()
    }
}
