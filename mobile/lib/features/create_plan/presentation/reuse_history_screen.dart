import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../core/theme/app_theme.dart';
import '../../history/data/scan_history_notifier.dart';

/// Screen: Dùng lại đơn thuốc đã quét trước đây.
///
/// Hiển thị danh sách các lần quét cũ (mới nhất trước).
/// Tap vào → sang ScanHistoryDetailScreen với mode=reuse để user xác nhận
/// và tiến vào review/schedule flow.
class ReuseHistoryScreen extends ConsumerWidget {
  const ReuseHistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scanAsync = ref.watch(scanHistoryNotifierProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dùng lại đơn đã quét'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/create'),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: () =>
            ref.read(scanHistoryNotifierProvider.notifier).refresh(),
        child: scanAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => _ErrorState(
            onRetry: () =>
                ref.read(scanHistoryNotifierProvider.notifier).refresh(),
          ),
          data: (page) {
            if (page.items.isEmpty) {
              return _EmptyState(
                onScanNow: () => context.go('/create/scan'),
              );
            }

            final df = DateFormat('dd/MM/yyyy HH:mm');
            return ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: page.items.length,
              separatorBuilder: (_, i) => const SizedBox(height: 10),
              itemBuilder: (context, index) {
                final item = page.items[index];
                return _ReuseCard(
                  drugCount: item.drugCount,
                  scannedAt: df.format(item.scannedAt.toLocal()),
                  qualityState: item.qualityState,
                  canReuse: item.drugCount > 0,
                  onTap: () =>
                      context.go('/history/scan/${item.id}?mode=reuse'),
                );
              },
            );
          },
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Reuse card — 1 lần quét trong danh sách
// ---------------------------------------------------------------------------

class _ReuseCard extends StatelessWidget {
  const _ReuseCard({
    required this.drugCount,
    required this.scannedAt,
    required this.qualityState,
    required this.canReuse,
    required this.onTap,
  });

  final int drugCount;
  final String scannedAt;
  final String qualityState;
  final bool canReuse;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final (qLabel, qColor) = _qualityInfo(qualityState);
    final accent = canReuse ? AppColors.success : AppColors.textMuted;

    return InkWell(
      onTap: canReuse ? onTap : null,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: canReuse
                ? AppColors.success.withValues(alpha: 0.35)
                : AppColors.border,
          ),
        ),
        child: Row(
          children: [
            // Icon
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.12),
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.history_rounded,
                color: accent,
                size: 22,
              ),
            ),
            const SizedBox(width: 14),

            // Info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    drugCount > 0
                        ? '$drugCount thuốc'
                        : 'Không nhận diện được thuốc',
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 14,
                      color: canReuse
                          ? AppColors.textPrimary
                          : AppColors.textMuted,
                    ),
                  ),
                  const SizedBox(height: 3),
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

            // Quality badge + action hint
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
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
                Icon(
                  canReuse ? Icons.chevron_right : Icons.block_outlined,
                  color: canReuse ? AppColors.textMuted : AppColors.textMuted,
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
// Empty state
// ---------------------------------------------------------------------------

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.onScanNow});

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
                    Icons.history_outlined,
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
                    'Quét đơn thuốc lần đầu để lưu và dùng lại sau.',
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
// Error state
// ---------------------------------------------------------------------------

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.onRetry});

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
