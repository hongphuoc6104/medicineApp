import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../create_plan/data/offline_dose_queue.dart';
import '../../create_plan/data/plan_repository.dart';
import '../domain/today_schedule.dart';

class TodayScheduleNotifier extends AsyncNotifier<TodaySchedule> {
  @override
  Future<TodaySchedule> build() async {
    final repo = ref.read(planRepositoryProvider);
    return repo.getTodaySchedule();
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
      return repo.getTodaySchedule();
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
            return TodayDose(
              occurrenceId: d.occurrenceId,
              planId: d.planId,
              drugName: d.drugName,
              time: d.time,
              scheduledTime: d.scheduledTime,
              status: status,
              dosage: d.dosage,
              pillsPerDose: d.pillsPerDose,
              notes: d.notes,
              takenAt: d.takenAt,
              note: d.note,
              hasReferenceProfile: d.hasReferenceProfile,
              referenceProfileStatus: d.referenceProfileStatus,
              verificationReady: d.verificationReady,
              expectedMedications: d.expectedMedications,
              missingReferenceDrugNames: d.missingReferenceDrugNames,
            );
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
          TodaySchedule(
            date: current.date,
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
