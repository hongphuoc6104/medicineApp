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
              'Chọn cách tạo kế hoạch',
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              'Quét đơn thuốc hoặc nhập thủ công',
              style: TextStyle(color: AppColors.textSecondary),
            ),
            const SizedBox(height: 32),

            // ── Option 1: Scan ──
            _OptionCard(
              icon: Icons.document_scanner_outlined,
              title: 'Quét đơn thuốc',
              subtitle:
                  'Dùng camera quét đơn thuốc,\nAI sẽ nhận diện tên thuốc tự động',
              color: AppColors.primary,
              onTap: () => context.go('/create/scan'),
            ),
            const SizedBox(height: 16),

            // ── Option 2: Manual ──
            _OptionCard(
              icon: Icons.edit_note,
              title: 'Nhập thủ công',
              subtitle:
                  'Tìm kiếm và thêm thuốc\ntừ cơ sở dữ liệu 9,284 thuốc VN',
              color: AppColors.info,
              onTap: () => context.go('/create/edit'),
            ),
            const SizedBox(height: 16),
            _OptionCard(
              icon: Icons.history_toggle_off,
              title: 'Dùng lại từ lịch sử',
              subtitle:
                  'Mở lịch sử quét và tạo lại kế hoạch\ntừ kết quả đã có trước đó',
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
