# iOS app — setup (one-time, on the Mac)

The .xcodeproj is not committed (create it locally, 5 min):
1. Xcode -> New Project -> iOS App "Encore", SwiftUI, bundle id dev.encore.app. Save in ios/ (replace this folder's Encore/ with the generated one, then copy the stub .swift files back in).
2. Signing: Personal Team (free Apple ID) — app valid 7 days, install the evening before. Enable Developer Mode on the iPhone.
3. Capabilities: Background Modes (Uses BLE accessories), MusicKit. Add ShazamKit.framework.
4. For Gemma: add llama.cpp swift package (or MediaPipe LLM pod) + the E2B GGUF in app resources.
Stubs in Encore/ show the intended module layout; each file lists its TODO.
