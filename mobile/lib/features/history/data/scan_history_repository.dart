import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';

class ScanHistoryItem {
  const ScanHistoryItem({
    required this.id,
    required this.drugCount,
    required this.scannedAt,
    required this.qualityState,
    required this.rejectReason,
    this.result,
  });

  final String id;
  final int drugCount;
  final DateTime scannedAt;
  final String qualityState;
  final String? rejectReason;
  final Map<String, dynamic>? result;

  factory ScanHistoryItem.fromJson(Map<String, dynamic> json) =>
      ScanHistoryItem(
        id: json['id']?.toString() ?? '',
        drugCount: json['drug_count'] as int? ?? 0,
        scannedAt:
            DateTime.tryParse(json['scanned_at']?.toString() ?? '') ??
            DateTime.now(),
        qualityState: json['quality_state']?.toString() ?? 'GOOD',
        rejectReason: json['reject_reason']?.toString(),
        result: json['result'] as Map<String, dynamic>?,
      );
}

class ScanHistoryDetail {
  const ScanHistoryDetail({
    required this.id,
    required this.drugCount,
    required this.scannedAt,
    required this.qualityState,
    required this.drugs,
    this.rejectReason,
    this.qualityScore,
    this.guidance,
    this.unresolvedCount = 0,
    this.qualityMetrics = const {},
  });

  final String id;
  final int drugCount;
  final DateTime scannedAt;
  final String qualityState;
  final String? rejectReason;
  final double? qualityScore;
  final String? guidance;
  final int unresolvedCount;
  final Map<String, dynamic> qualityMetrics;
  final List<Map<String, dynamic>> drugs;

  factory ScanHistoryDetail.fromJson(Map<String, dynamic> json) =>
      ScanHistoryDetail(
        id: json['id']?.toString() ?? '',
        drugCount: json['drugCount'] as int? ?? 0,
        scannedAt:
            DateTime.tryParse(json['scannedAt']?.toString() ?? '') ??
            DateTime.now(),
        qualityState: json['qualityState']?.toString() ?? 'GOOD',
        rejectReason: json['rejectReason']?.toString(),
        qualityScore: (json['qualityScore'] as num?)?.toDouble(),
        guidance: json['guidance']?.toString(),
        unresolvedCount: json['unresolvedCount'] as int? ?? 0,
        qualityMetrics:
            (json['qualityMetrics'] as Map<String, dynamic>?) ?? const {},
        drugs: (json['drugs'] as List<dynamic>? ?? const [])
            .map((e) => Map<String, dynamic>.from(e as Map))
            .toList(),
      );
}

class ScanHistoryPage {
  const ScanHistoryPage({
    required this.items,
    required this.total,
    required this.page,
    required this.limit,
  });

  final List<ScanHistoryItem> items;
  final int total;
  final int page;
  final int limit;
}

class ScanHistoryRepository {
  ScanHistoryRepository(this._dio);

  final Dio _dio;

  Future<ScanHistoryPage> getHistory({int page = 1, int limit = 20}) async {
    final response = await _dio.get(
      '/scan/history',
      queryParameters: {'page': page, 'limit': limit},
    );

    final items = (response.data['data'] as List<dynamic>? ?? const [])
        .map((e) => ScanHistoryItem.fromJson(e as Map<String, dynamic>))
        .toList();
    final pagination =
        response.data['pagination'] as Map<String, dynamic>? ??
        const <String, dynamic>{};

    return ScanHistoryPage(
      items: items,
      total: pagination['total'] as int? ?? items.length,
      page: pagination['page'] as int? ?? page,
      limit: pagination['limit'] as int? ?? limit,
    );
  }

  Future<ScanHistoryDetail> getHistoryDetail(String id) async {
    final response = await _dio.get('/scan/history/$id');
    return ScanHistoryDetail.fromJson(
      response.data['data'] as Map<String, dynamic>,
    );
  }
}

final scanHistoryRepositoryProvider = Provider<ScanHistoryRepository>((ref) {
  return ScanHistoryRepository(ref.watch(dioProvider));
});
