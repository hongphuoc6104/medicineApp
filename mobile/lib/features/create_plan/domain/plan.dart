/// Drug item in a plan (editable by user after scan or manual entry).
class PlanDrugItem {
  String name;
  String dosage;
  int pillsPerDose;
  String frequency; // daily, twice_daily, three_daily
  List<String> times; // ["07:00", "12:00", "19:00"]
  int totalDays;
  String notes;

  PlanDrugItem({
    required this.name,
    this.dosage = '',
    this.pillsPerDose = 1,
    this.frequency = 'daily',
    List<String>? times,
    this.totalDays = 7,
    this.notes = '',
  }) : times = times ?? ['07:00'];

  Map<String, dynamic> toCreateJson(String startDate) => {
    'drugName': name,
    'dosage': dosage,
    'frequency': frequency,
    'times': times,
    'pillsPerDose': pillsPerDose,
    'totalDays': totalDays,
    'startDate': startDate,
    if (notes.trim().isNotEmpty) 'notes': notes.trim(),
  };

  PlanDrugItem copyWith({
    String? name,
    String? dosage,
    int? pillsPerDose,
    String? frequency,
    List<String>? times,
    int? totalDays,
    String? notes,
  }) {
    return PlanDrugItem(
      name: name ?? this.name,
      dosage: dosage ?? this.dosage,
      pillsPerDose: pillsPerDose ?? this.pillsPerDose,
      frequency: frequency ?? this.frequency,
      times: times ?? List<String>.from(this.times),
      totalDays: totalDays ?? this.totalDays,
      notes: notes ?? this.notes,
    );
  }

  factory PlanDrugItem.fromPlan(Plan plan) {
    return PlanDrugItem(
      name: plan.drugName,
      dosage: plan.dosage ?? '',
      pillsPerDose: plan.pillsPerDose,
      frequency: plan.frequency,
      times: List<String>.from(plan.times),
      totalDays: plan.totalDays ?? 7,
      notes: plan.notes ?? '',
    );
  }
}

/// Plan model — matches GET /api/plans response.
class Plan {
  final String id;
  final String drugName;
  final String? dosage;
  final String frequency;
  final List<String> times;
  final int pillsPerDose;
  final int? totalDays;
  final String startDate;
  final String? endDate;
  final bool isActive;
  final String? notes;

  const Plan({
    required this.id,
    required this.drugName,
    this.dosage,
    required this.frequency,
    required this.times,
    this.pillsPerDose = 1,
    this.totalDays,
    required this.startDate,
    this.endDate,
    this.isActive = true,
    this.notes,
  });

  factory Plan.fromJson(Map<String, dynamic> json) => Plan(
    id: json['id'] as String,
    drugName: json['drug_name'] as String? ?? json['drugName'] as String? ?? '',
    dosage: json['dosage'] as String?,
    frequency: json['frequency'] as String? ?? 'daily',
    times: (json['times'] as List?)?.cast<String>() ?? [],
    pillsPerDose:
        json['pills_per_dose'] as int? ?? json['pillsPerDose'] as int? ?? 1,
    totalDays: json['total_days'] as int? ?? json['totalDays'] as int?,
    startDate:
        json['start_date'] as String? ?? json['startDate'] as String? ?? '',
    endDate: json['end_date'] as String? ?? json['endDate'] as String?,
    isActive: json['is_active'] as bool? ?? json['isActive'] as bool? ?? true,
    notes: json['notes'] as String?,
  );

  Map<String, dynamic> toUpdateJson() => {
    'drugName': drugName,
    if (dosage != null) 'dosage': dosage,
    'frequency': frequency,
    'times': times,
    'pillsPerDose': pillsPerDose,
    if (totalDays != null) 'totalDays': totalDays,
    'startDate': startDate,
    if (endDate != null) 'endDate': endDate,
    if (notes != null && notes!.trim().isNotEmpty) 'notes': notes!.trim(),
  };

  Plan copyWith({
    String? id,
    String? drugName,
    String? dosage,
    String? frequency,
    List<String>? times,
    int? pillsPerDose,
    int? totalDays,
    String? startDate,
    String? endDate,
    bool? isActive,
    String? notes,
  }) {
    return Plan(
      id: id ?? this.id,
      drugName: drugName ?? this.drugName,
      dosage: dosage ?? this.dosage,
      frequency: frequency ?? this.frequency,
      times: times ?? List<String>.from(this.times),
      pillsPerDose: pillsPerDose ?? this.pillsPerDose,
      totalDays: totalDays ?? this.totalDays,
      startDate: startDate ?? this.startDate,
      endDate: endDate ?? this.endDate,
      isActive: isActive ?? this.isActive,
      notes: notes ?? this.notes,
    );
  }
}
