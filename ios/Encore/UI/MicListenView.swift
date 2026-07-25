//  MicListenView.swift
//  Encore
//
//  "Listen" tab: recognition through the iPhone's own microphone, for working
//  without a pendant (Mathieu's rig). Same matcher, same journal.

import SwiftUI

struct MicListenView: View {
    @ObservedObject var stage: RecognitionStage
    @ObservedObject var journal: SessionStore

    init(stage: RecognitionStage) {
        self.stage = stage
        self.journal = stage.journal
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Button {
                    stage.micActive ? stage.stopMic() : stage.startMic()
                } label: {
                    Label(stage.micActive ? "Stop" : "Listen",
                          systemImage: stage.micActive ? "stop.circle.fill" : "mic.circle.fill")
                        .font(.title3.bold())
                }
                .buttonStyle(.borderedProminent)
                .tint(stage.micActive ? .red : .green)
                if !stage.matcherReady {
                    Text("catalog…").font(.footnote).foregroundStyle(.yellow)
                }
                Spacer()
            }

            Canvas { ctx, size in
                let vals = stage.micRMS
                guard !vals.isEmpty else { return }
                let w = size.width / CGFloat(150)
                for (i, v) in vals.enumerated() {
                    let h = max(2, CGFloat(min(v * 6, 1)) * size.height)
                    let rect = CGRect(x: CGFloat(i) * w, y: (size.height - h) / 2,
                                      width: max(w - 1, 1), height: h)
                    ctx.fill(Path(rect), with: .color(.green))
                }
            }
            .frame(height: 70)
            .background(.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 8))

            VStack(alignment: .leading, spacing: 4) {
                if let t = stage.currentTrack {
                    Text(t.title).font(.title3.bold())
                    Text(t.artist).foregroundStyle(.secondary)
                    if let bpm = t.bpm { Text("\(Int(bpm)) BPM").font(.footnote).foregroundStyle(.secondary) }
                } else {
                    Text(stage.micActive ? "Listening…" : "Tap Listen, play a track")
                        .font(.title3).foregroundStyle(.secondary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
            .background(.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))

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
                    .foregroundStyle(.white.opacity(0.8))
                }
            }
            Spacer()
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.black)
        .foregroundStyle(.white)
    }
}
