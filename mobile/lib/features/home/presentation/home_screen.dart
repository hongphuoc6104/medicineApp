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
          final stateError = state.error == null
              ? null
              : Exception(state.error);

          if (!state.hasPlans && state.error != null) {
            return _ErrorView(
              message: toFriendlyNetworkMessage(
                stateError!,
                genericMessage:
                    'Không tải được dữ liệu hôm nay. Vui lòng thử lại.',
              ),
              onRetry: () => ref.read(planNotifierProvider.notifier).refresh(),
            );
          }

          return RefreshIndicator(
            onRefresh: () async {
              await ref.read(planNotifierProvider.notifier).refresh();
              await ref.read(todayScheduleNotifierProvider.notifier).refresh();
            },
            child: state.hasPlans
                ? _DashboardView(plans: state.plans, todayAsync: todayAsync)
                : _OnboardingView(isOfflineCache: state.isFromCache),
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
  const _OnboardingView({this.isOfflineCache = false});

  final bool isOfflineCache;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 120),
      children: [
        if (isOfflineCache)
          Container(
            margin: const EdgeInsets.only(bottom: 14),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.warning.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Row(
              children: [
                Icon(Icons.cloud_off_outlined, color: AppColors.warning),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Đang dùng dữ liệu offline. Kéo xuống để thử đồng bộ lại.',
                  ),
                ),
              ],
            ),
          ),
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
                l10n.homeOnboardingTitle,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                l10n.homeOnboardingSubtitle,
                style: const TextStyle(
                  color: AppColors.textSecondary,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: 18),
              ElevatedButton.icon(
                onPressed: () => context.go('/create/scan'),
                icon: const Icon(Icons.document_scanner_outlined),
                label: Text(l10n.homeActionScan),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => context.go('/create/edit'),
                      icon: const Icon(Icons.edit_note),
                      label: Text(l10n.homeActionManual),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => context.go('/create/reuse'),
                      icon: const Icon(Icons.history_outlined),
                      label: Text(l10n.homeActionHistory),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),
        _LookupPrimaryCard(onTap: () => context.go('/lookup')),
        const SizedBox(height: 14),
        const _SectionLabel(title: 'Lối tắt'),
        const SizedBox(height: 10),
        _QuickActionGrid(
          actions: [
            _QuickActionItem(
              title: l10n.homeActionPlans,
              subtitle: l10n.homeActionPlansSubtitle,
              icon: Icons.calendar_month_rounded,
              onTap: () => context.go('/plans'),
            ),
            _QuickActionItem(
              title: l10n.homeActionDrugLookup,
              subtitle: l10n.homeActionDrugLookupSubtitle,
              icon: Icons.search_rounded,
              onTap: () => context.go('/lookup'),
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
            final featuredDose = dueNow.isNotEmpty
                ? dueNow.first
                : upcoming.isNotEmpty
                ? upcoming.first
                : laterToday.isNotEmpty
                ? laterToday.first
                : null;

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
                    backgroundColor: result == MarkDoseResult.synced
                        ? AppColors.success
                        : AppColors.warning,
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
                _HeroTodayCard(today: today, featuredDose: featuredDose),
                const SizedBox(height: 16),
                _QuickActionGrid(
                  actions: [
                    _QuickActionItem(
                      title: AppLocalizations.of(context).homeActionScan,
                      subtitle: 'Quét đơn để tạo kế hoạch mới',
                      icon: Icons.document_scanner_outlined,
                      onTap: () => context.go('/create/scan'),
                    ),
                    _QuickActionItem(
                      title: AppLocalizations.of(context).homeActionManual,
                      subtitle: 'Nhập tay nếu không có ảnh',
                      icon: Icons.edit_note,
                      onTap: () => context.go('/create/edit'),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                if (today.doses.isEmpty)
                  _TodayEmptyCard(
                    onScan: () => context.go('/create/scan'),
                    onCreatePlan: () => context.go('/create/edit'),
                    onViewPlans: () => context.go('/plans'),
                  )
                else ...[
                  if (dueNow.isNotEmpty) ...[
                    const _SectionLabel(title: 'Đến giờ uống'),
                    const SizedBox(height: 10),
                    ...dueNow.map(doseTile),
                    const SizedBox(height: 8),
                  ],
                  if (upcoming.isNotEmpty) ...[
                    const _SectionLabel(title: 'Sắp đến giờ'),
                    const SizedBox(height: 10),
                    ...upcoming.map(doseTile),
                    const SizedBox(height: 8),
                  ],
                  if (laterToday.isNotEmpty) ...[
                    const _SectionLabel(title: 'Còn lại hôm nay'),
                    const SizedBox(height: 10),
                    ...laterToday.map(doseTile),
                    const SizedBox(height: 8),
                  ],
                  if (dueNow.isEmpty && upcoming.isEmpty && laterToday.isEmpty)
                    _TodayEmptyCard(
                      onScan: () => context.go('/create/scan'),
                      onCreatePlan: () => context.go('/create/edit'),
                      onViewPlans: () => context.go('/plans'),
                    ),
                ],
                const SizedBox(height: 18),
                const _SectionLabel(title: 'Kế hoạch đang chạy'),
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

String _formatHomeDate(DateTime date) {
  return DateFormat('d MMMM, yyyy', 'vi_VN').format(date);
}

String _doseSummaryText(TodayDose dose) {
  final medications = dose.medications
      .where((item) => item.drugName.trim().isNotEmpty)
      .toList();

  if (medications.isNotEmpty) {
    if (medications.length == 1) {
      final item = medications.first;
      return '${item.drugName}: ${item.pills} viên';
    }

    final preview = medications
        .take(2)
        .map((item) => item.drugName.trim())
        .join(', ');
    final extra = medications.length - 2;
    final totalPills = medications.fold<int>(
      0,
      (sum, item) => sum + item.pills,
    );
    return extra > 0
        ? '$preview và $extra thuốc khác • $totalPills viên'
        : '$preview • $totalPills viên';
  }

  final dosage = dose.dosage?.trim();
  if (dosage != null && dosage.isNotEmpty) {
    return dosage;
  }

  return '${dose.pillsPerDose ?? 1} viên/liều';
}

String _planFrequencyLabel(BuildContext context, String freq) {
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

String _planSubtitleText(BuildContext context, Plan plan) {
  final freq = _planFrequencyLabel(context, plan.frequency);
  final times = plan.times.join(', ');

  if (plan.hasVariableDoseSchedule) {
    return '$freq · ${AppLocalizations.of(context).homeFreqHourly} · $times';
  }

  return '$freq · ${plan.pillsPerDose} viên · $times';
}

class _DateHeader extends StatelessWidget {
  const _DateHeader();

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final dateLabel = _formatHomeDate(now);
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
  const _HeroTodayCard({required this.today, required this.featuredDose});

  final TodaySchedule today;
  final TodayDose? featuredDose;

  String _formatCountdown(DateTime scheduled, DateTime now) {
    final diff = scheduled.difference(now);
    if (diff.inMinutes > 0) {
      if (diff.inHours > 0) {
        return 'Còn ${diff.inHours} giờ ${diff.inMinutes.remainder(60)} phút';
      }
      return 'Còn ${diff.inMinutes} phút';
    }
    final overdue = diff.abs();
    if (overdue.inHours > 0) {
      return 'Trễ ${overdue.inHours} giờ ${overdue.inMinutes.remainder(60)} phút';
    }
    return 'Trễ ${overdue.inMinutes} phút';
  }

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final scheduled = featuredDose?.scheduledLocalDateTime;
    final title = featuredDose == null
        ? 'Hôm nay chưa có liều nào'
        : featuredDose!.primaryTitle;
    final subtitle = featuredDose == null
        ? 'Bạn có thể tạo kế hoạch mới hoặc dùng lại kế hoạch cũ'
        : '${featuredDose!.time} • ${scheduled == null ? 'Đang chờ' : _formatCountdown(scheduled, now)}';

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFFEFFAF9), Color(0xFFF9FFFE)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: const Icon(
                  Icons.medication_liquid_rounded,
                  color: AppColors.primaryDark,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Hôm nay',
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: AppColors.primaryDark,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      AppLocalizations.of(context).homeHeroTitle,
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
          const SizedBox(height: 18),
          Text(
            title,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w900,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            subtitle,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: AppColors.textSecondary, height: 1.4),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _HeroChip(
                label: 'Tổng ${today.summary.total}',
                color: AppColors.primaryDark,
              ),
              _HeroChip(
                label: 'Đã uống ${today.summary.taken}',
                color: AppColors.success,
              ),
              _HeroChip(
                label: 'Còn ${today.summary.pending}',
                color: AppColors.info,
              ),
              if (today.summary.missed > 0)
                _HeroChip(
                  label: 'Quên ${today.summary.missed}',
                  color: AppColors.error,
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _LookupPrimaryCard extends StatelessWidget {
  const _LookupPrimaryCard({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(26),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Color(0xFF2AD1C9), Color(0xFF59D8D3)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(26),
          boxShadow: [
            BoxShadow(
              color: AppColors.primary.withValues(alpha: 0.18),
              blurRadius: 18,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.20),
                borderRadius: BorderRadius.circular(18),
              ),
              child: const Icon(
                Icons.search_rounded,
                color: Colors.white,
                size: 30,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.homeActionDrugLookup,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    l10n.homeActionDrugLookupSubtitle,
                    style: const TextStyle(
                      color: Colors.white,
                      height: 1.35,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            const Icon(
              Icons.chevron_right_rounded,
              color: Colors.white,
              size: 30,
            ),
          ],
        ),
      ),
    );
  }
}

class _HeroChip extends StatelessWidget {
  const _HeroChip({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.w800,
          fontSize: 12,
        ),
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
    final width = MediaQuery.sizeOf(context).width;
    final crossAxisCount = width < 360 ? 1 : 2;
    final childAspectRatio = crossAxisCount == 1 ? 2.55 : 1.05;

    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: actions.length,
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: crossAxisCount,
        childAspectRatio: childAspectRatio,
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
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 4),
                Text(
                  item.subtitle,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
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
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 15,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _planSubtitleText(context, plan),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
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
  const _TodayEmptyCard({
    required this.onScan,
    required this.onCreatePlan,
    required this.onViewPlans,
  });

  final VoidCallback onScan;
  final VoidCallback onCreatePlan;
  final VoidCallback onViewPlans;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Icon(
            Icons.event_available_rounded,
            color: AppColors.primaryDark,
            size: 36,
          ),
          const SizedBox(height: 10),
          const Text(
            'Hôm nay không có liều uống nào.',
            textAlign: TextAlign.center,
            style: TextStyle(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 4),
          const Text(
            'Bạn có thể quét đơn mới, nhập tay kế hoạch hoặc mở danh sách kế hoạch đang chạy.',
            style: TextStyle(color: AppColors.textSecondary),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: onScan,
              icon: const Icon(Icons.document_scanner_outlined),
              label: const Text('Quét đơn'),
            ),
          ),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: onCreatePlan,
              icon: const Icon(Icons.edit_note),
              label: const Text('Tạo kế hoạch'),
            ),
          ),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: TextButton.icon(
              onPressed: onViewPlans,
              icon: const Icon(Icons.view_list_outlined),
              label: const Text('Xem kế hoạch'),
            ),
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
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _doseSummaryText(dose),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
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
