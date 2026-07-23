// make_signature.swift — macOS helper: audio file -> .shazamsignature
// Usage: swift make_signature.swift <input audio> <output .shazamsignature>
// Used by fingerprint_catalog.py. Requires macOS 12+ (ShazamKit + AVFoundation).
import AVFoundation
import ShazamKit

let args = CommandLine.arguments
guard args.count == 3 else { FileHandle.standardError.write("usage: swift make_signature.swift <in> <out>\n".data(using: .utf8)!); exit(2) }
let inURL = URL(fileURLWithPath: args[1])
let outURL = URL(fileURLWithPath: args[2])

do {
    let file = try AVAudioFile(forReading: inURL)
    let target = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: 44100, channels: 1, interleaved: false)!
    let converter = AVAudioConverter(from: file.processingFormat, to: target)!
    let generator = SHSignatureGenerator()

    let inBuf = AVAudioPCMBuffer(pcmFormat: file.processingFormat, frameCapacity: 44100)!
    while true {
        try file.read(into: inBuf)
        if inBuf.frameLength == 0 { break }
        let outBuf = AVAudioPCMBuffer(pcmFormat: target, frameCapacity: 44100 * 2)!
        var err: NSError?
        var fed = false
        converter.convert(to: outBuf, error: &err) { _, status in
            if fed { status.pointee = .noDataNow; return nil }
            fed = true; status.pointee = .haveData; return inBuf
        }
        if let e = err { throw e }
        try generator.append(outBuf, at: nil)
        inBuf.frameLength = 0
        if file.framePosition >= file.length { break }
    }
    let signature = try generator.signature()
    try signature.dataRepresentation.write(to: outURL)
} catch {
    FileHandle.standardError.write("error: \(error)\n".data(using: .utf8)!)
    exit(1)
}
