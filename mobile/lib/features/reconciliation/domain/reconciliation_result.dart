import 'package:flutter/foundation.dart';

class ReconciliationResult {
  final String compareType;
  final ReconciliationMeta summary;
  final TransitionOfCare transitionOfCare;

  const ReconciliationResult({
    required this.compareType,
    required this.summary,
    required this.transitionOfCare,
  });

  factory ReconciliationResult.fromJson(Map<String, dynamic> json) {
    return ReconciliationResult(
      compareType: json['compareType'] as String? ?? '',
      summary: ReconciliationMeta.fromJson(json['summary'] as Map<String, dynamic>? ?? {}),
      transitionOfCare: TransitionOfCare.fromJson(json['transitionOfCare'] as Map<String, dynamic>? ?? {}),
    );
  }
}

class ReconciliationMeta {
  final int added;
  final int removed;
  final int substitutions;
  final int duplicates;
  final int strengthChanged;
  final int dosageFormChanged;
  final int manualReview;
  final bool hasChanges;
  final bool requiresManualReview;

  const ReconciliationMeta({
    this.added = 0,
    this.removed = 0,
    this.substitutions = 0,
    this.duplicates = 0,
    this.strengthChanged = 0,
    this.dosageFormChanged = 0,
    this.manualReview = 0,
    this.hasChanges = false,
    this.requiresManualReview = false,
  });

  factory ReconciliationMeta.fromJson(Map<String, dynamic> json) {
    return ReconciliationMeta(
      added: json['added'] as int? ?? 0,
      removed: json['removed'] as int? ?? 0,
      substitutions: json['substitutions'] as int? ?? 0,
      duplicates: json['duplicates'] as int? ?? 0,
      strengthChanged: json['strengthChanged'] as int? ?? 0,
      dosageFormChanged: json['dosageFormChanged'] as int? ?? 0,
      manualReview: json['manualReview'] as int? ?? 0,
      hasChanges: json['hasChanges'] as bool? ?? false,
      requiresManualReview: json['requiresManualReview'] as bool? ?? false,
    );
  }
}

class TransitionOfCare {
  final List<String> know;
  final List<String> check;
  final List<String> ask;
  final List<RiskCard> riskCards;

  const TransitionOfCare({
    this.know = const [],
    this.check = const [],
    this.ask = const [],
    this.riskCards = const [],
  });

  factory TransitionOfCare.fromJson(Map<String, dynamic> json) {
    return TransitionOfCare(
      know: (json['know'] as List?)?.map((e) => e.toString()).toList() ?? [],
      check: (json['check'] as List?)?.map((e) => e.toString()).toList() ?? [],
      ask: (json['ask'] as List?)?.map((e) => e.toString()).toList() ?? [],
      riskCards: (json['riskCards'] as List?)
              ?.map((e) => RiskCard.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}

class RiskCard {
  final String level;
  final String label;
  final String detail;

  const RiskCard({
    required this.level,
    required this.label,
    required this.detail,
  });

  factory RiskCard.fromJson(Map<String, dynamic> json) {
    return RiskCard(
      level: json['level'] as String? ?? 'info',
      label: json['label'] as String? ?? '',
      detail: json['detail'] as String? ?? '',
    );
  }
}
