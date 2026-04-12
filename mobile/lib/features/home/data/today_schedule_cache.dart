import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../domain/today_schedule.dart';

class TodayScheduleCache {
  static const _storage = FlutterSecureStorage();
  static const _cacheKey = 'today_schedule_cache_v1';

  Future<TodaySchedule?> load() async {
    final raw = await _storage.read(key: _cacheKey);
    if (raw == null || raw.isEmpty) return null;

    try {
      final json = jsonDecode(raw) as Map<String, dynamic>;
      final schedule = TodaySchedule.fromJson(json);

      // Validate date matches current system date
      final now = DateTime.now();
      final todayStr = '${now.year.toString().padLeft(4, '0')}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
      if (schedule.date.startsWith(todayStr)) {
         return schedule;
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  Future<void> save(TodaySchedule schedule) async {
    final encoded = jsonEncode(schedule.toJson());
    await _storage.write(key: _cacheKey, value: encoded);
  }

  Future<void> clear() async {
    await _storage.delete(key: _cacheKey);
  }
}

final todayScheduleCacheProvider = Provider<TodayScheduleCache>((ref) {
  return TodayScheduleCache();
});
