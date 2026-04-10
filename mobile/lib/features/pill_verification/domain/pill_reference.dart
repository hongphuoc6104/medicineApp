class PillReferenceImage {
  const PillReferenceImage({
    required this.id,
    required this.imagePath,
    required this.side,
    this.qualityScore,
    required this.confirmedByUser,
    this.createdAt,
  });

  final String id;
  final String imagePath;
  final String side;
  final double? qualityScore;
  final bool confirmedByUser;
  final String? createdAt;

  factory PillReferenceImage.fromJson(Map<String, dynamic> json) =>
      PillReferenceImage(
        id: json['id']?.toString() ?? '',
        imagePath: json['imagePath']?.toString() ?? '',
        side: json['side']?.toString() ?? 'front',
        qualityScore: (json['qualityScore'] as num?)?.toDouble(),
        confirmedByUser: json['confirmedByUser'] as bool? ?? false,
        createdAt: json['createdAt']?.toString(),
      );
}

class PillReferenceSet {
  const PillReferenceSet({
    required this.id,
    required this.planId,
    required this.drugNameSnapshot,
    required this.status,
    required this.imageCount,
    required this.images,
    this.createdAt,
    this.updatedAt,
  });

  final String id;
  final String planId;
  final String drugNameSnapshot;
  final String status;
  final int imageCount;
  final List<PillReferenceImage> images;
  final String? createdAt;
  final String? updatedAt;

  bool get isReady => status == 'ready' && imageCount > 0;

  factory PillReferenceSet.fromJson(Map<String, dynamic> json) =>
      PillReferenceSet(
        id: json['id']?.toString() ?? '',
        planId: json['planId']?.toString() ?? '',
        drugNameSnapshot: json['drugNameSnapshot']?.toString() ?? '',
        status: json['status']?.toString() ?? 'draft',
        imageCount: json['imageCount'] as int? ?? 0,
        images: (json['images'] as List<dynamic>? ?? const [])
            .map((e) => PillReferenceImage.fromJson(e as Map<String, dynamic>))
            .toList(),
        createdAt: json['createdAt']?.toString(),
        updatedAt: json['updatedAt']?.toString(),
      );
}
