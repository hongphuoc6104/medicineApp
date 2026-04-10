class DoseExpectedMedication {
  const DoseExpectedMedication({
    required this.planId,
    required this.drugName,
    this.occurrenceId,
    this.dosage,
    this.pillsPerDose,
  });

  final String planId;
  final String drugName;
  final String? occurrenceId;
  final String? dosage;
  final int? pillsPerDose;

  factory DoseExpectedMedication.fromJson(Map<String, dynamic> json) =>
      DoseExpectedMedication(
        planId: json['planId'] as String? ?? '',
        drugName: json['drugName'] as String? ?? '',
        occurrenceId: json['occurrenceId'] as String?,
        dosage: json['dosage'] as String?,
        pillsPerDose: json['pillsPerDose'] as int?,
      );
}

class TodayDose {
  const TodayDose({
    required this.occurrenceId,
    required this.planId,
    required this.drugName,
    required this.time,
    required this.scheduledTime,
    required this.status,
    this.dosage,
    this.pillsPerDose,
    this.notes,
    this.takenAt,
    this.note,
    this.hasReferenceProfile = false,
    this.referenceProfileStatus,
    this.verificationReady = false,
    this.expectedMedications = const [],
    this.missingReferenceDrugNames = const [],
  });

  final String occurrenceId;
  final String planId;
  final String drugName;
  final String time;
  final String scheduledTime;
  final String status;
  final String? dosage;
  final int? pillsPerDose;
  final String? notes;
  final String? takenAt;
  final String? note;
  final bool hasReferenceProfile;
  final String? referenceProfileStatus;
  final bool verificationReady;
  final List<DoseExpectedMedication> expectedMedications;
  final List<String> missingReferenceDrugNames;

  factory TodayDose.fromJson(Map<String, dynamic> json) => TodayDose(
    occurrenceId: json['occurrenceId'] as String? ?? '',
    planId: json['planId'] as String? ?? '',
    drugName: json['drugName'] as String? ?? '',
    time: json['time'] as String? ?? '',
    scheduledTime: json['scheduledTime'] as String? ?? '',
    status: json['status'] as String? ?? 'pending',
    dosage: json['dosage'] as String?,
    pillsPerDose: json['pillsPerDose'] as int?,
    notes: json['notes'] as String?,
    takenAt: json['takenAt'] as String?,
    note: json['note'] as String?,
    hasReferenceProfile: json['hasReferenceProfile'] as bool? ?? false,
    referenceProfileStatus: json['referenceProfileStatus'] as String?,
    verificationReady: json['verificationReady'] as bool? ?? false,
    expectedMedications:
        (json['expectedMedications'] as List<dynamic>? ?? const [])
            .map(
              (e) => DoseExpectedMedication.fromJson(e as Map<String, dynamic>),
            )
            .toList(),
    missingReferenceDrugNames:
        (json['missingReferenceDrugNames'] as List<dynamic>? ?? const [])
            .map((e) => e.toString())
            .toList(),
  );
}

class TodaySummary {
  const TodaySummary({
    required this.total,
    required this.taken,
    required this.pending,
    required this.skipped,
    required this.missed,
  });

  final int total;
  final int taken;
  final int pending;
  final int skipped;
  final int missed;

  factory TodaySummary.fromJson(Map<String, dynamic> json) => TodaySummary(
    total: json['total'] as int? ?? 0,
    taken: json['taken'] as int? ?? 0,
    pending: json['pending'] as int? ?? 0,
    skipped: json['skipped'] as int? ?? 0,
    missed: json['missed'] as int? ?? 0,
  );
}

class TodaySchedule {
  const TodaySchedule({
    required this.date,
    required this.doses,
    required this.summary,
  });

  final String date;
  final List<TodayDose> doses;
  final TodaySummary summary;

  const TodaySchedule.empty()
    : date = '',
      doses = const [],
      summary = const TodaySummary(
        total: 0,
        taken: 0,
        pending: 0,
        skipped: 0,
        missed: 0,
      );

  factory TodaySchedule.fromJson(Map<String, dynamic> json) => TodaySchedule(
    date: json['date'] as String? ?? '',
    doses: (json['doses'] as List<dynamic>? ?? const [])
        .map((e) => TodayDose.fromJson(e as Map<String, dynamic>))
        .toList(),
    summary: TodaySummary.fromJson(
      (json['summary'] as Map<String, dynamic>? ?? const {}),
    ),
  );
}
