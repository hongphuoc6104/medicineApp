import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import 'package:medicine_app/l10n/app_localizations.dart';

import '../../../core/network/network_error_mapper.dart';
import '../../../core/theme/app_theme.dart';
import '../../create_plan/data/offline_dose_queue.dart';
import '../../create_plan/domain/plan.dart';
import '../data/plan_notifier.dart';
import '../data/today_schedule_notifier.dart';
import '../domain/today_schedule.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final plansAsync = ref.watch(planNotifierProvider);
    final todayAsync = ref.watch(todayScheduleNotifierProvider);

    ref.listen<AsyncValue<TodaySchedule>>(todayScheduleNotifierProvider, (
      previous,
      next,
    ) async {
      if (next.hasValue) {
        final synced = await ref
            .read(todayScheduleNotifierProvider.notifier)
            .flushOfflineQueue();
        if (synced > 0 && context.mounted) {
          final l10n = AppLocalizations.of(context);
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(l10n.homeSyncSuccess(synced)),
              backgroundColor: AppColors.success,
            ),
          );
        }
      }
    });

    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.appTitle),
        actions: [
          IconButton(
            onPressed: () => context.push('/settings'),
            icon: const Icon(Icons.settings_outlined),
          ),
          const SizedBox(width: 6),
        ],
      ),
      body: plansAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => _ErrorView(
          message: toFriendlyNetworkMessage(
            e,
            genericMessage: 'Không tải được dữ liệu hôm nay. Vui lòng thử lại.',
          ),
          onRetry: () => ref.read(planNotifierProvider.notifier).refresh(),
        ),
        data: (state) {
          return RefreshIndicator(
            onRefresh: () async {
              await ref.read(planNotifierProvider.notifier).refresh();
              await ref.read(todayScheduleNotifierProvider.notifier).refresh();
            },
            child: state.hasPlans
                ? _DashboardView(plans: state.plans, todayAsync: todayAsync)
                : const _OnboardingView(),
          );
        },
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        const SizedBox(height: 120),
        Icon(Icons.cloud_off_rounded, size: 54, color: AppColors.textMuted),
        const SizedBox(height: 18),
        Text(
          'Không tải được dữ liệu hôm nay',
          textAlign: TextAlign.center,
          style: Theme.of(
            context,
          ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 8),
        Text(
          message,
          textAlign: TextAlign.center,
          style: const TextStyle(color: AppColors.textSecondary),
        ),
        const SizedBox(height: 18),
        ElevatedButton.icon(
          onPressed: onRetry,
          icon: const Icon(Icons.refresh),
          label: Text(AppLocalizations.of(context).commonRetry),
        ),
      ],
    );
  }
}

class _OnboardingView extends StatelessWidget {
  const _OnboardingView();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 120),
      children: [
        const _DateHeader(),
        const SizedBox(height: 18),
        Container(
          padding: const EdgeInsets.all(22),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFFEBFBFB), Color(0xFFF9FFFE)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(28),
            border: Border.all(color: AppColors.border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 54,
                height: 54,
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.18),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Icon(
                  Icons.medication_liquid_rounded,
                  color: AppColors.primaryDark,
                  size: 28,
                ),
              ),
              const SizedBox(height: 18),
              Text(
                AppLocalizations.of(context).homeOnboardingTitle,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                AppLocalizations.of(context).homeOnboardingSubtitle,
                style: const TextStyle(
                  color: AppColors.textSecondary,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: 18),
              ElevatedButton.icon(
                onPressed: () => context.go('/create/scan'),
                icon: const Icon(Icons.document_scanner_outlined),
                label: Text(AppLocalizations.of(context).homeActionScan),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => context.go('/create/edit'),
                      icon: const Icon(Icons.edit_note),
                      label: Text(
                        AppLocalizations.of(context).homeActionManual,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => context.go('/create/reuse'),
                      icon: const Icon(Icons.history_outlined),
                      label: Text(
                        AppLocalizations.of(context).homeActionHistory,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        _QuickActionGrid(
          actions: [
            _QuickActionItem(
              title: AppLocalizations.of(context).homeActionDrugLookup,
              subtitle: AppLocalizations.of(
                context,
              ).homeActionDrugLookupSubtitle,
              icon: Icons.search_rounded,
              onTap: () => context.go('/drugs'),
            ),
            _QuickActionItem(
              title: AppLocalizations.of(context).homeActionPlans,
              subtitle: AppLocalizations.of(context).homeActionPlansSubtitle,
              icon: Icons.calendar_month_rounded,
              onTap: () => context.go('/plans'),
            ),
          ],
        ),
      ],
    );
  }
}

