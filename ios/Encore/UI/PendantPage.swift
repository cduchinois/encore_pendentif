//  PendantPage.swift
//  Encore
//
//  "Pendant" page, same design language as DemoPage:
//  - "CAPTURE VIBE" card = the summary card, fed by the real pendant stream
//    (waveform + connection/battery/loss stats)
//  - the setlist timeline = SetlistTimeline, fed by the journal's
//    track_match events instead of demo data.

import SwiftUI

struct PendantPage: View {
    @ObservedObject var stage: RecognitionStage
    @ObservedObject var receiver: UDPAudioReceiver
    @ObservedObject var pipeline: CapturePipeline
    @ObservedObject var journal: SessionStore

    init(stage: RecognitionStage) {
        self.stage = stage
        self.receiver = stage.receiver
        self.pipeline = stage.pendant
        self.journal = stage.pendant.journal
    }

    var body: some View {
        ZStack {
            EncoreBackground(darken: true)

            ScrollView(showsIndicators: false) {
                LazyVStack(spacing: 14) {
                    header
                        .padding(.bottom, 4)

                    captureVibeCard
                        .padding(.bottom, 8)

                    setlistSectionHeader
                        .padding(.bottom, 2)

                    if journal.playlistTracks.isEmpty {
                        emptySetlist
                    } else {
                        SetlistTimeline(tracks: journal.playlistTracks) { track in
                            pipeline.pin(trackID: track.catalogID)
                        }
                    }
                }
                .padding(.horizontal, Theme.Space.screenH)
                .padding(.top, Theme.Space.screenTop)
                .padding(.bottom, 40)
            }
        }
    }

    // MARK: Header

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("ENCORE")
                .font(Theme.Font.label(11, weight: .heavy))
                .tracking(2.4)
                .foregroundStyle(.white.opacity(0.78))
                .shadow(color: .black.opacity(0.25), radius: 6, y: 1)

            Text("Pendant")
                .font(Theme.Font.display(30))
                .foregroundStyle(.white)
                .shadow(color: .black.opacity(0.30), radius: 14, y: 2)

            Text(headerSubtitle)
                .font(Theme.Font.body(13))
                .foregroundStyle(.white.opacity(0.82))
                .shadow(color: .black.opacity(0.25), radius: 6, y: 1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var headerSubtitle: String {
        let date = journal.startedAt.formatted(date: .abbreviated, time: .shortened)
        if stage.privacy { return "\(date) · privacy" }
        return connected ? "\(date) · en direct" : "\(date) · pendentif en attente"
    }

    // MARK: Capture vibe card (mirror of DemoPage's summary card)

    private var connected: Bool {
        guard let t = receiver.lastPacketAt else { return false }
        return Date().timeIntervalSince(t) < 8
    }

    private var captureVibeCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 8) {
                Image(systemName: "waveform")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(.white.opacity(0.9))
                Text("CAPTURE VIBE")
                    .font(Theme.Font.label(11, weight: .heavy))
                    .tracking(1.4)
                    .foregroundStyle(.white.opacity(0.85))
                Spacer(minLength: 0)
                if stage.privacy {
                    Image(systemName: "hand.raised.fill")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(.orange)
                } else if !stage.matcherReady {
                    Image(systemName: "hourglass")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(.white.opacity(0.75))
                } else {
                    Image(systemName: "dot.radiowaves.left.and.right")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(connected ? Theme.Palette.accentGreen : .white.opacity(0.4))
                }
            }

            LiveWaveform(values: receiver.rmsHistory, barCount: 42, height: 44)
                .frame(height: 44)

            HStack(spacing: 0) {
                summaryStat(value: "\(journal.playlistTracks.count)", label: "tracks")
                statDivider
                summaryStat(value: "\(receiver.framesPerSecond)", label: "fps")
                statDivider
                summaryStat(value: receiver.batteryPct >= 0 ? "\(receiver.batteryPct)%" : "--",
                            label: "battery")
            }
        }
        .padding(24)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.Palette.accentGreen.opacity(0.32), in: RoundedRectangle(cornerRadius: 32))
        .glassEffect(.clear.interactive(), in: RoundedRectangle(cornerRadius: 32))
    }

    private func summaryStat(value: String, label: String) -> some View {
        VStack(spacing: 3) {
            Text(value)
                .font(Theme.Font.label(18, weight: .bold))
                .foregroundStyle(.white)
                .monospacedDigit()
            Text(label.uppercased())
                .font(Theme.Font.label(10, weight: .semibold))
                .tracking(1.1)
                .foregroundStyle(.white.opacity(0.72))
        }
        .frame(maxWidth: .infinity)
    }

    private var statDivider: some View {
        Rectangle()
            .fill(Color.white.opacity(0.16))
            .frame(width: 1, height: 30)
    }

    // MARK: Setlist

    private var setlistSectionHeader: some View {
        HStack(alignment: .firstTextBaseline) {
            Text("La setlist")
                .font(Theme.Font.title(18))
                .foregroundStyle(.white)
                .shadow(color: .black.opacity(0.25), radius: 6, y: 1)
            Spacer(minLength: 8)
            Text("live · \(journal.playlistTracks.count) tracks")
                .font(Theme.Font.label(12, weight: .semibold))
                .foregroundStyle(.white.opacity(0.68))
                .monospacedDigit()
                .shadow(color: .black.opacity(0.2), radius: 5, y: 1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var emptySetlist: some View {
        Text(connected ? "En écoute — le premier match arrive…"
                       : "Allume le pendentif pour commencer la capture.")
            .font(Theme.Font.body(13))
            .foregroundStyle(.white.opacity(0.6))
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.top, 6)
    }
}

// MARK: - Live waveform

/// Same capsule look as DemoPage's decorative waveform, but driven by real
/// per-chunk RMS (pendant stream or iPhone mic). Shared by PendantPage and
/// PhonePage.
struct LiveWaveform: View {
    let values: [Float]
    var barCount: Int
    var height: CGFloat

    var body: some View {
        HStack(alignment: .center, spacing: 3) {
            ForEach(0..<barCount, id: \.self) { i in
                Capsule()
                    .fill(barGradient)
                    .frame(width: 3, height: max(4, CGFloat(level(i)) * height))
            }
        }
        .frame(maxWidth: .infinity)
        .allowsHitTesting(false)
    }

    /// Map the last `barCount` RMS values onto the bars, newest on the right.
    private func level(_ i: Int) -> Float {
        let missing = barCount - values.count
        let idx = values.count - barCount + i
        if i < missing || idx < 0 || idx >= values.count { return 0.08 }
        return min(0.15 + values[idx] * 6, 1)
    }

    private var barGradient: LinearGradient {
        LinearGradient(
            colors: [Color.white.opacity(0.55), Color.white.opacity(0.95)],
            startPoint: .bottom,
            endPoint: .top
        )
    }
}
