import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';

/// Tab 2: Create Plan — choose between scan and manual.
class CreatePlanScreen extends StatelessWidget {
  const CreatePlanScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Tạo kế hoạch')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SizedBox(height: 32),
            Text(
              'Chọn cách bắt đầu tạo kế hoạch',
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              'Ứng dụng hỗ trợ trích xuất tên thuốc. Bạn kiểm tra lại danh sách trước khi lưu kế hoạch.',
              style: TextStyle(color: AppColors.textSecondary),
            ),
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.surfaceSoft,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.border),
              ),
              child: const Text(
                'Lưu ý: Kết quả quét là bước gợi ý ban đầu, không thay thế hoàn toàn việc kiểm tra toa thuốc.',
                style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
              ),
            ),
            const SizedBox(height: 24),

            // ── Option 1: Scan ──
            _OptionCard(
              icon: Icons.document_scanner_outlined,
              title: 'Quét đơn thuốc',
              subtitle:
                  'Chụp hoặc tải ảnh đơn thuốc,\nứng dụng trích xuất tên thuốc để bạn kiểm tra lại',
              color: AppColors.primary,
              onTap: () => context.go('/create/scan'),
            ),
            const SizedBox(height: 16),

            // ── Option 2: Manual ──
            _OptionCard(
              icon: Icons.edit_note,
              title: 'Nhập thủ công',
              subtitle:
                  'Tự nhập danh sách thuốc\nkhi không dùng ảnh quét hoặc cần nhập mới hoàn toàn',
              color: AppColors.info,
              onTap: () => context.go('/create/edit'),
            ),
            const SizedBox(height: 16),
            _OptionCard(
              icon: Icons.history_toggle_off,
              title: 'Dùng lại từ lịch sử',
              subtitle:
                  'Dùng lại kết quả đã quét trước đó\nđể tạo kế hoạch mới nhanh hơn',
              color: AppColors.success,
              onTap: () => context.go('/history'),
            ),
          ],
        ),
      ),
    );
  }
}

class _OptionCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Color color;
  final VoidCallback onTap;

  const _OptionCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: color.withValues(alpha: 0.3)),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, size: 28, color: color),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: 13,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
            Icon(Icons.chevron_right, color: AppColors.textMuted),
          ],
        ),
      ),
    );
  }
}