class _DashboardView extends ConsumerWidget {
  const _DashboardView({required this.plans, required this.todayAsync});

  final List<Plan> plans;
  final AsyncValue<TodaySchedule> todayAsync;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pendingCountFuture = ref.watch(_pendingCountProvider.future);
    final canMark = !todayAsync.isLoading;

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 130),
      children: [
        const _DateHeader(),
        const SizedBox(height: 12),
        const _WeekStrip(),
        const SizedBox(height: 18),
        FutureBuilder<int>(
          future: pendingCountFuture,
          builder: (context, snapshot) {
            final count = snapshot.data ?? 0;
            if (count <= 0) return const SizedBox.shrink();
            return Container(
              margin: const EdgeInsets.only(bottom: 16),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.warning.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(18),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.sync_problem_outlined,
                    color: AppColors.warning,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      AppLocalizations.of(context).homePendingSync(count),
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ),
                ],
              ),
            );
          },
        ),
        todayAsync.when(
          loading: () => const _TodayLoadingCard(),
          error: (e, _) => _TodayErrorCard(
            message: toFriendlyNetworkMessage(
              e,
              genericMessage:
                  'Không tải được lịch uống thuốc hôm nay. Vui lòng thử lại.',
            ),
            onRetry: () =>
                ref.read(todayScheduleNotifierProvider.notifier).refresh(),
          ),
          data: (today) {
            final now = DateTime.now();
            final sortedDoses = List<TodayDose>.from(today.doses)
              ..sort((a, b) => a.comparePriority(b, now));
            final dueNow = sortedDoses.where((d) => d.isDueNow(now)).toList();
            final upcoming = sortedDoses
                .where((d) => d.isUpcomingSoon(now))
                .toList();
            final laterToday = sortedDoses
                .where(
                  (d) =>
                      d.effectiveStatus(now) == 'pending' &&
                      !d.isDueNow(now) &&
                      !d.isUpcomingSoon(now),
                )
                .toList();

            Widget doseTile(TodayDose dose) => _TodayDoseTile(
              dose: dose,
              canMark: canMark,
              onTaken: () async {
                final result = await ref
                    .read(todayScheduleNotifierProvider.notifier)
                    .markDose(dose: dose, status: 'taken');
                if (!context.mounted) return;
                final l10n = AppLocalizations.of(context);

                if (result == MarkDoseResult.failed) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Lỗi lưu liều uống. Vui lòng thử lại.'),
                      backgroundColor: AppColors.error,
                    ),
                  );
                  return;
                }

                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(
                      result == MarkDoseResult.synced
                          ? l10n.homeDoseTakenStatus(dose.primaryTitle)
                          : l10n.homeDoseOfflineStatus,
                    ),
                    backgroundColor: result == MarkDoseResult.synced ? AppColors.success : AppColors.warning,
                  ),
                );
              },
              onSkipped: () async {
                final result = await ref
                    .read(todayScheduleNotifierProvider.notifier)
                    .markDose(dose: dose, status: 'skipped');
                if (!context.mounted) return;
                final l10n = AppLocalizations.of(context);

                if (result == MarkDoseResult.failed) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Lỗi lưu liều uống. Vui lòng thử lại.'),
                      backgroundColor: AppColors.error,
                    ),
                  );
                  return;
                }

                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(
                      result == MarkDoseResult.synced
                          ? l10n.homeDoseSkippedStatus(dose.primaryTitle)
                          : l10n.homeDoseOfflineStatus,
                    ),
                    backgroundColor: AppColors.warning,
                  ),
                );
              },
            );

            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _HeroTodayCard(today: today),
                const SizedBox(height: 16),
                if (today.doses.isEmpty)
                  const _TodayEmptyCard()
                else ...[
                  if (dueNow.isNotEmpty) ...[
                    _SectionLabel(
                      title: AppLocalizations.of(context).homeSectionDueNow,
                    ),
                    const SizedBox(height: 10),
                    ...dueNow.map(doseTile),
                    const SizedBox(height: 8),
                  ],
                  if (upcoming.isNotEmpty) ...[
                    _SectionLabel(
                      title: AppLocalizations.of(context).homeSectionUpcoming,
                    ),
                    const SizedBox(height: 10),
                    ...upcoming.map(doseTile),
                    const SizedBox(height: 8),
                  ],
                  if (laterToday.isNotEmpty) ...[
                    const _SectionLabel(title: 'Các liều còn lại hôm nay'),
                    const SizedBox(height: 10),
                    ...laterToday.map(doseTile),
                    const SizedBox(height: 8),
                  ],
                  if (dueNow.isEmpty && upcoming.isEmpty && laterToday.isEmpty)
                    const _TodayEmptyCard(),
                ],
                const SizedBox(height: 18),
                _SectionLabel(title: AppLocalizations.of(context).homeInUse),
                const SizedBox(height: 10),
                ...plans.take(3).map((plan) => _PlanCard(plan: plan)),
                if (plans.length > 3) ...[
                  const SizedBox(height: 8),
                  TextButton.icon(
                    onPressed: () => context.go('/plans'),
                    icon: const Icon(Icons.open_in_new),
                    label: Text(
                      AppLocalizations.of(
                        context,
                      ).homeViewAllPlans(plans.length),
                    ),
                  ),
                ],
              ],
            );
          },
        ),
      ],
    );
  }
}

