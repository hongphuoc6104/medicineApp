import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:medicine_app/l10n/app_localizations.dart';

import '../../../core/theme/app_theme.dart';

/// Tab 2: Create Plan — choose between scan and manual.
class CreatePlanScreen extends StatelessWidget {
  const CreatePlanScreen({super.key});

  void _handleBack(BuildContext context) {
    if (Navigator.of(context).canPop()) {
      Navigator.of(context).pop();
      return;
    }

    final location = GoRouterState.of(context).matchedLocation;
    if (location.startsWith('/plans/')) {
      context.go('/plans');
      return;
    }
    context.go('/home');
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.createPlanTitle),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => _handleBack(context),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SizedBox(height: 12),
            Text(
              l10n.createPlanStartTitle,
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              l10n.createPlanStartSubtitle,
              style: const TextStyle(color: AppColors.textSecondary),
            ),
            const SizedBox(height: 12),
            const _CreatePlanNote(),
            const SizedBox(height: 20),
            _OptionCard(
              icon: Icons.document_scanner_outlined,
              title: l10n.createPlanScanTitle,
              subtitle: l10n.createPlanScanSubtitle,
              color: AppColors.primary,
              onTap: () => context.go('/create/scan'),
            ),
            const SizedBox(height: 16),
            _OptionCard(
              icon: Icons.edit_note,
              title: l10n.createPlanManualTitle,
              subtitle: l10n.createPlanManualSubtitle,
              color: AppColors.info,
              onTap: () => context.go('/create/edit'),
            ),
            const SizedBox(height: 16),
            _OptionCard(
              icon: Icons.history_toggle_off,
              title: l10n.createPlanHistoryTitle,
              subtitle: l10n.createPlanHistorySubtitle,
              color: AppColors.success,
              onTap: () => context.go('/create/reuse'),
            ),
            const SizedBox(height: 12),
          ],
        ),
      ),
    );
  }
}

class _CreatePlanNote extends StatelessWidget {
  const _CreatePlanNote();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surfaceSoft,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: const Text(
        'Chọn 1 cách bắt đầu. Mọi cách đều đi vào cùng một luồng tạo kế hoạch.',
        style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
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
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: 13,
                      color: AppColors.textSecondary,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
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
