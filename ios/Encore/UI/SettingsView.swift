//  SettingsView.swift
//  Encore
//
//  Settings tab: the pendant's BLE link (status, forget) and a photo that
//  replaces the bundled background image across the whole app.

import SwiftUI
import PhotosUI

struct SettingsView: View {
    @ObservedObject private var settings = AppSettings.shared
    @ObservedObject var receiver: PendantBLEClient
    @State private var pickerItem: PhotosPickerItem?

    var body: some View {
        ZStack {
            EncoreBackground(darken: true)

            ScrollView(showsIndicators: false) {
                VStack(spacing: 14) {
                    header
                        .padding(.bottom, 4)

                    pendantCard

                    backgroundCard
                }
                .padding(.horizontal, Theme.Space.screenH)
                .padding(.top, Theme.Space.screenTop)
                .padding(.bottom, 40)
            }
        }
        .onChange(of: pickerItem) { _, item in
            guard let item else { return }
            Task {
                if let data = try? await item.loadTransferable(type: Data.self) {
                    await MainActor.run { settings.setBackground(data) }
                }
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

            Text("Réglages")
                .font(Theme.Font.display(30))
                .foregroundStyle(.white)
                .shadow(color: .black.opacity(0.30), radius: 14, y: 2)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    // MARK: Background card

    private var backgroundCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 8) {
                Image(systemName: "photo")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(.white.opacity(0.9))
                Text("FOND D'ÉCRAN")
                    .font(Theme.Font.label(11, weight: .heavy))
                    .tracking(1.4)
                    .foregroundStyle(.white.opacity(0.85))
                Spacer(minLength: 0)
                if settings.customBackground != nil {
                    Text("perso")
                        .font(Theme.Font.label(10, weight: .semibold))
                        .foregroundStyle(Theme.Palette.accentGreen)
                }
            }

            preview

            PhotosPicker(selection: $pickerItem, matching: .images) {
                HStack(spacing: 10) {
                    Image(systemName: "photo.badge.plus")
                        .font(.system(size: 14, weight: .semibold))
                    Text("Choisir une image")
                        .font(Theme.Font.label(15, weight: .semibold))
                }
                .foregroundStyle(.white)
                .frame(maxWidth: .infinity)
                .frame(height: 48)
            }
            .glassEffect(.clear.interactive(),
                         in: RoundedRectangle(cornerRadius: Theme.Radius.action, style: .continuous))

            if settings.customBackground != nil {
                Button {
                    settings.resetBackground()
                    pickerItem = nil
                } label: {
                    Text("Revenir au fond par défaut")
                        .font(Theme.Font.label(13, weight: .semibold))
                        .foregroundStyle(.white.opacity(0.75))
                        .frame(maxWidth: .infinity)
                        .frame(height: 40)
                }
                .glassEffect(.clear.interactive(),
                             in: RoundedRectangle(cornerRadius: Theme.Radius.action, style: .continuous))
            }
        }
        .padding(24)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 32))
        .glassEffect(.clear.interactive(), in: RoundedRectangle(cornerRadius: 32))
    }

    // MARK: Pendant card — the BLE link

    private var pendantCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 8) {
                Image(systemName: "dot.radiowaves.left.and.right")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(.white.opacity(0.9))
                Text("PENDENTIF")
                    .font(Theme.Font.label(11, weight: .heavy))
                    .tracking(1.4)
                    .foregroundStyle(.white.opacity(0.85))
                Spacer(minLength: 0)
                Text(pendantStatus)
                    .font(Theme.Font.label(10, weight: .semibold))
                    .foregroundStyle(receiver.state == .connected ? Theme.Palette.accentGreen
                                                                  : .white.opacity(0.6))
            }

            Text("Le pendentif se connecte en Bluetooth et se reconnecte tout seul. "
                 + "Oublie-le pour en associer un autre.")
                .font(Theme.Font.label(11))
                .foregroundStyle(.white.opacity(0.55))

            Button {
                receiver.forget()
            } label: {
                Text("Oublier ce pendentif")
                    .font(Theme.Font.label(13, weight: .semibold))
                    .foregroundStyle(.white.opacity(0.75))
                    .frame(maxWidth: .infinity)
                    .frame(height: 40)
            }
            .glassEffect(.clear.interactive(),
                         in: RoundedRectangle(cornerRadius: Theme.Radius.action, style: .continuous))
        }
        .padding(24)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 32))
        .glassEffect(.clear.interactive(), in: RoundedRectangle(cornerRadius: 32))
    }

    private var pendantStatus: String {
        switch receiver.state {
        case .off: return "bluetooth off"
        case .unauthorized: return "non autorisé"
        case .scanning: return "recherche…"
        case .connecting: return "connexion…"
        case .connected: return receiver.pendantName ?? "connecté"
        }
    }

    private var preview: some View {
        Group {
            if let custom = settings.customBackground {
                Image(uiImage: custom).resizable()
            } else {
                Image("BackgroundImage").resizable()
            }
        }
        .aspectRatio(contentMode: .fill)
        .frame(height: 150)
        .frame(maxWidth: .infinity)
        .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.card, style: .continuous))
    }
}
