//  PhonePage.swift
//  Encore
//
//  "Phone" page: recognition through the iPhone's own microphone, for working
//  without a pendant (Mathieu's rig). Same design language as the other
//  pages, same matcher and journal underneath.

import SwiftUI

struct PhonePage: View {
    @ObservedObject var stage: RecognitionStage
    @ObservedObject var journal: SessionStore

    init(stage: RecognitionStage) {
        self.stage = stage
        self.journal = stage.journal
    }

    var body: some View {
        ZStack {
            EncoreBackground(darken: true)

            ScrollView(showsIndicators: false) {
                LazyVStack(spacing: 14) {
                    header
                        .padding(.bottom, 4)

                    micCard
                        .padding(.bottom, 8)

                    setlistSectionHeader
                        .padding(.bottom, 2)

                    if journal.playlistTracks.isEmpty {
                        emptySetlist
                    } else {
                        SetlistTimeline(tracks: journal.playlistTracks)
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

            Text("Phone")
                .font(Theme.Font.display(30))
                .foregroundStyle(.white)
                .shadow(color: .black.opacity(0.30), radius: 14, y: 2)

            Text(stage.micActive ? "micro iPhone · en écoute"
                                 : "micro iPhone · sans pendentif")
                .font(Theme.Font.body(13))
                .foregroundStyle(.white.opacity(0.82))
                .shadow(color: .black.opacity(0.25), radius: 6, y: 1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    // MARK: Mic card (mirror of the capture vibe card)

    private var micCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 8) {
                Image(systemName: "mic")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(.white.opacity(0.9))
                Text("MICRO IPHONE")
                    .font(Theme.Font.label(11, weight: .heavy))
                    .tracking(1.4)
                    .foregroundStyle(.white.opacity(0.85))
                Spacer(minLength: 0)
                if !stage.matcherReady {
                    Image(systemName: "hourglass")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(.white.opacity(0.75))
                } else {
                    Image(systemName: "dot.radiowaves.left.and.right")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(stage.micActive ? Theme.Palette.accentGreen : .white.opacity(0.4))
                }
            }

            LiveWaveform(values: stage.micRMS, barCount: 42, height: 44)
                .frame(height: 44)

            Button {
                stage.micActive ? stage.stopMic() : stage.startMic()
            } label: {
                HStack(spacing: 10) {
                    Image(systemName: stage.micActive ? "stop.fill" : "mic.fill")
                        .font(.system(size: 14, weight: .semibold))
                    Text(stage.micActive ? "Stop" : "Écouter")
                        .font(Theme.Font.label(15, weight: .semibold))
                }
                .foregroundStyle(.white)
                .frame(maxWidth: .infinity)
                .frame(height: 48)
            }
            .glassEffect(.clear.interactive(),
                         in: RoundedRectangle(cornerRadius: Theme.Radius.action, style: .continuous))
        }
        .padding(24)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.Palette.accentGreen.opacity(0.32), in: RoundedRectangle(cornerRadius: 32))
        .glassEffect(.clear.interactive(), in: RoundedRectangle(cornerRadius: 32))
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
        Text(stage.micActive ? "En écoute — le premier match arrive…"
                             : "Appuie sur Écouter et joue un morceau.")
            .font(Theme.Font.body(13))
            .foregroundStyle(.white.opacity(0.6))
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.top, 6)
    }
}
