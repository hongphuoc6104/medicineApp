import 'dart:convert';
import 'dart:io';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:integration_test/integration_test.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('R0 (Full Page) vs R1 (Medication ROI Re-OCR) On-Device Benchmark',
      (WidgetTester tester) async {
    final textRecognizer = TextRecognizer(script: TextRecognitionScript.latin);

    final manifestString =
        await rootBundle.loadString('assets/real_roi_samples/real_roi_manifest.json');
    final List<dynamic> manifest = jsonDecode(manifestString);

    print('[INFO] Loaded ${manifest.length} hard real-world camera captures for R0 vs R1.');

    final tempDir = Directory.systemTemp;
    final outputDir = Directory('/sdcard/Download/real_roi_ocr');
    try {
      if (!await outputDir.exists()) {
        await outputDir.create(recursive: true);
      }
    } catch (_) {}

    final List<String> conditions = ['r0', 'r1'];
    int totalRuns = manifest.length * conditions.length;
    int currentRun = 0;

    for (final item in manifest) {
      final imageId = item['image_id'] as String;
      final pid = item['prescription_id'] as String;
      final r1Box = (item['r1_crop_box'] as List).cast<num>();

      for (final cond in conditions) {
        currentRun++;
        final filename = '${cond}_$imageId.jpg';
        final assetPath = 'assets/real_roi_samples/$filename';

        try {
          final byteData = await rootBundle.load(assetPath);
          final tempFile = File('${tempDir.path}/$filename');
          await tempFile.writeAsBytes(byteData.buffer.asUint8List());

          final inputImage = InputImage.fromFilePath(tempFile.path);
          final recognizedText = await textRecognizer.processImage(inputImage);

          double xOffset = 0.0;
          double yOffset = 0.0;
          if (cond == 'r1') {
            xOffset = r1Box[0].toDouble();
            yOffset = r1Box[1].toDouble();
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
            'condition': cond,
            'image_id': imageId,
            'prescription_id': pid,
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
            final outputFile = File('${outputDir.path}/${cond}_$imageId.json');
            await outputFile.writeAsString(jsonString);
          } catch (_) {}

          print('[REAL_ROI_OCR_JSON_START]');
          print(jsonString);
          print('[REAL_ROI_OCR_JSON_END]');

          print('[$currentRun/$totalRuns] $cond for $imageId ($pid): ${linesData.length} lines detected.');

          try {
            await tempFile.delete();
          } catch (_) {}
        } catch (e) {
          print('[ERROR] Processing $cond for $imageId failed: $e');
        }
      }
    }

    await textRecognizer.close();
    print('[DONE] Completed R0 vs R1 on-device OCR on all $totalRuns configurations.');
  });
}
