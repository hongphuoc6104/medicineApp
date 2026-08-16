import 'dart:io';
import 'dart:ui';

import 'package:google_mlkit_document_scanner/google_mlkit_document_scanner.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:image/image.dart' as img;

import 'models.dart';
import 'scanner.dart';

class MlKitPrescriptionScanner implements PrescriptionScanner {
  MlKitPrescriptionScanner()
    : _recognizer = TextRecognizer(script: TextRecognitionScript.latin);

  final TextRecognizer _recognizer;

  @override
  Future<EntityRequest?> scan() async {
    final scanner = DocumentScanner(
      options: DocumentScannerOptions(
        pageLimit: 10,
        isGalleryImport: true,
        mode: ScannerMode.full,
      ),
    );

    try {
      final result = await scanner.scanDocument();
      final paths = result.images;
      if (paths == null || paths.isEmpty) return null;

      final pages = <OcrPage>[];
      for (var pageIndex = 0; pageIndex < paths.length; pageIndex++) {
        pages.add(await _recognizePage(paths[pageIndex], pageIndex));
      }
      return EntityRequest(
        documentId: 'mobile-${DateTime.now().microsecondsSinceEpoch}',
        pages: pages,
      );
    } finally {
      scanner.close();
    }
  }

  Future<OcrPage> _recognizePage(String path, int pageIndex) async {
    final bytes = await File(path).readAsBytes();
    final decoded = img.decodeImage(bytes);
    if (decoded == null) {
      throw StateError('Không đọc được kích thước ảnh trang ${pageIndex + 1}');
    }

    final recognized = await _recognizer.processImage(
      InputImage.fromFilePath(path),
    );
    final regions = <OcrRegion>[];
    var readingOrder = 0;
    for (
      var blockIndex = 0;
      blockIndex < recognized.blocks.length;
      blockIndex++
    ) {
      final block = recognized.blocks[blockIndex];
      if (block.lines.isEmpty) {
        regions.add(
          _region(
            id: 'p${pageIndex}_b$blockIndex',
            text: block.text,
            rect: block.boundingBox,
            readingOrder: readingOrder++,
          ),
        );
      }
      for (var lineIndex = 0; lineIndex < block.lines.length; lineIndex++) {
        final line = block.lines[lineIndex];
        regions.add(
          _region(
            id: 'p${pageIndex}_b${blockIndex}_l$lineIndex',
            text: line.text,
            rect: line.boundingBox,
            readingOrder: readingOrder++,
            confidence: line.confidence,
          ),
        );
      }
    }

    return OcrPage(
      pageIndex: pageIndex,
      imageWidth: decoded.width,
      imageHeight: decoded.height,
      regions: regions,
    );
  }

  OcrRegion _region({
    required String id,
    required String text,
    required Rect rect,
    required int readingOrder,
    double? confidence,
  }) {
    return OcrRegion(
      regionId: id,
      text: text,
      bbox: BoundingBox(
        left: rect.left,
        top: rect.top,
        right: rect.right,
        bottom: rect.bottom,
      ),
      readingOrder: readingOrder,
      confidence: confidence,
    );
  }

  @override
  Future<void> close() => _recognizer.close();
}
