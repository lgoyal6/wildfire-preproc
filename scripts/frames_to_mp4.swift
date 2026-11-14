import AppKit
import AVFoundation
import Foundation

enum VideoError: Error {
    case badArguments
    case noFrames
    case imageLoadFailed(String)
    case pixelBufferFailed
}

func makePixelBuffer(from image: NSImage, width: Int, height: Int) throws -> CVPixelBuffer {
    var pixelBuffer: CVPixelBuffer?
    let attrs: [CFString: Any] = [
        kCVPixelBufferCGImageCompatibilityKey: true,
        kCVPixelBufferCGBitmapContextCompatibilityKey: true,
    ]
    CVPixelBufferCreate(
        kCFAllocatorDefault,
        width,
        height,
        kCVPixelFormatType_32ARGB,
        attrs as CFDictionary,
        &pixelBuffer
    )
    guard let buffer = pixelBuffer else { throw VideoError.pixelBufferFailed }

    CVPixelBufferLockBaseAddress(buffer, [])
    defer { CVPixelBufferUnlockBaseAddress(buffer, []) }

    guard
        let context = CGContext(
            data: CVPixelBufferGetBaseAddress(buffer),
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: CVPixelBufferGetBytesPerRow(buffer),
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.noneSkipFirst.rawValue
        )
    else {
        throw VideoError.pixelBufferFailed
    }

    context.clear(CGRect(x: 0, y: 0, width: width, height: height))
    if let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) {
        context.draw(cgImage, in: CGRect(x: 0, y: 0, width: width, height: height))
    }
    return buffer
}

func main() throws {
    guard CommandLine.arguments.count >= 4 else { throw VideoError.badArguments }
    let framesDir = URL(fileURLWithPath: CommandLine.arguments[1])
    let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])
    let fps = Int32(CommandLine.arguments[3]) ?? 8

    let frameURLs = try FileManager.default.contentsOfDirectory(
        at: framesDir,
        includingPropertiesForKeys: nil
    )
    .filter { $0.pathExtension.lowercased() == "jpg" || $0.pathExtension.lowercased() == "jpeg" }
    .sorted { $0.lastPathComponent < $1.lastPathComponent }

    guard let firstURL = frameURLs.first else { throw VideoError.noFrames }
    guard let firstImage = NSImage(contentsOf: firstURL) else {
        throw VideoError.imageLoadFailed(firstURL.path)
    }
    let width = Int(firstImage.size.width)
    let height = Int(firstImage.size.height)

    try? FileManager.default.removeItem(at: outputURL)
    try FileManager.default.createDirectory(
        at: outputURL.deletingLastPathComponent(),
        withIntermediateDirectories: true
    )

    let writer = try AVAssetWriter(outputURL: outputURL, fileType: .mp4)
    let input = AVAssetWriterInput(
        mediaType: .video,
        outputSettings: [
            AVVideoCodecKey: AVVideoCodecType.h264,
            AVVideoWidthKey: width,
            AVVideoHeightKey: height,
            AVVideoCompressionPropertiesKey: [
                AVVideoAverageBitRateKey: 6_000_000,
                AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
            ],
        ]
    )
    input.expectsMediaDataInRealTime = false

    let adaptor = AVAssetWriterInputPixelBufferAdaptor(
        assetWriterInput: input,
        sourcePixelBufferAttributes: [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32ARGB,
            kCVPixelBufferWidthKey as String: width,
            kCVPixelBufferHeightKey as String: height,
        ]
    )

    writer.add(input)
    writer.startWriting()
    writer.startSession(atSourceTime: .zero)

    let frameDuration = CMTime(value: 1, timescale: fps)
    var frameIndex: Int64 = 0
    for url in frameURLs {
        while !input.isReadyForMoreMediaData {
            Thread.sleep(forTimeInterval: 0.01)
        }
        guard let image = NSImage(contentsOf: url) else {
            throw VideoError.imageLoadFailed(url.path)
        }
        let buffer = try makePixelBuffer(from: image, width: width, height: height)
        let time = CMTimeMultiply(frameDuration, multiplier: Int32(frameIndex))
        adaptor.append(buffer, withPresentationTime: time)
        frameIndex += 1
    }

    input.markAsFinished()
    let semaphore = DispatchSemaphore(value: 0)
    writer.finishWriting {
        semaphore.signal()
    }
    semaphore.wait()

    if writer.status == .failed {
        throw writer.error ?? VideoError.pixelBufferFailed
    }
}

do {
    try main()
} catch {
    fputs("frames_to_mp4 failed: \(error)\n", stderr)
    exit(1)
}
