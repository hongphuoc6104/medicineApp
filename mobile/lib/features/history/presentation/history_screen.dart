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
                Tab(text: 'Đơn thuốc đã quét'),
                Tab(text: 'Lịch sử uống thuốc'),
              ],
            ),
            Expanded(
              child: TabBarView(
                children: [
                  // -------------------------------------------------------
                  // Tab 1: Scan history
                  // -------------------------------------------------------
                  RefreshIndicator(
                    onRefresh: () => ref
                        .read(scanHistoryNotifierProvider.notifier)
                        .refresh(),
                    child: scanAsync.when(
                      loading: () =>
                          const Center(child: CircularProgressIndicator()),
                      error: (e, _) => _ScanErrorState(
                        onRetry: () => ref
                            .read(scanHistoryNotifierProvider.notifier)
                            .refresh(),
                      ),
                      data: (page) {
                        if (page.items.isEmpty) {
                          return _ScanEmptyState(
                            onScanNow: () => context.go('/create/scan'),
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
                            return _ScanHistoryCard(
                              drugCount: item.drugCount,
                              scannedAt: df.format(item.scannedAt.toLocal()),
                              qualityState: item.qualityState,
                              onTap: () =>
                                  context.go('/history/scan/${item.id}'),
                            );
                          },
                        );
                      },
                    ),
                  ),

                  // -------------------------------------------------------
                  // Tab 2: Medication logs
                  // -------------------------------------------------------
                  RefreshIndicator(
                    onRefresh: () => ref
                        .read(medicationLogsNotifierProvider.notifier)
                        .refresh(),
                    child: logAsync.when(
                      loading: () =>
                          const Center(child: CircularProgressIndicator()),
                      error: (e, _) => _ErrorState(
                        message: 'Không tải được lịch sử uống thuốc.\nKéo xuống để thử lại.',
                      ),
                      data: (page) {
                        if (page.items.isEmpty) {
                          return const _EmptyState(
                            icon: Icons.medication_outlined,
                            message: 'Chưa có lịch sử uống thuốc.',
                            hint: 'Dữ liệu sẽ xuất hiện khi bạn bắt đầu theo dõi kế hoạch.',
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
                              title: Text(log.drugName ?? 'Không rõ tên thuốc'),
                              subtitle: Text(
                                df.format(log.scheduledTime.toLocal()),
                              ),
                              trailing: Text(
                                _statusLabel(log.status),
                                style: TextStyle(
                                  color: _statusColor(log.status),
                                  fontWeight: FontWeight.w600,
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
        return 'Đã uống';
      case 'skipped':
        return 'Bỏ qua';
      case 'missed':
        return 'Nhỡ';
      default:
        return 'Chờ';
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

// ---------------------------------------------------------------------------
// Scan history card — hiển thị 1 lần quét trong danh sách
// ---------------------------------------------------------------------------

class _ScanHistoryCard extends StatelessWidget {
  const _ScanHistoryCard({
    required this.drugCount,
    required this.scannedAt,
    required this.qualityState,
    required this.onTap,
  });

  final int drugCount;
  final String scannedAt;
  final String qualityState;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final (qLabel, qColor) = _qualityInfo(qualityState);

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            // Icon
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.document_scanner_outlined,
                color: AppColors.primary,
                size: 22,
              ),
            ),
            const SizedBox(width: 14),

            // Main info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    drugCount > 0
                        ? '$drugCount thuốc được nhận diện'
                        : 'Không nhận diện được thuốc',
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 14,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    scannedAt,
                    style: const TextStyle(
                      color: AppColors.textMuted,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),

            // Quality badge + chevron
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: qColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    qLabel,
                    style: TextStyle(
                      color: qColor,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                const SizedBox(height: 6),
                const Icon(
                  Icons.chevron_right,
                  color: AppColors.textMuted,
                  size: 18,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  static (String, Color) _qualityInfo(String state) {
    switch (state) {
      case 'GOOD':
        return ('Ảnh tốt', AppColors.success);
      case 'WARNING':
        return ('Ảnh mờ', AppColors.warning);
      case 'REJECT':
        return ('Ảnh kém', AppColors.error);
      default:
        return ('Đã quét', AppColors.textMuted);
    }
  }
}

// ---------------------------------------------------------------------------
// Scan tab — empty state
// ---------------------------------------------------------------------------

class _ScanEmptyState extends StatelessWidget {
  const _ScanEmptyState({required this.onScanNow});

  final VoidCallback onScanNow;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        SizedBox(
          height: MediaQuery.of(context).size.height * 0.55,
          child: Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 40),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.document_scanner_outlined,
                    size: 56,
                    color: AppColors.textMuted,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Chưa có đơn thuốc nào được quét',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 16,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Quét đơn thuốc để lưu kết quả vào đây và dùng lại sau.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: AppColors.textMuted),
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton.icon(
                    onPressed: onScanNow,
                    icon: const Icon(Icons.camera_alt_outlined),
                    label: const Text('Quét đơn thuốc ngay'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Scan tab — error state
// ---------------------------------------------------------------------------

class _ScanErrorState extends StatelessWidget {
  const _ScanErrorState({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        SizedBox(
          height: MediaQuery.of(context).size.height * 0.5,
          child: Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 40),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.wifi_off_outlined,
                    size: 48,
                    color: AppColors.textMuted,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Không tải được lịch sử quét',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Kiểm tra kết nối và thử lại.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: AppColors.textMuted),
                  ),
                  const SizedBox(height: 20),
                  OutlinedButton.icon(
                    onPressed: onRetry,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Thử lại'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Generic empty state (dùng cho tab medication logs)
// ---------------------------------------------------------------------------

class _EmptyState extends StatelessWidget {
  const _EmptyState({
    required this.icon,
    required this.message,
    this.hint,
  });

  final IconData icon;
  final String message;
  final String? hint;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        SizedBox(
          height: MediaQuery.of(context).size.height * 0.5,
          child: Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 40),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(icon, size: 48, color: AppColors.textMuted),
                  const SizedBox(height: 16),
                  Text(
                    message,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 15,
                    ),
                  ),
                  if (hint != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      hint!,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: AppColors.textMuted),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Generic error state (dùng cho tab medication logs)
// ---------------------------------------------------------------------------

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
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 40),
              child: Text(
                message,
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppColors.error),
              ),
            ),
          ),
        ),
      ],
    );
  }
}
