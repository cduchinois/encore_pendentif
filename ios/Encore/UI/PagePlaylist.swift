//  PagePlaylist.swift
//  Encore
//
//  Standalone demo page — musical recap of a DJ set with a scrollable
//  timeline of identified tracks. Uses only the local design system
//  (`Theme.Radius`, `Theme.Font`) and the native iOS 26 Liquid Glass API
//  (`.glassEffect(.clear.interactive())`).

import SwiftUI

struct PagePlaylist: View {

    // MARK: Inputs

    var tracks: [PlaylistTrack] = PlaylistDemoData.tracks
    var label: String = PlaylistDemoData.label
    var title: String = PlaylistDemoData.title
    var subtitle: String = PlaylistDemoData.subtitle
    var venue: String = PlaylistDemoData.venue
    var averageBPM: Int = PlaylistDemoData.averageBPM

    /// Optional close closure — when set, a dismiss button appears in the
    /// header. Without it, no button is added — the page enforces no
    /// navigation contract.
    var onClose: (() -> Void)?
    var onGenerate: (() -> Void)?

    var body: some View {
        ZStack(alignment: .bottom) {
            scrollBody
            floatingCTA
        }
    }

    // MARK: Scroll

    private var scrollBody: some View {
        ScrollView(showsIndicators: false) {
            LazyVStack(spacing: 14) {
                header
                    .padding(.bottom, 4)

                summaryCard
                    .padding(.bottom, 8)

                setlistSectionHeader
                    .padding(.bottom, 2)

                SetlistTimeline(tracks: tracks)
            }
            .padding(.horizontal, Theme.Space.screenH)
            .padding(.top, Theme.Space.screenTop)
            // Let the list extend behind the floating CTA.
            .padding(.bottom, 140)
        }
    }

    // MARK: Setlist section header ("La setlist · extrait · X → Y")

