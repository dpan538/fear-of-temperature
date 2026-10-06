import Foundation
import Vision
import AppKit
let url = URL(fileURLWithPath: CommandLine.arguments[1])
let image = NSImage(contentsOf: url)!
var rect = CGRect(origin: .zero, size: image.size)
let cg = image.cgImage(forProposedRect: &rect, context: nil, hints: nil)!
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["en-US"]
request.usesLanguageCorrection = false
let handler = VNImageRequestHandler(cgImage: cg, options: [:])
try handler.perform([request])
let rows: [[String: Any]] = (request.results ?? []).compactMap { obs in
    guard let text = obs.topCandidates(1).first else { return nil }
    let b = obs.boundingBox
    return ["text": text.string, "confidence": text.confidence,
            "box_bottom_left_normalized": [b.minX, b.minY, b.maxX, b.maxY]]
}
let data = try JSONSerialization.data(withJSONObject: rows, options: [.prettyPrinted, .sortedKeys])
print(String(data: data, encoding: .utf8)!)
