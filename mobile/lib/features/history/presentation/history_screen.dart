import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../core/theme/app_theme.dart';
import '../data/medication_logs_notifier.dart';
import '../data/scan_history_notifier.dart';

class HistoryScreen extends ConsumerWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scanAsync = ref.watch(scanHistoryNotifierProvider);
    final logAsync = ref.watch(medicationLogsNotifierProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Lịch sử'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            onPressed: () => context.go('/settings'),
          ),
        ],
      ),
      body: DefaultTabController(
        length: 2,
        child: Column(
          children: [
            TabBar(
              indicatorColor: AppColors.primary,
              labelColor: AppColors.primary,
              unselectedLabelColor: AppColors.textMuted,
              tabs: const [
                Tab(text: 'Lịch sử quét'),
                Tab(text: 'Lịch sử uống thuốc'),
              ],
            ),
            Expanded(
              child: TabBarView(
                children: [
                  RefreshIndicator(
                    onRefresh: () => ref
                        .read(scanHistoryNotifierProvider.notifier)
                        .refresh(),
                    child: scanAsync.when(
                      loading: () =>
                          const Center(child: CircularProgressIndicator()),
                      error: (e, _) => _ErrorState(
                        message: 'Khong tai duoc lich su quet\n$e',
                      ),
                      data: (page) {
                        if (page.items.isEmpty) {
                          return const _EmptyState(
                            message: 'Chua co lich su quet',
                          );
                        }
                        final df = DateFormat('dd/MM/yyyy HH:mm');
                        return ListView.separated(
                          padding: const EdgeInsets.all(16),
                          itemCount: page.items.length,
                          separatorBuilder: (context, index) =>
                              const SizedBox(height: 8),
                          itemBuilder: (context, index) {
                            final item = page.items[index];
                            return ListTile(
                              tileColor: AppColors.surface,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                              onTap: () =>
                                  context.go('/history/scan/${item.id}'),
                              title: Text('Scan #${item.id.substring(0, 8)}'),
                              subtitle: Text(
                                df.format(item.scannedAt.toLocal()),
                              ),
                              trailing: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                crossAxisAlignment: CrossAxisAlignment.end,
                                children: [
                                  Text('${item.drugCount} thuoc'),
                                  Text(
                                    item.qualityState,
                                    style: const TextStyle(fontSize: 12),
                                  ),
                                ],
                              ),
                            );
                          },
                        );
                      },
                    ),
                  ),
                  RefreshIndicator(
                    onRefresh: () => ref
                        .read(medicationLogsNotifierProvider.notifier)
                        .refresh(),
                    child: logAsync.when(
                      loading: () =>
                          const Center(child: CircularProgressIndicator()),
                      error: (e, _) => _ErrorState(
                        message: 'Khong tai duoc lich su uong thuoc\n$e',
                      ),
                      data: (page) {
                        if (page.items.isEmpty) {
                          return const _EmptyState(
                            message: 'Chua co lich su uong thuoc',
                          );
                        }
                        final df = DateFormat('dd/MM/yyyy HH:mm');
                        return ListView.separated(
                          padding: const EdgeInsets.all(16),
                          itemCount: page.items.length,
                          separatorBuilder: (context, index) =>
                              const SizedBox(height: 8),
                          itemBuilder: (context, index) {
                            final log = page.items[index];
                            return ListTile(
                              tileColor: AppColors.surface,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                              leading: Icon(
                                _statusIcon(log.status),
                                color: _statusColor(log.status),
                              ),
                              title: Text(log.drugName ?? 'Khong ro ten thuoc'),
                              subtitle: Text(
                                df.format(log.scheduledTime.toLocal()),
                              ),
                              trailing: Text(
                                _statusLabel(log.status),
                                style: TextStyle(
                                  color: _statusColor(log.status),
                                ),
                              ),
                            );
                          },
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  static String _statusLabel(String status) {
    switch (status) {
      case 'taken':
        return 'Da uong';
      case 'skipped':
        return 'Bo qua';
      case 'missed':
        return 'Nho';
      default:
        return 'Cho';
    }
  }

  static Color _statusColor(String status) {
    switch (status) {
      case 'taken':
        return AppColors.success;
      case 'skipped':
        return AppColors.warning;
      case 'missed':
        return AppColors.error;
      default:
        return AppColors.textMuted;
    }
  }

  static IconData _statusIcon(String status) {
    switch (status) {
      case 'taken':
        return Icons.check_circle;
      case 'skipped':
        return Icons.remove_circle;
      case 'missed':
        return Icons.error;
      default:
        return Icons.schedule;
    }
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        SizedBox(
          height: MediaQuery.of(context).size.height * 0.5,
          child: Center(
            child: Text(
              message,
              style: const TextStyle(color: AppColors.textMuted),
            ),
          ),
        ),
      ],
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        SizedBox(
          height: MediaQuery.of(context).size.height * 0.5,
          child: Center(
            child: Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(color: AppColors.error),
            ),
          ),
        ),
      ],
    );
  }
}
