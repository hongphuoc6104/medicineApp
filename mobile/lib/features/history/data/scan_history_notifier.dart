import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'scan_history_repository.dart';

class ScanHistoryNotifier extends AsyncNotifier<ScanHistoryPage> {
  @override
  Future<ScanHistoryPage> build() async {
    final repo = ref.read(scanHistoryRepositoryProvider);
    return repo.getHistory();
  }

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() async {
      final repo = ref.read(scanHistoryRepositoryProvider);
      return repo.getHistory();
    });
  }
}

final scanHistoryNotifierProvider =
    AsyncNotifierProvider<ScanHistoryNotifier, ScanHistoryPage>(
      ScanHistoryNotifier.new,
    );
