import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../../auth/data/auth_notifier.dart';
import '../../home/data/plan_notifier.dart';
import '../../home/data/today_schedule_notifier.dart';
import '../data/settings_notifier.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

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
                      await ref
                          .read(settingsNotifierProvider.notifier)
                          .setRemindersEnabled(v);
                      if (!context.mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            v
                                ? 'Đã bật nhắc uống thuốc trên thiết bị này'
                                : 'Đã tắt nhắc uống thuốc trên thiết bị này',
                          ),
                        ),
                      );
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
                    .read(todayScheduleNotifierProvider.notifier)
                    .refresh();
                if (!context.mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Đã đồng bộ dữ liệu hiện tại')),
                );
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
