import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../../core/network/dio_client.dart';

class PendingDoseLog {
  const PendingDoseLog({
    required this.planId,
    required this.scheduledTime,
    required this.status,
    required this.occurrenceId,
    required this.queuedAt,
    this.note,
  });

  final String planId;
  final String scheduledTime;
  final String status;
  final String occurrenceId;
  final String queuedAt;
  final String? note;

  Map<String, dynamic> toJson() => {
    'planId': planId,
    'scheduledTime': scheduledTime,
    'status': status,
    'occurrenceId': occurrenceId,
    'queuedAt': queuedAt,
    if (note != null && note!.isNotEmpty) 'note': note,
  };

  factory PendingDoseLog.fromJson(Map<String, dynamic> json) => PendingDoseLog(
    planId: json['planId']?.toString() ?? '',
    scheduledTime: json['scheduledTime']?.toString() ?? '',
    status: json['status']?.toString() ?? 'pending',
    occurrenceId: json['occurrenceId']?.toString() ?? '',
    queuedAt:
        json['queuedAt']?.toString() ??
        DateTime.now().toUtc().toIso8601String(),
    note: json['note']?.toString(),
  );
}

class OfflineDoseQueue {
  OfflineDoseQueue(this._dio);

  final Dio _dio;
  static const _storage = FlutterSecureStorage();
  static const _queueKey = 'offline_dose_log_queue_v1';

  Future<List<PendingDoseLog>> _loadQueue() async {
    final raw = await _storage.read(key: _queueKey);
    if (raw == null || raw.isEmpty) {
      return const [];
    }

    try {
      final list = jsonDecode(raw) as List<dynamic>;
      return list
          .map((e) => PendingDoseLog.fromJson(e as Map<String, dynamic>))
          .toList();
    } catch (_) {
      await _storage.delete(key: _queueKey);
      return const [];
    }
  }

  Future<void> _saveQueue(List<PendingDoseLog> queue) async {
    if (queue.isEmpty) {
      await _storage.delete(key: _queueKey);
      return;
    }
    final encoded = jsonEncode(queue.map((e) => e.toJson()).toList());
    await _storage.write(key: _queueKey, value: encoded);
  }

  Future<void> enqueue(PendingDoseLog item) async {
    final queue = await _loadQueue();

    final deduped =
        queue.where((it) => it.occurrenceId != item.occurrenceId).toList()
          ..add(item);

    await _saveQueue(deduped);
  }

  Future<int> pendingCount() async {
    final queue = await _loadQueue();
    return queue.length;
  }

  Future<int> flush() async {
    final queue = await _loadQueue();
    if (queue.isEmpty) {
      return 0;
    }

    final remaining = <PendingDoseLog>[];
    var synced = 0;

    for (final item in queue) {
      try {
        await _dio.post(
          '/plans/${item.planId}/log',
          data: {
            'scheduledTime': item.scheduledTime,
            'status': item.status,
            'occurrenceId': item.occurrenceId,
            if (item.note != null && item.note!.isNotEmpty) 'note': item.note,
          },
        );
        synced += 1;
      } on DioException {
        remaining.add(item);
      } catch (_) {
        remaining.add(item);
      }
    }

    await _saveQueue(remaining);
    return synced;
  }
}

final offlineDoseQueueProvider = Provider<OfflineDoseQueue>((ref) {
  return OfflineDoseQueue(ref.watch(dioProvider));
});
