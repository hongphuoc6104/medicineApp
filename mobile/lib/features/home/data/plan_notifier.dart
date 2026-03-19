import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/notifications/notification_service.dart';
import '../../create_plan/data/plan_repository.dart';
import '../../create_plan/domain/plan.dart';
import '../../settings/data/settings_repository.dart';

/// State for all active plans
class PlansState {
  final List<Plan> plans;
  final bool isLoading;
  final String? error;

  const PlansState({this.plans = const [], this.isLoading = false, this.error});

  bool get hasPlans => plans.isNotEmpty;

  PlansState copyWith({List<Plan>? plans, bool? isLoading, String? error}) {
    return PlansState(
      plans: plans ?? this.plans,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

class PlanNotifier extends AsyncNotifier<PlansState> {
  @override
  Future<PlansState> build() async {
    return _loadPlans();
  }

  Future<PlansState> _loadPlans() async {
    try {
      final repo = ref.read(planRepositoryProvider);
      final plans = await repo.getPlans(activeOnly: true);

      final notificationService = ref.read(notificationServiceProvider);
      final settingsRepo = ref.read(settingsRepositoryProvider);
      final remindersEnabled = await settingsRepo.getRemindersEnabled();
      if (remindersEnabled) {
        await notificationService.rescheduleAllPlans(plans);
      } else {
        await notificationService.cancelAllNotifications();
      }

      return PlansState(plans: plans);
    } catch (e) {
      return PlansState(error: e.toString());
    }
  }

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() => _loadPlans());
  }
}

final planNotifierProvider = AsyncNotifierProvider<PlanNotifier, PlansState>(
  PlanNotifier.new,
);
