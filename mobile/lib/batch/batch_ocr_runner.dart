import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:image/image.dart' as img;

class BatchOcrRunner {
  final TextRecognizer _recognizer = TextRecognizer(
    script: TextRecognitionScript.latin,
  );

  Future<void> runBatch({
    required Directory inputDir,
    required Directory outputDir,
    void Function(String message)? onLog,
  }) async {
    final log = onLog ?? (msg) => debugPrint('[BatchOCR] $msg');

    if (!await inputDir.exists()) {
      log('Thư mục input không tồn tại: ${inputDir.path}');
      return;
    }
    if (!await outputDir.exists()) {
      await outputDir.create(recursive: true);
    }

    final files = inputDir
        .listSync(recursive: true)
        .whereType<File>()
        .where((f) {
          final ext = f.path.toLowerCase();
          return ext.endsWith('.jpg') ||
              ext.endsWith('.jpeg') ||
              ext.endsWith('.png') ||
              ext.endsWith('.webp');
        })
        .toList()
      ..sort((a, b) => a.path.compareTo(b.path));

    log('Tìm thấy ${files.length} ảnh cần OCR trong ${inputDir.path}');

    var successCount = 0;
    var failCount = 0;

    for (var i = 0; i < files.length; i++) {
      final file = files[i];
      final fileName = file.uri.pathSegments.last;
      final relativePath = file.path.startsWith('${inputDir.path}/')
          ? file.path.substring(inputDir.path.length + 1)
          : fileName;
      if (!await file.exists()) {
        log('[${i + 1}/${files.length}] Không tìm thấy file: ${file.path} (Bỏ qua)');
        continue;
      }
      final jsonRelativePath =
          '${relativePath.replaceAll(RegExp(r'\.[^\.]+$'), '')}.json';
      final outputFile = File('${outputDir.path}/$jsonRelativePath');
      if (await outputFile.exists()) {
        successCount++;
        log('[${i + 1}/${files.length}] Đã có sẵn: $relativePath (Bỏ qua)');
        continue;
      }
      await outputFile.parent.create(recursive: true);

      final stopwatch = Stopwatch()..start();
      try {
        final result = await _processSingleImage(file);
        await outputFile.writeAsString(
          const JsonEncoder.withIndent('  ').convert(result),
        );
        stopwatch.stop();
        successCount++;
        log('[${i + 1}/${files.length}] Hoàn thành: $fileName (${stopwatch.elapsedMilliseconds}ms)');
      } catch (e, st) {
        stopwatch.stop();
        failCount++;
        log('[${i + 1}/${files.length}] LỖI: $fileName - $e\n$st');
      }
    }

    log('=== KẾT THÚC BATCH OCR: $successCount thành công, $failCount thất bại ===');
  }

  Future<Map<String, dynamic>> _processSingleImage(File file) async {
    final bytes = await file.readAsBytes();
    int? imageWidth;
    int? imageHeight;

    try {
      final decoded = img.decodeImage(bytes);
      if (decoded != null) {
        imageWidth = decoded.width;
        imageHeight = decoded.height;
      }
    } catch (_) {}

    final inputImage = InputImage.fromFilePath(file.path);
    final recognizedText = await _recognizer.processImage(inputImage);

    return {
      'metadata': {
        'fileName': file.uri.pathSegments.last,
        'filePath': file.path,
        'fileSizeBytes': bytes.length,
        'imageWidth': imageWidth,
        'imageHeight': imageHeight,
        'processedAt': DateTime.now().toUtc().toIso8601String(),
        'recognizerScript': 'latin',
      },
      'fullText': recognizedText.text,
      'blocks': recognizedText.blocks.map(_serializeBlock).toList(),
    };
  }

  Map<String, dynamic> _serializeBlock(TextBlock block) {
    return {
      'text': block.text,
      'boundingBox': _serializeRect(block.boundingBox),
      'recognizedLanguages': block.recognizedLanguages,
      'cornerPoints': block.cornerPoints.map(_serializePoint).toList(),
      'lines': block.lines.map(_serializeLine).toList(),
    };
  }

  Map<String, dynamic> _serializeLine(TextLine line) {
    return {
      'text': line.text,
      'boundingBox': _serializeRect(line.boundingBox),
      'confidence': line.confidence,
      'angle': line.angle,
      'recognizedLanguages': line.recognizedLanguages,
      'cornerPoints': line.cornerPoints.map(_serializePoint).toList(),
      'elements': line.elements.map(_serializeElement).toList(),
    };
  }

  Map<String, dynamic> _serializeElement(TextElement element) {
    return {
      'text': element.text,
      'boundingBox': _serializeRect(element.boundingBox),
      'confidence': element.confidence,
      'angle': element.angle,
      'recognizedLanguages': element.recognizedLanguages,
      'cornerPoints': element.cornerPoints.map(_serializePoint).toList(),
      'symbols': element.symbols.map(_serializeSymbol).toList(),
    };
  }

  Map<String, dynamic> _serializeSymbol(TextSymbol symbol) {
    return {
      'text': symbol.text,
      'boundingBox': _serializeRect(symbol.boundingBox),
      'confidence': symbol.confidence,
      'angle': symbol.angle,
      'recognizedLanguages': symbol.recognizedLanguages,
      'cornerPoints': symbol.cornerPoints.map(_serializePoint).toList(),
    };
  }

  Map<String, dynamic> _serializeRect(Rect rect) {
    return {
      'left': rect.left,
      'top': rect.top,
      'right': rect.right,
      'bottom': rect.bottom,
      'width': rect.width,
      'height': rect.height,
    };
  }

  Map<String, dynamic> _serializePoint(Point<int> point) {
    return {'x': point.x, 'y': point.y};
  }

  Future<void> close() => _recognizer.close();
}
