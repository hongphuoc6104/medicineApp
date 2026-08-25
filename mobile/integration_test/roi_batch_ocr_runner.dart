// ignore_for_file: avoid_print

import 'dart:convert';
import 'dart:io';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:integration_test/integration_test.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('C0 / C1 / C2 Medication ROI On-Device ML Kit OCR Runner',
      (WidgetTester tester) async {
    final textRecognizer = TextRecognizer(script: TextRecognitionScript.latin);

    // Load ROI Manifest
    final manifestString =
        await rootBundle.loadString('assets/roi_samples/roi_manifest.json');
    final List<dynamic> manifest = jsonDecode(manifestString);

    print('[INFO] Loaded ${manifest.length} sample prescriptions for C0/C1/C2 ROI Ablation.');

    final tempDir = Directory.systemTemp;
    final outputDir = Directory('/sdcard/Download/roi_ocr');
    try {
      if (!await outputDir.exists()) {
        await outputDir.create(recursive: true);
      }
    } catch (_) {}

    final List<String> tiers = ['c0', 'c1', 'c2'];
    int totalRuns = manifest.length * tiers.length;
    int currentRun = 0;

    for (final item in manifest) {
      final imageId = item['image_id'] as String;
      final c1Box = (item['c1_box'] as List).cast<num>();
      final c2Box = (item['c2_box'] as List).cast<num>();

      for (final tier in tiers) {
        currentRun++;
        final filename = '${tier}_$imageId.png';
        final assetPath = 'assets/roi_samples/$filename';

        try {
          final byteData = await rootBundle.load(assetPath);
          final tempFile = File('${tempDir.path}/$filename');
          await tempFile.writeAsBytes(byteData.buffer.asUint8List());

          final inputImage = InputImage.fromFilePath(tempFile.path);
          final recognizedText = await textRecognizer.processImage(inputImage);

          // Compute coordinate offsets
          double xOffset = 0.0;
          double yOffset = 0.0;
          if (tier == 'c1') {
            xOffset = c1Box[0].toDouble();
            yOffset = c1Box[1].toDouble();
          } else if (tier == 'c2') {
            xOffset = c2Box[0].toDouble();
            yOffset = c2Box[1].toDouble();
          }

          final List<Map<String, dynamic>> linesData = [];
          for (int bIdx = 0; bIdx < recognizedText.blocks.length; bIdx++) {
            final block = recognizedText.blocks[bIdx];
            for (int lIdx = 0; lIdx < block.lines.length; lIdx++) {
              final line = block.lines[lIdx];
              final rect = line.boundingBox;
              linesData.add({
                'text': line.text,
                'bbox': {
                  'left': rect.left + xOffset,
                  'top': rect.top + yOffset,
                  'right': rect.right + xOffset,
                  'bottom': rect.bottom + yOffset,
                },
                'local_bbox': {
                  'left': rect.left,
                  'top': rect.top,
                  'right': rect.right,
                  'bottom': rect.bottom,
                },
                'confidence': line.confidence ?? 0.95,
                'block_index': bIdx,
                'line_index': lIdx,
              });
            }
          }

          final resultPayload = {
            'tier': tier,
            'image_id': imageId,
            'file_name': filename,
            'text': recognizedText.text,
            'block_count': recognizedText.blocks.length,
            'line_count': linesData.length,
            'x_offset': xOffset,
            'y_offset': yOffset,
            'lines': linesData,
          };

          final jsonString = jsonEncode(resultPayload);

          try {
            final outputFile = File('${outputDir.path}/${tier}_$imageId.json');
            await outputFile.writeAsString(jsonString);
          } catch (_) {}

          print('[ROI_OCR_JSON_START]');
          print(jsonString);
          print('[ROI_OCR_JSON_END]');

          print('[$currentRun/$totalRuns] $tier for $imageId: ${linesData.length} lines detected.');

          try {
            await tempFile.delete();
          } catch (_) {}
        } catch (e) {
          print('[ERROR] Processing $tier for $imageId failed: $e');
        }
      }
    }

    await textRecognizer.close();
    print('[DONE] Completed C0/C1/C2 on-device OCR on all $totalRuns configurations.');
  });
}
