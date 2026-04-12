import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/notifications/notification_service.dart';
import '../../create_plan/data/plan_repository.dart';
import '../../home/data/plan_notifier.dart';
import 'settings_repository.dart';

class SettingsState {
  const SettingsState({this.remindersEnabled = true, this.isLoading = false});

  final bool remindersEnabled;
  final bool isLoading;

  SettingsState copyWith({bool? remindersEnabled, bool? isLoading}) {
    return SettingsState(
      remindersEnabled: remindersEnabled ?? this.remindersEnabled,
      isLoading: isLoading ?? this.isLoading,
    );
  }
}

class SettingsNotifier extends AsyncNotifier<SettingsState> {
  @override
  Future<SettingsState> build() async {
    final repo = ref.read(settingsRepositoryProvider);
    final enabled = await repo.getRemindersEnabled();
    return SettingsState(remindersEnabled: enabled);
  }

  Future<void> setRemindersEnabled(bool enabled) async {
    final repo = ref.read(settingsRepositoryProvider);
    await repo.setRemindersEnabled(enabled);
    final notificationService = ref.read(notificationServiceProvider);
    if (!enabled) {
      await notificationService.cancelAllNotifications();
    } else {
      final plansAsync = ref.read(planNotifierProvider);
      final cachedPlans = plansAsync.asData?.value.plans;
      if (cachedPlans != null) {
        await notificationService.rescheduleAllPlans(cachedPlans);
      } else {
        final planRepository = ref.read(planRepositoryProvider);
        final plans = await planRepository.getPlans(activeOnly: true);
        await notificationService.rescheduleAllPlans(plans);
      }
    }
    state = AsyncValue.data(SettingsState(remindersEnabled: enabled));
  }
}

final settingsNotifierProvider =
    AsyncNotifierProvider<SettingsNotifier, SettingsState>(
      SettingsNotifier.new,
    );
