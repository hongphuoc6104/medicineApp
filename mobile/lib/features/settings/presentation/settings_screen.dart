import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../../auth/data/auth_notifier.dart';
import '../../home/data/plan_notifier.dart';
import '../../home/data/today_schedule_notifier.dart';
import '../data/settings_notifier.dart';
import '../../../core/notifications/notification_service.dart';

Future<void> _logoutCleanup(WidgetRef ref) async {
  await ref.read(notificationServiceProvider).cancelAllNotifications();
  await ref.read(planNotifierProvider.notifier).clearForCurrentUser();
  await ref.read(todayScheduleNotifierProvider.notifier).clearForCurrentUser();
}

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  Future<void> _showScheduledRemindersReport(
    BuildContext context,
    WidgetRef ref,
  ) async {
    final notificationService = ref.read(notificationServiceProvider);
    await ref
        .read(planNotifierProvider.notifier)
        .ensureNotificationsSynced(
          force: true,
          reason: 'settings_report_force',
        );
    final report = await notificationService.buildScheduledRemindersReport();
    if (!context.mounted) {
      return;
    }

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Báo cáo lịch nhắc trên thiết bị'),
          content: SizedBox(
            width: double.maxFinite,
            child: SingleChildScrollView(
              child: SelectableText(
                report,
                style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Đóng'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _showMiuiChecklist(BuildContext context) async {
    if (!context.mounted) {
      return;
    }

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Checklist MIUI / Android'),
          content: const SingleChildScrollView(
            child: SelectableText(
              '1) Cài đặt > Ứng dụng > Uống thuốc > Tự khởi động: BẬT.\n\n'
              '2) Cài đặt > Pin > Tiết kiệm pin ứng dụng > Uống thuốc: '
              'Không hạn chế.\n\n'
              '3) Cài đặt > Thông báo > Uống thuốc:\n'
              '   - Cho phép thông báo\n'
              '   - Hiển thị trên màn hình khóa\n'
              '   - Pop-up banner\n'
              '   - Âm thanh + rung\n\n'
              '4) Mở Recent Apps và khóa app Uống thuốc (kéo xuống biểu tượng khóa).\n\n'
              '5) Sau khi đổi cài đặt hệ thống, vào app bấm "Đồng bộ ngay" '
              'rồi kiểm tra lại bằng chuỗi nhắc theo giây/phút.',
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Đã hiểu'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settingsAsync = ref.watch(settingsNotifierProvider);
    final settingsState = settingsAsync.asData?.value ?? const SettingsState();

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/home'),
        ),
        title: const Text('Cài đặt'),
      ),
      body: ListView(
        children: [
          _buildSection('Tài khoản', [
            ListTile(
              leading: const Icon(Icons.person_outline),
              title: const Text('Hồ sơ'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () {},
            ),
          ]),
          _buildSection('Thông báo', [
            SwitchListTile(
              secondary: const Icon(Icons.notifications_outlined),
              title: const Text('Nhắc uống thuốc'),
              subtitle: const Text('Tắt sẽ hủy nhắc trên thiết bị này'),
              value: settingsState.remindersEnabled,
              thumbColor: WidgetStateProperty.all(AppColors.primary),
              onChanged: settingsAsync.isLoading
                  ? null
                  : (v) async {
                      final success = await ref
                          .read(settingsNotifierProvider.notifier)
                          .setRemindersEnabled(v);
                      if (!context.mounted) return;
                      final message = success
                          ? (v
                                ? 'Đã bật nhắc uống thuốc trên thiết bị này'
                                : 'Đã tắt nhắc uống thuốc trên thiết bị này')
                          : (v
                                ? 'Chưa thể bật nhắc uống thuốc vì chưa có quyền thông báo'
                                : 'Không thể cập nhật cài đặt nhắc uống thuốc');
                      ScaffoldMessenger.of(
                        context,
                      ).showSnackBar(SnackBar(content: Text(message)));
                    },
            ),
            ListTile(
              leading: const Icon(Icons.sync_outlined),
              title: const Text('Đồng bộ ngay'),
              subtitle: const Text(
                'Tải lại kế hoạch hôm nay và đồng bộ log offline',
              ),
              trailing: const Icon(Icons.chevron_right),
              onTap: () async {
                await ref.read(planNotifierProvider.notifier).refresh();
                await ref
                    .read(planNotifierProvider.notifier)
                    .ensureNotificationsSynced(
                      force: true,
                      reason: 'settings_manual_sync',
                    );
                await ref
                    .read(todayScheduleNotifierProvider.notifier)
                    .refresh();
                if (!context.mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Đã đồng bộ dữ liệu hiện tại')),
                );
              },
            ),
            ListTile(
              leading: const Icon(Icons.notification_add_outlined),
              title: const Text('Gửi chuỗi nhắc uống thuốc (5 lần)'),
              subtitle: const Text(
                'Gửi chuỗi nhắc: trước giờ, đúng giờ, trễ 15/30/45 phút',
              ),
              trailing: const Icon(Icons.chevron_right),
              onTap: () async {
                await ref
                    .read(notificationServiceProvider)
                    .sendDebugNotificationsBurst();
                if (!context.mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text(
                      'Đã lên lịch chuỗi 5 lần nhắc uống thuốc (trong ~10-75 giây).',
                    ),
                  ),
                );
              },
            ),
            ListTile(
              leading: const Icon(Icons.timer_outlined),
              title: const Text('Gửi chuỗi nhắc theo phút (5 lần)'),
              subtitle: const Text(
                'Lên lịch trong 1-5 phút để test gần thực tế',
              ),
              trailing: const Icon(Icons.chevron_right),
              onTap: () async {
                await ref
                    .read(notificationServiceProvider)
                    .sendDebugNotificationsMinuteScale();
                if (!context.mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text(
                      'Đã lên lịch chuỗi theo phút (1-5 phút tới).',
                    ),
                  ),
                );
              },
            ),
            ListTile(
              leading: const Icon(Icons.notifications_active_outlined),
              title: const Text('Hiện thông báo ngay (màn hình khóa)'),
              subtitle: const Text(
                'Gửi ngay 1 nhắc để kiểm tra lockscreen tức thì',
              ),
              trailing: const Icon(Icons.chevron_right),
              onTap: () async {
                await ref
                    .read(notificationServiceProvider)
                    .showImmediateLockscreenTest();
                if (!context.mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text(
                      'Đã gửi thông báo test tức thì. Hãy tắt màn hình để kiểm tra.',
                    ),
                  ),
                );
              },
            ),
            ListTile(
              leading: const Icon(Icons.receipt_long_outlined),
              title: const Text('Xem báo cáo lịch nhắc đã lên'),
              subtitle: const Text(
                'Kiểm tra danh sách reminder đang chờ trên thiết bị',
              ),
              trailing: const Icon(Icons.chevron_right),
              onTap: () async {
                await _showScheduledRemindersReport(context, ref);
              },
            ),
            ListTile(
              leading: const Icon(Icons.battery_saver_outlined),
              title: const Text('Checklist MIUI / Pin nền'),
              subtitle: const Text(
                'Mở hướng dẫn Autostart, No restrictions, lockscreen',
              ),
              trailing: const Icon(Icons.chevron_right),
              onTap: () async {
                await _showMiuiChecklist(context);
              },
            ),
          ]),
          _buildSection('Ứng dụng', [
            ListTile(
              leading: const Icon(Icons.info_outline),
              title: const Text('Phiên bản ứng dụng'),
              trailing: Text(
                '1.0.0',
                style: TextStyle(color: AppColors.textMuted),
              ),
            ),
          ]),
          const SizedBox(height: 24),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: OutlinedButton.icon(
              onPressed: () async {
                await _logoutCleanup(ref);
                await ref.read(authNotifierProvider.notifier).logout();
              },
              icon: const Icon(Icons.logout, color: AppColors.error),
              label: const Text(
                'Đăng xuất',
                style: TextStyle(color: AppColors.error),
              ),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppColors.error),
                minimumSize: const Size(double.infinity, 48),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSection(String title, List<Widget> children) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 24, 16, 8),
          child: Text(
            title,
            style: const TextStyle(
              color: AppColors.textMuted,
              fontSize: 12,
              fontWeight: FontWeight.w600,
              letterSpacing: 1.2,
            ),
          ),
        ),
        ...children,
        const Divider(height: 1),
      ],
    );
  }
}
