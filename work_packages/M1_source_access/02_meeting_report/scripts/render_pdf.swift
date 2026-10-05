import AppKit
import Foundation
import PDFKit

guard CommandLine.arguments.count == 3 else {
    fputs("Usage: render_pdf.swift input.pdf output_directory\n", stderr)
    exit(2)
}

let inputURL = URL(fileURLWithPath: CommandLine.arguments[1])
let outputURL = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)

guard let document = PDFDocument(url: inputURL) else {
    fputs("Could not open PDF: \(inputURL.path)\n", stderr)
    exit(1)
}

try FileManager.default.createDirectory(at: outputURL, withIntermediateDirectories: true)

for index in 0..<document.pageCount {
    guard let page = document.page(at: index) else { continue }
    let bounds = page.bounds(for: .mediaBox)
    let size = NSSize(width: bounds.width * 2.0, height: bounds.height * 2.0)
    let image = page.thumbnail(of: size, for: .mediaBox)
    guard
        let tiff = image.tiffRepresentation,
        let bitmap = NSBitmapImageRep(data: tiff),
        let png = bitmap.representation(using: .png, properties: [:])
    else {
        fputs("Could not render page \(index + 1)\n", stderr)
        exit(1)
    }
    let fileURL = outputURL.appendingPathComponent(String(format: "page-%02d.png", index + 1))
    try png.write(to: fileURL)
}

print("Rendered \(document.pageCount) pages to \(outputURL.path)")
