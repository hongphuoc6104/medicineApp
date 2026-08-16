import 'package:flutter_test/flutter_test.dart';
import 'package:medicine_app/scan/models.dart';

void main() {
  test('serializes OCR pages and nullable confidence', () {
    final request = EntityRequest(
      documentId: 'mobile-test',
      pages: [
        OcrPage(
          pageIndex: 0,
          imageWidth: 1200,
          imageHeight: 1800,
          regions: const [
            OcrRegion(
              regionId: 'p0_b0_l0',
              text: 'Paracetamol 500 mg',
              bbox: BoundingBox(left: 10, top: 20, right: 310, bottom: 70),
              readingOrder: 0,
            ),
          ],
        ),
      ],
    );

    expect(request.toJson(), {
      'schema_version': 'rxie.ocr.v1',
      'document_id': 'mobile-test',
      'ocr_engine': {
        'name': 'google_mlkit_text_recognition',
        'version': '0.15.1',
      },
      'pages': [
        {
          'page_index': 0,
          'width': 1200,
          'height': 1800,
          'regions': [
            {
              'region_id': 'p0_b0_l0',
              'text': 'Paracetamol 500 mg',
              'bbox': {
                'points': [
                  [10.0, 20.0],
                  [310.0, 20.0],
                  [310.0, 70.0],
                  [10.0, 70.0],
                ],
              },
              'reading_order': 0,
              'confidence': null,
            },
          ],
        },
      ],
    });
  });

  group('parseEntityResponse', () {
    test('parses an entities envelope and nullable confidence', () {
      final entities = parseEntityResponse({
        'entities': [
          {'type': 'DRUG', 'text': 'Paracetamol', 'confidence': 0.94},
          {'entity_type': 'DOSAGE', 'text': '500 mg', 'confidence': null},
        ],
      });

      expect(entities, hasLength(2));
      expect(entities.first.type, 'DRUG');
      expect(entities.first.text, 'Paracetamol');
      expect(entities.first.confidence, 0.94);
      expect(entities.last.type, 'DOSAGE');
      expect(entities.last.confidence, isNull);
    });

    test('parses a top-level list', () {
      final entities = parseEntityResponse([
        {'type': 'QUANTITY', 'text': '10 viên', 'confidence': 1},
      ]);

      expect(entities.single.confidence, 1.0);
    });

    test('rejects malformed entities', () {
      expect(
        () => parseEntityResponse({
          'entities': [
            {'type': 'DRUG', 'confidence': 0.8},
          ],
        }),
        throwsFormatException,
      );
    });
  });
}
