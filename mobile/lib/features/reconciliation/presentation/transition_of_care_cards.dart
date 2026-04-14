import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../domain/reconciliation_result.dart';

class TransitionOfCareWidget extends StatelessWidget {
  const TransitionOfCareWidget({super.key, required this.transitionOfCare});

  final TransitionOfCare transitionOfCare;

  @override
  Widget build(BuildContext context) {
    if (transitionOfCare.riskCards.isEmpty && transitionOfCare.check.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.surfaceHigh),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Text(
              'Chú ý thay đổi',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: AppColors.error,
              ),
            ),
          ),
          if (transitionOfCare.riskCards.isNotEmpty)
            ...transitionOfCare.riskCards.map((card) => _RiskCardItem(card: card)),
          if (transitionOfCare.check.isNotEmpty) ...[
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: transitionOfCare.check
                    .map((val) => _ChecklistItem(text: val))
                    .toList(),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _RiskCardItem extends StatelessWidget {
  final RiskCard card;

  const _RiskCardItem({required this.card});

  @override
  Widget build(BuildContext context) {
    final color = card.level == 'warning' ? AppColors.warning : AppColors.info;
    final icon = card.level == 'warning' ? Icons.warning_amber_rounded : Icons.info_outline;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  card.label,
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: color,
                  ),
                ),
                Text(
                  card.detail,
                  style: const TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ChecklistItem extends StatelessWidget {
  final String text;

  const _ChecklistItem({required this.text});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 4, right: 8),
            child: Icon(Icons.check_circle_outline, size: 16, color: AppColors.primary),
          ),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(fontSize: 13, color: AppColors.textPrimary),
            ),
          ),
        ],
      ),
    );
  }
}