final _pendingCountProvider = FutureProvider<int>((ref) async {
  return ref.read(offlineDoseQueueProvider).pendingCount();
});

class _DateHeader extends StatelessWidget {
  const _DateHeader();

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final dateLabel = DateFormat('d MMMM, yyyy').format(now);
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                AppLocalizations.of(context).homeTitleToday,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                dateLabel,
                style: const TextStyle(color: AppColors.textSecondary),
              ),
            ],
          ),
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: AppColors.border),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.calendar_today_rounded,
                size: 16,
                color: AppColors.primaryDark,
              ),
              const SizedBox(width: 6),
              Text(AppLocalizations.of(context).homeTodayDrugs),
            ],
          ),
        ),
      ],
    );
  }
}

class _WeekStrip extends StatelessWidget {
  const _WeekStrip();

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final monday = now.subtract(Duration(days: now.weekday - 1));
    final days = List.generate(7, (index) => monday.add(Duration(days: index)));
    final labels = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: List.generate(days.length, (index) {
          final day = days[index];
          final selected =
              day.year == now.year &&
              day.month == now.month &&
              day.day == now.day;
          return Column(
            children: [
              Text(
                labels[index],
                style: const TextStyle(
                  fontSize: 11,
                  color: AppColors.textMuted,
                ),
              ),
              const SizedBox(height: 8),
              AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                width: 36,
                height: 36,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: selected ? AppColors.primary : AppColors.surfaceSoft,
                  borderRadius: BorderRadius.circular(18),
                ),
                child: Text(
                  '${day.day}',
                  style: TextStyle(
                    color: selected ? Colors.white : AppColors.textPrimary,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          );
        }),
      ),
    );
  }
}

class _HeroTodayCard extends StatelessWidget {
  const _HeroTodayCard({required this.today});

