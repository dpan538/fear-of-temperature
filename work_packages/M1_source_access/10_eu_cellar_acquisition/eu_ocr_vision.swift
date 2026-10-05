// Render official PDF pages locally and preserve Vision OCR line coordinates.
import AppKit
import Foundation
import PDFKit
import Vision

guard CommandLine.arguments.count >= 2,
      let pdf = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1])) else {
    fputs("usage: eu_ocr_vision.swift FILE.pdf [MAX_PAGES]\n", stderr)
    exit(2)
}
let maxPages = CommandLine.arguments.count >= 3 ? Int(CommandLine.arguments[2]) ?? 0 : 0
let count = maxPages > 0 ? min(pdf.pageCount, maxPages) : pdf.pageCount
for index in 0..<count {
    guard let page = pdf.page(at: index) else { continue }
    let bounds = page.bounds(for: .mediaBox)
    let scale = min(3.0, 2400.0 / max(bounds.width, bounds.height))
    let image = page.thumbnail(of: NSSize(width: bounds.width * scale,
                                          height: bounds.height * scale), for: .mediaBox)
    guard let tiff = image.tiffRepresentation,
          let bitmap = NSBitmapImageRep(data: tiff),
          let cgImage = bitmap.cgImage else {
        fputs("render failed on page \(index + 1)\n", stderr)
        exit(3)
    }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["en-US"]
    request.usesLanguageCorrection = true
    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    do { try handler.perform([request]) }
    catch {
        fputs("OCR failed on page \(index + 1): \(error)\n", stderr)
        exit(4)
    }
    let lines: [[String: Any]] = (request.results ?? []).compactMap { observation in
        guard let choice = observation.topCandidates(1).first else { return nil }
        let box = observation.boundingBox
        return ["text": choice.string, "confidence": choice.confidence,
                "x": box.minX, "y": box.minY, "width": box.width, "height": box.height]
    }
    let headingRequest = VNRecognizeTextRequest()
    headingRequest.recognitionLevel = .accurate
    headingRequest.recognitionLanguages = ["en-US"]
    headingRequest.usesLanguageCorrection = true
    headingRequest.regionOfInterest = CGRect(x: 0.05, y: 0.70, width: 0.90, height: 0.20)
    try handler.perform([headingRequest])
    let headingLines: [[String: Any]] = (headingRequest.results ?? []).compactMap { observation in
        guard let choice = observation.topCandidates(1).first else { return nil }
        let box = observation.boundingBox
        return ["text": choice.string, "confidence": choice.confidence,
                "x": box.minX, "y": box.minY, "width": box.width, "height": box.height]
    }
    let row: [String: Any] = ["page": index + 1, "lines": lines,
                              "top_region_lines": headingLines]
    let data = try JSONSerialization.data(withJSONObject: row, options: [.sortedKeys])
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write(Data([10]))
}
