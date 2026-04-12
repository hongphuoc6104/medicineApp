import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../create_plan/data/offline_dose_queue.dart';
import '../../create_plan/data/plan_repository.dart';
import '../domain/today_schedule.dart';
import 'today_schedule_cache.dart';

class TodayScheduleNotifier extends AsyncNotifier<TodaySchedule> {
  @override
  Future<TodaySchedule> build() async {
    return _loadAndRevalidate();
  }

  Future<TodaySchedule> _loadAndRevalidate() async {
    final cache = ref.read(todayScheduleCacheProvider);
    final cached = await cache.load();

    if (cached != null) {
      state = AsyncValue.data(await _applyOfflineQueue(cached));
    }

    try {
      await flushOfflineQueue();
      final repo = ref.read(planRepositoryProvider);
      final fresh = await repo.getTodaySchedule();

      await cache.save(fresh);

      final finalFresh = await _applyOfflineQueue(fresh);
      return finalFresh;
    } catch (e, st) {
      if (cached != null) {
        return await _applyOfflineQueue(cached);
      }
      Error.throwWithStackTrace(e, st);
    }
  }

  Future<TodaySchedule> _applyOfflineQueue(TodaySchedule schedule) async {
    final queue = ref.read(offlineDoseQueueProvider);
    final pendingLogs = await queue.getPendingLogs();

    if (pendingLogs.isEmpty) return schedule;

    final logMap = { for (var e in pendingLogs) e.occurrenceId : e };

    final updatedDoses = schedule.doses.map((d) {
      if (logMap.containsKey(d.occurrenceId)) {
        return d.copyWith(status: logMap[d.occurrenceId]!.status);
      }
      return d;
    }).toList();

    final updatedSummary = TodaySummary(
      total: updatedDoses.length,
      taken: updatedDoses.where((d) => d.status == 'taken').length,
      pending: updatedDoses.where((d) => d.status == 'pending').length,
      skipped: updatedDoses.where((d) => d.status == 'skipped').length,
      missed: updatedDoses.where((d) => d.status == 'missed').length,
    );

    return schedule.copyWith(doses: updatedDoses, summary: updatedSummary);
  }

  Future<int> flushOfflineQueue() async {
    final queue = ref.read(offlineDoseQueueProvider);
    return queue.flush();
  }

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() async {
      await flushOfflineQueue();
      final repo = ref.read(planRepositoryProvider);
      final fresh = await repo.getTodaySchedule();
      
      final cache = ref.read(todayScheduleCacheProvider);
      await cache.save(fresh);
      
      return await _applyOfflineQueue(fresh);
    });
  }

  Future<bool> markDose({
    required TodayDose dose,
    required String status,
  }) async {
    final queue = ref.read(offlineDoseQueueProvider);

    try {
      final repo = ref.read(planRepositoryProvider);
      await repo.logDose(
        planId: dose.planId,
        scheduledTime: dose.scheduledTime,
        status: status,
        occurrenceId: dose.occurrenceId,
      );
      await refresh();
      return true;
    } catch (_) {
      await queue.enqueue(
        PendingDoseLog(
          planId: dose.planId,
          scheduledTime: dose.scheduledTime,
          status: status,
          occurrenceId: dose.occurrenceId,
          queuedAt: DateTime.now().toUtc().toIso8601String(),
        ),
      );

      final current = state.asData?.value;
      if (current != null) {
        final updatedDoses = current.doses.map((d) {
          if (d.occurrenceId == dose.occurrenceId) {
            return d.copyWith(status: status);
          }
          return d;
        }).toList();

        final updatedSummary = TodaySummary(
          total: updatedDoses.length,
          taken: updatedDoses.where((d) => d.status == 'taken').length,
          pending: updatedDoses.where((d) => d.status == 'pending').length,
          skipped: updatedDoses.where((d) => d.status == 'skipped').length,
          missed: updatedDoses.where((d) => d.status == 'missed').length,
        );

        state = AsyncValue.data(
          current.copyWith(
            doses: updatedDoses,
            summary: updatedSummary,
          ),
        );
      }

      return true;
    }
  }
}

final todayScheduleNotifierProvider =
    AsyncNotifierProvider<TodayScheduleNotifier, TodaySchedule>(
      TodayScheduleNotifier.new,
    );
