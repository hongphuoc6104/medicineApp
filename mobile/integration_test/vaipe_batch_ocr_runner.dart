import 'dart:convert';
import 'dart:io';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:integration_test/integration_test.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('VAIPE Batch ML Kit OCR Runner on Android Device',
      (WidgetTester tester) async {
    final textRecognizer = TextRecognizer(script: TextRecognitionScript.latin);

    final List<String> sampleNames = [
      'VAIPE_P_TRAIN_0.png',
      'VAIPE_P_TRAIN_1.png',
      'VAIPE_P_TRAIN_10.png',
      'VAIPE_P_TRAIN_100.png',
      'VAIPE_P_TRAIN_1000.png',
      'VAIPE_P_TRAIN_1001.png',
      'VAIPE_P_TRAIN_1002.png',
      'VAIPE_P_TRAIN_1003.png',
      'VAIPE_P_TRAIN_1004.png',
      'VAIPE_P_TRAIN_1005.png',
      'VAIPE_P_TRAIN_1006.png',
      'VAIPE_P_TRAIN_1007.png',
      'VAIPE_P_TRAIN_1008.png',
      'VAIPE_P_TRAIN_1009.png',
      'VAIPE_P_TRAIN_101.png',
      'VAIPE_P_TRAIN_1010.png',
      'VAIPE_P_TRAIN_1011.png',
      'VAIPE_P_TRAIN_1012.png',
      'VAIPE_P_TRAIN_1013.png',
      'VAIPE_P_TRAIN_1014.png',
      'VAIPE_P_TRAIN_1015.png',
      'VAIPE_P_TRAIN_1016.png',
      'VAIPE_P_TRAIN_1017.png',
      'VAIPE_P_TRAIN_1018.png',
      'VAIPE_P_TRAIN_1019.png',
      'VAIPE_P_TRAIN_102.png',
      'VAIPE_P_TRAIN_1020.png',
      'VAIPE_P_TRAIN_1021.png',
      'VAIPE_P_TRAIN_1022.png',
      'VAIPE_P_TRAIN_1023.png',
    ];

    print('[INFO] Starting on-device ML Kit OCR on ${sampleNames.length} VAIPE samples...');

    final tempDir = Directory.systemTemp;
    int processedCount = 0;

    for (final filename in sampleNames) {
      final imageId = filename.substring(0, filename.lastIndexOf('.'));
      final assetPath = 'assets/vaipe_samples/$filename';

      try {
        // Load asset bytes and write to temp file
        final byteData = await rootBundle.load(assetPath);
        final tempFile = File('${tempDir.path}/$filename');
        await tempFile.writeAsBytes(byteData.buffer.asUint8List());

        // Process with ML Kit Text Recognition on actual hardware
        final inputImage = InputImage.fromFilePath(tempFile.path);
        final recognizedText = await textRecognizer.processImage(inputImage);

        final List<Map<String, dynamic>> linesData = [];
        for (int bIdx = 0; bIdx < recognizedText.blocks.length; bIdx++) {
          final block = recognizedText.blocks[bIdx];
          for (int lIdx = 0; lIdx < block.lines.length; lIdx++) {
            final line = block.lines[lIdx];
            final rect = line.boundingBox;
            linesData.add({
              'text': line.text,
              'bbox': {
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
          'image_id': imageId,
          'file_name': filename,
          'text': recognizedText.text,
          'block_count': recognizedText.blocks.length,
          'line_count': linesData.length,
          'lines': linesData,
        };

        final jsonString = jsonEncode(resultPayload);

        // Print stream token for direct host capture
        print('[VAIPE_OCR_JSON_START]');
        print(jsonString);
        print('[VAIPE_OCR_JSON_END]');

        processedCount++;
        print('[PROCESSED $processedCount/${sampleNames.length}] $imageId -> ${linesData.length} lines detected by ML Kit.');

        // Clean up temp file
        try {
          await tempFile.delete();
        } catch (_) {}
      } catch (e) {
        print('[ERROR] Failed processing $imageId: $e');
      }
    }

    await textRecognizer.close();
    print('[DONE] Successfully completed ML Kit OCR on $processedCount/${sampleNames.length} VAIPE images.');
  });
}
