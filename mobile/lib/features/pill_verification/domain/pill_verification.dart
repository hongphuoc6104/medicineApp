class ExpectedMedication {
  const ExpectedMedication({
    required this.planId,
    required this.drugName,
    this.dosage,
    this.pillsPerDose,
  });

  final String planId;
  final String drugName;
  final String? dosage;
  final int? pillsPerDose;

  Map<String, dynamic> toJson() => {
    'planId': planId,
    'drugName': drugName,
    if (dosage != null) 'dosage': dosage,
    if (pillsPerDose != null) 'pillsPerDose': pillsPerDose,
  };

  factory ExpectedMedication.fromJson(Map<String, dynamic> json) =>
      ExpectedMedication(
        planId: json['planId']?.toString() ?? '',
        drugName: json['drugName']?.toString() ?? '',
        dosage: json['dosage']?.toString(),
        pillsPerDose: json['pillsPerDose'] as int?,
      );
}

class PillDetectionItem {
  const PillDetectionItem({
    required this.detectionIdx,
    required this.bbox,
    required this.score,
    required this.assignmentStatus,
    this.assignedDrugName,
    this.note,
    this.suggestedDrugNames = const [],
  });

  final int detectionIdx;
  final List<dynamic> bbox;
  final double score;
  final String assignmentStatus;
  final String? assignedDrugName;
  final String? note;
  final List<String> suggestedDrugNames;

  factory PillDetectionItem.fromJson(Map<String, dynamic> json) =>
      PillDetectionItem(
        detectionIdx: json['detectionIdx'] as int? ?? 0,
        bbox: (json['bbox'] as List<dynamic>? ?? const []),
        score: (json['score'] as num?)?.toDouble() ?? 0,
        assignmentStatus: json['assignmentStatus']?.toString() ?? 'unassigned',
        assignedDrugName: json['assignedDrugName']?.toString(),
        note: json['note']?.toString(),
        suggestedDrugNames:
            (json['suggestedDrugNames'] as List<dynamic>? ?? const [])
                .map((e) => e.toString())
                .toList(),
      );
}

class PillVerificationSummary {
  const PillVerificationSummary({
    required this.totalDetections,
    required this.assigned,
    required this.unknown,
    required this.extra,
    required this.unassigned,
    required this.missingExpected,
  });

  final int totalDetections;
  final int assigned;
  final int unknown;
  final int extra;
  final int unassigned;
  final int missingExpected;

  factory PillVerificationSummary.fromJson(Map<String, dynamic> json) =>
      PillVerificationSummary(
        totalDetections: json['totalDetections'] as int? ?? 0,
        assigned: json['assigned'] as int? ?? 0,
        unknown: json['unknown'] as int? ?? 0,
        extra: json['extra'] as int? ?? 0,
        unassigned: json['unassigned'] as int? ?? 0,
        missingExpected: json['missingExpected'] as int? ?? 0,
      );
}

class PillVerificationSession {
  const PillVerificationSession({
    required this.sessionId,
    required this.occurrenceId,
    required this.status,
    required this.expectedMedications,
    required this.detections,
    required this.summary,
    this.note,
  });

  final String sessionId;
  final String occurrenceId;
  final String status;
  final List<ExpectedMedication> expectedMedications;
  final List<PillDetectionItem> detections;
  final PillVerificationSummary summary;
  final String? note;

  factory PillVerificationSession.fromJson(Map<String, dynamic> json) =>
      PillVerificationSession(
        sessionId: json['sessionId']?.toString() ?? '',
        occurrenceId: json['occurrenceId']?.toString() ?? '',
        status: json['status']?.toString() ?? 'draft',
        expectedMedications:
            (json['expectedMedications'] as List<dynamic>? ?? const [])
                .map(
                  (e) => ExpectedMedication.fromJson(e as Map<String, dynamic>),
                )
                .toList(),
        detections: (json['detections'] as List<dynamic>? ?? const [])
            .map((e) => PillDetectionItem.fromJson(e as Map<String, dynamic>))
            .toList(),
        summary: PillVerificationSummary.fromJson(
          (json['summary'] as Map<String, dynamic>? ?? const {}),
        ),
        note: json['note']?.toString(),
      );
}
