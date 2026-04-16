import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../../drug/data/drug_repository.dart';

class InteractionItem {
  const InteractionItem({
    required this.drugA,
    required this.drugB,
    required this.ingredientA,
    required this.ingredientB,
    required this.severity,
    required this.severityOriginal,
    required this.warning,
  });

  final String drugA;
  final String drugB;
  final String ingredientA;
  final String ingredientB;
  final String severity;
  final String severityOriginal;
  final String warning;

  factory InteractionItem.fromJson(Map<String, dynamic> json) {
    return InteractionItem(
      drugA: json['drugA']?.toString() ?? '',
      drugB: json['drugB']?.toString() ?? '',
      ingredientA: json['ingredientA']?.toString() ?? '',
      ingredientB: json['ingredientB']?.toString() ?? '',
      severity: json['severity']?.toString() ?? 'unknown',
      severityOriginal: json['severityOriginal']?.toString() ?? '',
      warning: json['warning']?.toString() ?? '',
    );
  }
}

class InteractionGroup {
  const InteractionGroup({
    required this.severity,
    required this.severityOriginal,
    required this.count,
    required this.interactions,
  });

  final String severity;
  final String severityOriginal;
  final int count;
  final List<InteractionItem> interactions;

  factory InteractionGroup.fromJson(Map<String, dynamic> json) {
    final interactionList = (json['interactions'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(InteractionItem.fromJson)
        .toList();

    return InteractionGroup(
      severity: json['severity']?.toString() ?? 'unknown',
      severityOriginal: json['severityOriginal']?.toString() ?? '',
      count: (json['count'] as num?)?.toInt() ?? interactionList.length,
      interactions: interactionList,
    );
  }
}

class InteractionCheckResult {
  const InteractionCheckResult({
    required this.hasInteractions,
    required this.totalInteractions,
    required this.highestSeverity,
    required this.severitySummary,
    required this.interactions,
    required this.groups,
    required this.message,
  });

  final bool hasInteractions;
  final int totalInteractions;
  final String highestSeverity;
  final Map<String, int> severitySummary;
  final List<InteractionItem> interactions;
  final List<InteractionGroup> groups;
  final String? message;

  factory InteractionCheckResult.fromJson(Map<String, dynamic> json) {
    final summaryRaw =
        json['severitySummary'] as Map<String, dynamic>? ?? const {};
    final summary = <String, int>{
      'contraindicated': (summaryRaw['contraindicated'] as num?)?.toInt() ?? 0,
      'major': (summaryRaw['major'] as num?)?.toInt() ?? 0,
      'moderate': (summaryRaw['moderate'] as num?)?.toInt() ?? 0,
      'minor': (summaryRaw['minor'] as num?)?.toInt() ?? 0,
      'caution': (summaryRaw['caution'] as num?)?.toInt() ?? 0,
      'unknown': (summaryRaw['unknown'] as num?)?.toInt() ?? 0,
    };

    final interactionList = (json['interactions'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(InteractionItem.fromJson)
        .toList();

    final groupList = (json['groups'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(InteractionGroup.fromJson)
        .toList();

    return InteractionCheckResult(
      hasInteractions:
          json['hasInteractions'] as bool? ?? interactionList.isNotEmpty,
      totalInteractions:
          (json['totalInteractions'] as num?)?.toInt() ??
          interactionList.length,
      highestSeverity: json['highestSeverity']?.toString() ?? 'unknown',
      severitySummary: summary,
      interactions: interactionList,
      groups: groupList,
      message: json['message']?.toString(),
    );
  }
}

class ActiveIngredientSuggestion {
  const ActiveIngredientSuggestion({required this.name});

  final String name;

  factory ActiveIngredientSuggestion.fromJson(Map<String, dynamic> json) {
    return ActiveIngredientSuggestion(name: json['name']?.toString() ?? '');
  }
}

class DrugInteractionRepository {
  DrugInteractionRepository(this._dio);

  final Dio _dio;

  Future<InteractionCheckResult> checkByDrugs(List<String> drugNames) async {
    final response = await _dio.post(
      '/drug-interactions/check-by-drugs',
      data: {'drugNames': drugNames},
    );

    return InteractionCheckResult.fromJson(
      response.data['data'] as Map<String, dynamic>? ?? const {},
    );
  }

  Future<List<ActiveIngredientSuggestion>> searchActiveIngredients(
    String keyword,
  ) async {
    final response = await _dio.get(
      '/drug-interactions/search-active-ingredients',
      queryParameters: {'keyword': keyword},
    );

    final data = response.data['data'] as Map<String, dynamic>? ?? const {};
    final list = (data['suggestions'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(ActiveIngredientSuggestion.fromJson)
        .where((item) => item.name.trim().isNotEmpty)
        .toList();

    return list;
  }

  Future<InteractionCheckResult> checkByActiveIngredients(
    List<String> activeIngredients,
  ) async {
    final response = await _dio.post(
      '/drug-interactions/check-by-active-ingredients',
      data: {'activeIngredients': activeIngredients},
    );

    return InteractionCheckResult.fromJson(
      response.data['data'] as Map<String, dynamic>? ?? const {},
    );
  }

  Future<InteractionCheckResult> getByActiveIngredient(
    String ingredientName,
  ) async {
    final response = await _dio.get(
      '/drug-interactions/by-active-ingredient',
      queryParameters: {'ingredientName': ingredientName},
    );

    return InteractionCheckResult.fromJson(
      response.data['data'] as Map<String, dynamic>? ?? const {},
    );
  }
}

final drugInteractionRepositoryProvider = Provider<DrugInteractionRepository>((
  ref,
) {
  return DrugInteractionRepository(ref.watch(dioProvider));
});

final lookupDrugSuggestionsProvider = FutureProvider.family
    .autoDispose<List<DrugSearchItem>, String>((ref, keyword) async {
      final trimmed = keyword.trim();
      if (trimmed.length < 2) {
        return const [];
      }

      final repo = ref.read(drugRepositoryProvider);
      final page = await repo.search(trimmed, limit: 10);
      return page.items;
    });
