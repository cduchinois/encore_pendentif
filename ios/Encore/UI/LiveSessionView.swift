//  LiveSessionView.swift
//  Encore
//
//  Gate 1-2 debug view: incoming pendant stream (waveform + stats) and the
//  live recognition state. Ugly on purpose — the pretty timeline is PagePlaylist.

import SwiftUI

struct LiveSessionView: View {
    @ObservedObject var stage: RecognitionStage
    @ObservedObject var receiver: UDPAudioReceiver
    @ObservedObject var journal: SessionStore

    init(stage: RecognitionStage) {
        self.stage = stage
        self.receiver = stage.receiver
        self.journal = stage.journal
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            statsRow
            waveform
            currentTrackCard
            eventsList
            Spacer()
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.black)
        .foregroundStyle(.white)
    }

    private var connected: Bool {
        guard let t = receiver.lastPacketAt else { return false }
        return Date().timeIntervalSince(t) < 8
    }

    private var statsRow: some View {
        HStack(spacing: 14) {
            Circle().fill(connected ? .green : .red).frame(width: 10, height: 10)
            Text(connected ? "pendant" : "waiting…")
            Text("\(receiver.framesPerSecond) fps")
            Text("lost \(receiver.lostFrames)")
            if receiver.batteryPct >= 0 { Text("bat \(receiver.batteryPct)%") }
            Text("\(receiver.rssi) dBm")
            if stage.privacy { Text("PRIVACY").foregroundStyle(.orange) }
            if !stage.matcherReady { Text("catalog…").foregroundStyle(.yellow) }
        }
        .font(.system(.footnote, design: .monospaced))
    }

    private var waveform: some View {
        Canvas { ctx, size in
            let vals = receiver.rmsHistory
            guard !vals.isEmpty else { return }
            let w = size.width / CGFloat(150)
            for (i, v) in vals.enumerated() {
                let h = max(2, CGFloat(min(v * 6, 1)) * size.height)
                let rect = CGRect(x: CGFloat(i) * w, y: (size.height - h) / 2,
                                  width: max(w - 1, 1), height: h)
                ctx.fill(Path(rect), with: .color(.cyan))
            }
        }
        .frame(height: 70)
        .background(.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 8))
    }

    private var currentTrackCard: some View {
        VStack(alignment: .leading, spacing: 4) {
            if let t = stage.currentTrack {
                Text(t.title).font(.title3.bold())
                Text(t.artist).foregroundStyle(.secondary)
                if let bpm = t.bpm { Text("\(Int(bpm)) BPM").font(.footnote).foregroundStyle(.secondary) }
            } else {
                Text("Listening…").font(.title3).foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
    }

    private var eventsList: some View {
        VStack(alignment: .leading, spacing: 3) {
            ForEach(journal.events.suffix(8).reversed(), id: \.ts_ms) { ev in
                HStack {
                    Text(String(format: "%6.1fs", Double(ev.ts_ms) / 1000))
                    Text(ev.kind.rawValue)
                    if let id = ev.track_id, let t = CatalogStore.shared.track(id) {
                        Text("· \(t.title)").lineLimit(1)
                    }
                }
                .font(.system(.caption, design: .monospaced))
                .foregroundStyle(ev.kind == .pin ? .yellow : .white.opacity(0.8))
            }
        }
    }
}
