//  LlamaRunner.swift
//  Encore
//
//  Produces the Gemma ID card (contracts/id_card.schema.json) for an unknown
//  clip. Two interchangeable backends behind one call:
//   - .llamaServer: llama.cpp `llama-server` running Gemma 4 E2B (Mac on the
//     hotspot during the hackathon; the embedded on-device build slots in
//     here later — same request shape, OpenAI-style with input_audio)
//   - .geminiAPI: Google Gemini as an online fallback (validated end-to-end
//     on the test clip)
//  BPM and ts_start_ms are injected from DSP/journal, never model-guessed.

import Foundation

enum GemmaBackend: String {
    case off
    case llamaServer
    case geminiAPI
}

struct LlamaRunner {
    var backend: GemmaBackend
    var serverURL: URL?          // llama-server base, e.g. http://172.20.10.2:8080
    var geminiKey: String?

    static let prompt = """
    You listen to a 20 second club recording. Return ONLY a JSON object with \
    keys: genre (string), description (string, one sentence), has_vocals \
    (boolean), confidence (number 0-1), lyrics_snippet (string or null, only \
    include words you clearly hear). Never guess a song title or artist name. \
    No text outside the JSON.
    """

    /// Runs the backend on the wav and returns a schema-shaped ID card.
    /// bpm/tsStartMs are stamped by the caller (DSP + journal clock).
    func idCard(forWav wavURL: URL, bpm: Double?, tsStartMs: Int) async throws -> IDCard {
        let audio = try Data(contentsOf: wavURL)
        let text: String
        switch backend {
        case .off:
            throw GemmaError.disabled
        case .llamaServer:
            text = try await callLlamaServer(audio: audio)
        case .geminiAPI:
            text = try await callGemini(audio: audio)
        }
        var card = try Self.parseCard(text)
        card.bpm = bpm
        card.ts_start_ms = tsStartMs
        card.clip_ref = wavURL.lastPathComponent
        return card
    }

    // MARK: llama.cpp server (OpenAI-style chat with input_audio)

    private func callLlamaServer(audio: Data) async throws -> String {
        guard let base = serverURL else { throw GemmaError.notConfigured }
        var req = URLRequest(url: base.appendingPathComponent("v1/chat/completions"))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.timeoutInterval = 120
        let body: [String: Any] = [
            "temperature": 1.0, "top_p": 0.95, "max_tokens": 512,
            "messages": [[
                "role": "user",
                "content": [
                    ["type": "text", "text": Self.prompt],
                    ["type": "input_audio",
                     "input_audio": ["data": audio.base64EncodedString(), "format": "wav"]],
                ],
            ]],
        ]
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, _) = try await URLSession.shared.data(for: req)
        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let choices = json["choices"] as? [[String: Any]],
              let msg = choices.first?["message"] as? [String: Any],
              let content = msg["content"] as? String else {
            throw GemmaError.badResponse(String(data: data.prefix(200), encoding: .utf8) ?? "")
        }
        return content
    }

    // MARK: Gemini API fallback

    private func callGemini(audio: Data) async throws -> String {
        guard let key = geminiKey, !key.isEmpty else { throw GemmaError.notConfigured }
        var req = URLRequest(url: URL(string:
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=\(key)")!)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.timeoutInterval = 90
        let body: [String: Any] = [
            "contents": [[
                "parts": [
                    ["text": Self.prompt],
                    ["inline_data": ["mime_type": "audio/wav",
                                     "data": audio.base64EncodedString()]],
                ],
            ]],
        ]
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, _) = try await URLSession.shared.data(for: req)
        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let candidates = json["candidates"] as? [[String: Any]],
              let content = candidates.first?["content"] as? [String: Any],
              let parts = content["parts"] as? [[String: Any]],
              let text = parts.first?["text"] as? String else {
            throw GemmaError.badResponse(String(data: data.prefix(200), encoding: .utf8) ?? "")
        }
        return text
    }

    // MARK: Output parsing (models wrap JSON in prose/fences at will)

    static func parseCard(_ text: String) throws -> IDCard {
        guard let start = text.firstIndex(of: "{"),
              let end = text.lastIndex(of: "}") else { throw GemmaError.noJSON }
        let data = Data(text[start...end].utf8)
        do {
            return try JSONDecoder().decode(IDCard.self, from: data)
        } catch {
            throw GemmaError.badJSON("\(error)")
        }
    }
}

enum GemmaError: Error {
    case disabled, notConfigured, noJSON
    case badJSON(String)
    case badResponse(String)
}