    private var setlistSectionHeader: some View {
        HStack(alignment: .firstTextBaseline) {
            Text("La setlist")
                .font(Theme.Font.title(18))
                .foregroundStyle(.white)
                .shadow(color: .black.opacity(0.25), radius: 6, y: 1)
            Spacer(minLength: 8)
            Text("extrait · \(setlistRange)")
                .font(Theme.Font.label(12, weight: .semibold))
                .foregroundStyle(.white.opacity(0.68))
                .monospacedDigit()
                .shadow(color: .black.opacity(0.2), radius: 5, y: 1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var setlistRange: String {
        let first = tracks.first?.timestamp ?? "--:--"
        let last  = tracks.last?.timestamp  ?? "--:--"
        return "\(first) \u{2192} \(last)"
    }

    // MARK: Header

    private var header: some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(alignment: .leading, spacing: 6) {
                Text(label)
                    .font(Theme.Font.label(11, weight: .heavy))
                    .tracking(2.4)
                    .foregroundStyle(.white.opacity(0.78))
                    .shadow(color: .black.opacity(0.25), radius: 6, y: 1)

                Text(title)
                    .font(Theme.Font.display(30))
                    .foregroundStyle(.white)
                    .shadow(color: .black.opacity(0.30), radius: 14, y: 2)
                    .fixedSize(horizontal: false, vertical: true)

                Text("\(subtitle) · \(venue)")
                    .font(Theme.Font.body(13))
                    .foregroundStyle(.white.opacity(0.82))
                    .shadow(color: .black.opacity(0.25), radius: 6, y: 1)
            }

            Spacer(minLength: 0)

            if let onClose {
                // `.glassEffect(.clear.interactive())` directly on the Button:
                // no buttonStyle, no custom animation. The "drop" on click is
                // the native iOS 26 `.interactive()` behavior.
                Button(action: onClose) {
                    Image(systemName: "xmark")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(.white)
                        .frame(width: 38, height: 38)
                        .contentShape(Circle())
                }
                .glassEffect(.clear.interactive(), in: Circle())
                .accessibilityLabel("Fermer")
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    // MARK: Summary card

    private var summaryCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 8) {
                Image(systemName: "waveform")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(.white.opacity(0.9))
                Text("SESSION LIVE")
                    .font(Theme.Font.label(11, weight: .heavy))
                    .tracking(1.4)
                    .foregroundStyle(.white.opacity(0.85))
                Spacer(minLength: 0)
                Image(systemName: "dot.radiowaves.left.and.right")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(.white.opacity(0.75))
            }

            PlaylistWaveform(barCount: 42, height: 44)
                .frame(height: 44)

            HStack(spacing: 0) {
                summaryStat(value: "\(tracks.count)", label: "tracks")
                statDivider
                summaryStat(value: subtitleValue, label: "durée")
                statDivider
                summaryStat(value: "\(averageBPM)", label: "avg bpm")
            }
        }
        .padding(24)
        .frame(maxWidth: .infinity, alignment: .leading)
        // Green tint under a Liquid Glass clear layer — reads as bright vs
        // the dark forest backdrop.
        .background(Theme.Palette.accentGreen.opacity(0.32), in: RoundedRectangle(cornerRadius: 32))
        .glassEffect(.clear.interactive(), in: RoundedRectangle(cornerRadius: 32))
    }

    private var subtitleValue: String {
        // "DJ Set · 1 h 24 min" -> "1h24"
        "1h24"
    }

    private func summaryStat(value: String, label: String) -> some View {
        VStack(spacing: 3) {
            Text(value)
                .font(Theme.Font.label(18, weight: .bold))
                .foregroundStyle(.white)
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

    // MARK: Floating CTA

    private var floatingCTA: some View {
        // `.glassEffect(.clear.interactive())` directly on the Button.
        // Shadow lives on the label. The "drop" on click is the native iOS 26
        // `.interactive()` behavior.
        Button {
            onGenerate?()
        } label: {
            HStack(spacing: 10) {
                Image(systemName: "wand.and.stars")
                    .font(.system(size: 15, weight: .semibold))
                Text("Générer une playlist")
                    .font(Theme.Font.label(16, weight: .semibold))
            }
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .frame(height: 58)
            .padding(.horizontal, 20)
            .shadow(color: .black.opacity(0.22), radius: 14, y: 8)
        }
        .glassEffect(
            .clear.interactive(),
            in: RoundedRectangle(cornerRadius: Theme.Radius.action, style: .continuous)
        )
        .accessibilityLabel("Générer une playlist")
        .padding(.horizontal, 20)
        .padding(.bottom, 8)
    }
}

// MARK: - Timeline

/// Vertical timeline: continuous rail + dots at each timestamp + track cards
/// on the right. Rail is a single Rectangle drawn behind all rows (via
/// ZStack) so it never breaks between rows.
private struct SetlistTimeline: View {

    let tracks: [PlaylistTrack]

    /// Horizontal rail position (from the timeline's leading edge).
    /// Timestamp column = 46pt, dot centered in the 20pt that follow.
    private let timestampColumnWidth: CGFloat = 46
    private let dotColumnWidth: CGFloat = 20

    private var railX: CGFloat { timestampColumnWidth + dotColumnWidth / 2 }

    var body: some View {
        ZStack(alignment: .topLeading) {
            // Vertical rail — stretches to VStack size (rows dominate the
            // ZStack height). Dots are drawn on top.
            Rectangle()
                .fill(Color.white.opacity(0.18))
                .frame(width: 1)
                .offset(x: railX)
                .padding(.vertical, 10)

            VStack(spacing: 10) {
                ForEach(tracks) { track in
                    TimelineTrackRow(
                        track: track,
                        timestampColumnWidth: timestampColumnWidth,
                        dotColumnWidth: dotColumnWidth
                    )
                    .transition(.opacity.combined(with: .move(edge: .bottom)))
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct TimelineTrackRow: View {
    let track: PlaylistTrack
    let timestampColumnWidth: CGFloat
    let dotColumnWidth: CGFloat

    /// The dot only reflects `isPlaying`. The pinned state is rendered as an
    /// aurora outline on the card, not on the dot.
    private var dotStyle: TimelineDotStyle {
        track.isPlaying ? .playing : .standard
    }

    var body: some View {
        HStack(alignment: .top, spacing: 0) {
            // Column 1: timestamp, right-aligned inside a STRICT width (no
            // trailing padding — that would shift the dot column and
            // misalign the dot center with the rail).
            Text(track.timestamp)
                .font(Theme.Font.label(12, weight: .semibold))
                .foregroundStyle(.white.opacity(0.65))
                .monospacedDigit()
                .shadow(color: .black.opacity(0.2), radius: 4, y: 1)
                .frame(width: timestampColumnWidth, alignment: .trailing)
                .padding(.top, 14) // baseline-aligned with the card title

            // Column 2: dot on the rail — STRICT width = dotColumnWidth,
            // dot centered ⇒ its center is exactly at
            // `timestampColumnWidth + dotColumnWidth / 2` = railX.
            // Two states: pulse (playing), standard.
            TimelineDot(style: dotStyle)
                .frame(width: dotColumnWidth)
                .padding(.top, 16) // aligns dot with the title line

            // Column 3: track card — the visual gap between dot and card
            // lives here (leading padding only) so previous columns don't
            // shift.
            trackCard
                .padding(.leading, 10)
        }
    }

    private var trackCard: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(track.title)
                .font(Theme.Font.body(15, weight: .semibold))
                .foregroundStyle(.white)
                .lineLimit(2)
                .fixedSize(horizontal: false, vertical: true)

            Text(track.artist)
                .font(Theme.Font.body(13))
                .foregroundStyle(.white.opacity(0.72))
                .lineLimit(1)

            if metaLine.isEmpty == false {
                Text(metaLine)
                    .font(Theme.Font.label(11, weight: .semibold))
                    .foregroundStyle(.white.opacity(0.6))
                    .lineLimit(1)
                    .padding(.top, 2)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
        .frame(maxWidth: .infinity, alignment: .leading)
        // Subtle tint as fill + interactive Liquid Glass CLEAR on top.
        // No stroke overlay — the rim comes naturally from the glass.
        .background(
            Color.white.opacity(0.05),
            in: RoundedRectangle(cornerRadius: Theme.Radius.card, style: .continuous)
        )
        .glassEffect(
            .clear.interactive(),
            in: RoundedRectangle(cornerRadius: Theme.Radius.card, style: .continuous)
        )
        .overlay {
            if track.isPinned {
                // Rainbow aurora glow around the whole card.
                AuroraBorder(cornerRadius: Theme.Radius.card)
            }
        }
    }

    /// Meta line: "126 BPM · 5:20" — gracefully omits missing fields.
    private var metaLine: String {
        var parts: [String] = []
        if let bpm = track.bpm { parts.append("\(bpm) BPM") }
        if let d = track.duration { parts.append(d) }
        return parts.joined(separator: " · ")
    }
}

// MARK: - Waveform

/// Decorative waveform built from vertical capsules. Not tied to real audio —
/// this is a visual pulse that breathes.
private struct PlaylistWaveform: View {
    var barCount: Int
    var height: CGFloat

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        Group {
            if reduceMotion {
                staticBars
            } else {
                TimelineView(.animation(minimumInterval: 1.0 / 30.0)) { tl in
                    let t = tl.date.timeIntervalSinceReferenceDate
                    bars(phase: t)
                }
            }
        }
        .allowsHitTesting(false)
    }

    private var staticBars: some View {
        HStack(alignment: .center, spacing: 3) {
            ForEach(0..<barCount, id: \.self) { i in
                Capsule()
                    .fill(barGradient)
                    .frame(width: 3, height: max(6, height * envelope(i)))
            }
        }
        .frame(maxWidth: .infinity)
    }

    private func bars(phase: Double) -> some View {
        HStack(alignment: .center, spacing: 3) {
            ForEach(0..<barCount, id: \.self) { i in
                let localPhase = Double(i) * 0.32
                let s = sin(phase * 1.6 + localPhase) * 0.5 + 0.5
                let h = 0.22 + 0.78 * s * envelope(i)
                Capsule()
                    .fill(barGradient)
                    .frame(width: 3, height: max(4, CGFloat(h) * height))
            }
        }
        .frame(maxWidth: .infinity)
    }

    /// Soft envelope: taller in the center, shorter at the edges.
    private func envelope(_ i: Int) -> Double {
        let x = Double(i) / Double(max(1, barCount - 1))
        return 0.45 + 0.55 * sin(.pi * x)
    }

    private var barGradient: LinearGradient {
        LinearGradient(
            colors: [
                Color.white.opacity(0.55),
                Color.white.opacity(0.95)
            ],
            startPoint: .bottom,
            endPoint: .top
        )
    }
}

// MARK: - Timeline dot

/// Shared pastel palette for the aurora (Apple-Intelligence-style).
private let auroraColors: [Color] = [
    Color(hex: 0xFFCDA0),
    Color(hex: 0xFFB4CE),
    Color(hex: 0xE0B4FF),
    Color(hex: 0xB4C7FF),
    Color(hex: 0xA6F0D9),
    Color(hex: 0xFFF3B4),
    Color(hex: 0xFFCDA0)
]

private enum TimelineDotStyle {
    case standard
    case playing     // pulsing dot — "live"
}

/// Single rail dot — switches between two renders based on `style`. Neither
/// captures touch, both respect Reduce Motion.
private struct TimelineDot: View {
    let style: TimelineDotStyle

    var body: some View {
        Group {
            switch style {
            case .standard: StandardDot()
            case .playing:  PulsingDot()
            }
        }
        .allowsHitTesting(false)
    }
}

/// Discrete default dot — translucent ring + crisp white core.
private struct StandardDot: View {
    var body: some View {
        ZStack {
            Circle()
                .fill(Color.white.opacity(0.35))
                .frame(width: 12, height: 12)
            Circle()
                .fill(Color.white)
                .frame(width: 6, height: 6)
                .shadow(color: .white.opacity(0.6), radius: 4)
        }
    }
}

/// Aurora border — pastel angular gradient rotating around the
/// RoundedRectangle. Three layers (wide blurred halo, mid blurred halo,
/// crisp rim) for a real overflowing glow. Respects Reduce Motion.
private struct AuroraBorder: View {
    var cornerRadius: CGFloat

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        Group {
            if reduceMotion {
                content(angle: 0)
            } else {
                TimelineView(.animation) { tl in
                    let period: Double = 8
                    let phase = tl.date.timeIntervalSinceReferenceDate
                        .truncatingRemainder(dividingBy: period) / period
                    content(angle: phase * 360)
                }
            }
        }
        .allowsHitTesting(false)
    }

    private func content(angle: Double) -> some View {
        let shape = RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
        let gradient = AngularGradient(
            colors: auroraColors,
            center: .center,
            startAngle: .degrees(angle),
            endAngle: .degrees(angle + 360)
        )
        return ZStack {
            // Wide blurred halo — the main light overflow.
            shape
                .stroke(gradient, lineWidth: 14)
                .blur(radius: 14)
                .opacity(0.55)
            // Mid halo — carries the intensity.
            shape
                .stroke(gradient, lineWidth: 6)
                .blur(radius: 4)
                .opacity(0.85)
            // Crisp rim — final contour.
            shape
                .stroke(gradient, lineWidth: 1.2)
                .opacity(0.95)
        }
    }
}

/// Pulsing "live" dot — expanding ring that fades out (sonar) + core that
/// breathes.
private struct PulsingDot: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        if reduceMotion {
            frame(ringScale: 1.0, ringOpacity: 0.0, corePulse: 0.5)
        } else {
            TimelineView(.animation) { tl in
                let period: Double = 1.6
                let p = tl.date.timeIntervalSinceReferenceDate
                    .truncatingRemainder(dividingBy: period) / period
                // Ring: grows from 1× to ~2.6×, opacity 1 → 0.
                let ringScale = 1.0 + 1.6 * p
                let ringOpacity = 1.0 - p
                // Core: gentle oscillation via sin(2π·p).
                let corePulse = 0.5 + 0.5 * sin(p * 2 * .pi)
                frame(ringScale: ringScale, ringOpacity: ringOpacity, corePulse: corePulse)
            }
        }
    }

    private func frame(ringScale: Double, ringOpacity: Double, corePulse: Double) -> some View {
        ZStack {
            // Sonar: ring propagating outward.
            Circle()
                .stroke(Color.white.opacity(0.65), lineWidth: 1.5)
                .frame(width: 10, height: 10)
                .scaleEffect(ringScale)
                .opacity(ringOpacity)
            // Base translucent ring (same as the standard dot).
            Circle()
                .fill(Color.white.opacity(0.35))
                .frame(width: 12, height: 12)
            // Breathing core — size + halo modulated by corePulse.
            Circle()
                .fill(Color.white)
                .frame(width: 6, height: 6)
                .scaleEffect(0.9 + 0.25 * corePulse)
                .shadow(
                    color: .white.opacity(0.5 + 0.5 * corePulse),
                    radius: 4 + 5 * corePulse
                )
        }
    }
}

// MARK: - Preview container

/// Forest backdrop container used for previews and demo full-screen covers.
/// PagePlaylist itself stays transparent and inherits the parent's
/// background — the container decides.
struct PlaylistPreviewContainer<Content: View>: View {
    @ViewBuilder var content: Content

    var body: some View {
        ZStack {
            EncoreBackground(darken: true)

            content
        }
    }
}

// MARK: - Preview

#Preview("PagePlaylist — forest backdrop") {
    PlaylistPreviewContainer {
        PagePlaylist(onClose: {}, onGenerate: {})
    }
}

#Preview("PagePlaylist — no close button") {
    PlaylistPreviewContainer {
        PagePlaylist()
    }
}