  final TodaySchedule today;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF58D5D4), Color(0xFF85E6E2)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(30),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            AppLocalizations.of(context).homeHeroTitle,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 14,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            AppLocalizations.of(
              context,
            ).homeHeroTotalDoses(today.summary.total),
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 18),
          Row(
            children: [
              _HeroMetric(
                label: AppLocalizations.of(context).homeHeroTaken,
                value: '${today.summary.taken}',
              ),
              _HeroMetric(
                label: AppLocalizations.of(context).homeHeroPending,
                value: '${today.summary.pending}',
              ),
              _HeroMetric(
                label: AppLocalizations.of(context).homeHeroSkipped,
                value: '${today.summary.skipped}',
              ),
              _HeroMetric(
                label: AppLocalizations.of(context).homeHeroMissed,
                value: '${today.summary.missed}',
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HeroMetric extends StatelessWidget {
  const _HeroMetric({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        children: [
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 22,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: const TextStyle(color: Colors.white70, fontSize: 11),
          ),
        ],
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return Text(
      title,
      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
    );
  }
}

class _QuickActionGrid extends StatelessWidget {
  const _QuickActionGrid({required this.actions});

  final List<_QuickActionItem> actions;

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: actions.length,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        childAspectRatio: 1.05,
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
      ),
      itemBuilder: (context, index) {
        final item = actions[index];
        return InkWell(
          onTap: item.onTap,
          borderRadius: BorderRadius.circular(24),
          child: Ink(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: AppColors.primary.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(item.icon, color: AppColors.primaryDark),
                ),
                const Spacer(),
                Text(
                  item.title,
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 4),
                Text(
                  item.subtitle,
                  style: const TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _QuickActionItem {
  _QuickActionItem({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback onTap;
}

class _PlanCard extends StatelessWidget {
  const _PlanCard({required this.plan});

  final Plan plan;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () => context.go('/plans/${plan.id}'),
      borderRadius: BorderRadius.circular(24),
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: AppColors.border),
        ),
        child: Row(
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                color: AppColors.surfaceSoft,
                borderRadius: BorderRadius.circular(18),
              ),
              child: const Icon(
                Icons.medication_rounded,
                color: AppColors.primaryDark,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    plan.drugName,
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 15,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    plan.hasVariableDoseSchedule
                        ? '${_freqLabel(context, plan.frequency)} · ${AppLocalizations.of(context).homeFreqHourly} · ${plan.times.join(', ')}'
                        : '${_freqLabel(context, plan.frequency)} · ${plan.pillsPerDose} viên · ${plan.times.join(', ')}',
                    style: const TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                AppLocalizations.of(context).homePlanActive,
                style: const TextStyle(
                  color: AppColors.primaryDark,
                  fontWeight: FontWeight.w800,
                  fontSize: 11,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  static String _freqLabel(BuildContext context, String freq) {
    switch (freq) {
      case 'twice_daily':
        return AppLocalizations.of(context).homeFreqDaily2;
      case 'three_daily':
        return AppLocalizations.of(context).homeFreqDaily3;
      case 'weekly':
        return AppLocalizations.of(context).homeFreqWeekly;
      default:
        return AppLocalizations.of(context).homeFreqDaily1;
    }
  }
}

class _TodayLoadingCard extends StatelessWidget {
  const _TodayLoadingCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          const SizedBox(
            width: 22,
            height: 22,
            child: CircularProgressIndicator(strokeWidth: 2.4),
          ),
          const SizedBox(width: 14),
          Expanded(child: Text(AppLocalizations.of(context).homeLoadingToday)),
        ],
      ),
    );
  }
}

class _TodayErrorCard extends StatelessWidget {
  const _TodayErrorCard({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            AppLocalizations.of(context).homeErrorLoadSchedule,
            style: const TextStyle(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          Text(message, style: const TextStyle(color: AppColors.textSecondary)),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh),
            label: Text(AppLocalizations.of(context).commonRetry),
          ),
        ],
      ),
    );
  }
}

class _TodayEmptyCard extends StatelessWidget {
  const _TodayEmptyCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppColors.border),
      ),
      child: const Column(
        children: [
          Icon(
            Icons.event_available_rounded,
            color: AppColors.primaryDark,
            size: 36,
          ),
          SizedBox(height: 10),
          Text(
            'Hôm nay không có liều uống nào.',
            style: TextStyle(fontWeight: FontWeight.w800),
          ),
          SizedBox(height: 4),
          Text(
            'Bạn có thể xem lịch sử hoặc kiểm tra các kế hoạch đang chạy.',
            style: TextStyle(color: AppColors.textSecondary),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

class _TodayDoseTile extends StatelessWidget {
  const _TodayDoseTile({
    required this.dose,
    required this.canMark,
    required this.onTaken,
    required this.onSkipped,
  });

  final TodayDose dose;
  final bool canMark;
  final VoidCallback onTaken;
  final VoidCallback onSkipped;

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final status = dose.effectiveStatus(now);
    final pending = status == 'pending';
    final statusMeta = switch (status) {
      'taken' => ('Đã uống', AppColors.success, Icons.check_circle_rounded),
      'skipped' => ('Bỏ qua', AppColors.warning, Icons.remove_circle_rounded),
      'missed' => ('Đã quên', AppColors.error, Icons.error_rounded),
      _ when dose.isDueNow(now) => (
        'Đến giờ uống',
        AppColors.primaryDark,
        Icons.alarm_rounded,
      ),
      _ when dose.isUpcomingSoon(now) => (
        'Sắp đến giờ',
        AppColors.info,
        Icons.notifications_active_rounded,
      ),
      _ => ('Chờ đến giờ', AppColors.primaryDark, Icons.schedule_rounded),
    };

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        children: [
          Row(
            children: [
              SizedBox(
                width: 56,
                child: Column(
                  children: [
                    Text(
                      dose.time,
                      style: const TextStyle(
                        fontWeight: FontWeight.w900,
                        fontSize: 22,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Icon(statusMeta.$3, color: statusMeta.$2, size: 20),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      dose.primaryTitle,
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 4),
                    if (dose.medications.isNotEmpty)
                      ...dose.medications.map(
                        (item) => Padding(
                          padding: const EdgeInsets.only(bottom: 2),
                          child: Text(
                            '${item.drugName}: ${item.pills} viên',
                            style: const TextStyle(
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ),
                      )
                    else
                      Text(
                        dose.dosage?.isNotEmpty == true
                            ? dose.dosage!
                            : '${dose.pillsPerDose ?? 1} viên/liều',
                        style: const TextStyle(color: AppColors.textSecondary),
                      ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: statusMeta.$2.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        statusMeta.$1,
                        style: TextStyle(
                          color: statusMeta.$2,
                          fontWeight: FontWeight.w800,
                          fontSize: 12,
                        ),
                      ),
                    ),
                    if (dose.isUpcomingSoon(now)) ...[
                      const SizedBox(height: 8),
                      const Text(
                        'Thông báo trước 30 phút đã được lên lịch.',
                        style: TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 12,
                        ),
                      ),
                    ] else if (dose.isDueNow(now)) ...[
                      const SizedBox(height: 8),
                      const Text(
                        'Nếu chưa uống, hệ thống sẽ nhắc lại mỗi 15 phút.',
                        style: TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 12,
                        ),
                      ),
                    ] else if (status == 'missed') ...[
                      const SizedBox(height: 8),
                      const Text(
                        'Liều này đã quá 45 phút nên được chuyển sang trạng thái quên.',
                        style: TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
          if (pending && dose.isDueNow(now)) ...[
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: canMark ? onSkipped : null,
                    child: const Text('Bỏ qua'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: ElevatedButton(
                    onPressed: canMark ? onTaken : null,
                    child: const Text('Đã uống'),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
