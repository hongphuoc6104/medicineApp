import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../domain/reconciliation_result.dart';

/// Repository for calling reconciliation APIs
class ReconciliationRepository {
  final Dio _dio;

  ReconciliationRepository(this._dio);

  /// Compare a new scan vs the user's active plan
  Future<ReconciliationResult> compareScanVsActivePlan(String scanId) async {
    final response = await _dio.post(
      '/reconciliation/scan-vs-active-plan',
      data: {'scanId': scanId},
    );
    return ReconciliationResult.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  /// Compare a scan vs previous scan
  Future<ReconciliationResult> compareScanVsPreviousScan(String scanId, {String? previousScanId}) async {
    final response = await _dio.post(
      '/reconciliation/scan-vs-previous-scan',
      data: {
        'scanId': scanId,
        if (previousScanId != null) 'previousScanId': previousScanId,
      },
    );
    return ReconciliationResult.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  /// Compare dispensed (package/label) text vs active plan
  Future<ReconciliationResult> compareDispensedTextVsActivePlan(Map<String, dynamic> payload) async {
    final response = await _dio.post(
      '/reconciliation/dispensed-text-vs-active-plan',
      data: payload,
    );
    return ReconciliationResult.fromJson(response.data['data'] as Map<String, dynamic>);
  }
}

final reconciliationRepositoryProvider = Provider<ReconciliationRepository>((ref) {
  return ReconciliationRepository(ref.watch(dioProvider));
});
