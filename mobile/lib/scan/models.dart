class BoundingBox {
  const BoundingBox({
    required this.left,
    required this.top,
    required this.right,
    required this.bottom,
  });

  final double left;
  final double top;
  final double right;
  final double bottom;

  Map<String, Object> toJson() => {
    'points': [
      [left, top],
      [right, top],
      [right, bottom],
      [left, bottom],
    ],
  };
}

class OcrRegion {
  const OcrRegion({
    required this.regionId,
    required this.text,
    required this.bbox,
    required this.readingOrder,
    this.confidence,
  });

  final String regionId;
  final String text;
  final BoundingBox bbox;
  final int readingOrder;
  final double? confidence;

  Map<String, Object?> toJson() => {
    'region_id': regionId,
    'text': text,
    'bbox': bbox.toJson(),
    'reading_order': readingOrder,
    'confidence': confidence,
  };
}

class OcrPage {
  const OcrPage({
    required this.pageIndex,
    required this.imageWidth,
    required this.imageHeight,
    required this.regions,
  });

  final int pageIndex;
  final int imageWidth;
  final int imageHeight;
  final List<OcrRegion> regions;

  Map<String, Object> toJson() => {
    'page_index': pageIndex,
    'width': imageWidth,
    'height': imageHeight,
    'regions': regions.map((region) => region.toJson()).toList(),
  };
}

class EntityRequest {
  const EntityRequest({required this.documentId, required this.pages});

  final String documentId;
  final List<OcrPage> pages;

  Map<String, Object> toJson() => {
    'schema_version': 'rxie.ocr.v1',
    'document_id': documentId,
    'ocr_engine': {
      'name': 'google_mlkit_text_recognition',
      'version': '0.15.1',
    },
    'pages': pages.map((page) => page.toJson()).toList(),
  };
}

class ExtractedEntity {
  const ExtractedEntity({
    required this.type,
    required this.text,
    this.confidence,
  });

  final String type;
  final String text;
  final double? confidence;

  factory ExtractedEntity.fromJson(Map<String, dynamic> json) {
    final type = json['type'] ?? json['entity_type'];
    final text = json['text'];
    final confidence = json['confidence'];
    if (type is! String || type.isEmpty || text is! String || text.isEmpty) {
      throw const FormatException(
        'Entity must contain non-empty type and text',
      );
    }
    if (confidence != null && confidence is! num) {
      throw const FormatException('Entity confidence must be numeric or null');
    }
    return ExtractedEntity(
      type: type,
      text: text,
      confidence: (confidence as num?)?.toDouble(),
    );
  }
}

List<ExtractedEntity> parseEntityResponse(Object? body) {
  final rawEntities = switch (body) {
    List<dynamic> value => value,
    {'entities': final List<dynamic> value} => value,
    _ => throw const FormatException(
      'Response must be a list or contain entities',
    ),
  };

  return rawEntities
      .map((value) {
        if (value is! Map<String, dynamic>) {
          throw const FormatException('Each entity must be a JSON object');
        }
        return ExtractedEntity.fromJson(value);
      })
      .toList(growable: false);
}
