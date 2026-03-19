import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

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
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Da dong bo $synced thao tac offline'),
              backgroundColor: AppColors.success,
            ),
          );
        }
      }
    });

    return Scaffold(
      appBar: AppBar(
        title: const Text('MedicineApp'),
        actions: [
          IconButton(
            onPressed: () => context.go('/settings'),
            icon: const Icon(Icons.settings_outlined),
          ),
          const SizedBox(width: 6),
        ],
      ),
      body: plansAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => _ErrorView(
          error: e.toString(),
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
  const _ErrorView({required this.error, required this.onRetry});

  final String error;
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
          'Khong tai duoc du lieu hom nay',
          textAlign: TextAlign.center,
          style: Theme.of(
            context,
          ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 8),
        Text(
          error,
          textAlign: TextAlign.center,
          style: const TextStyle(color: AppColors.textSecondary),
        ),
        const SizedBox(height: 18),
        ElevatedButton.icon(
          onPressed: onRetry,
          icon: const Icon(Icons.refresh),
          label: const Text('Thu lai'),
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
                'Bat dau quan ly thuoc mot cach de hieu',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Quet don thuoc de tao lich nhac, hoac nhap thu cong neu ban muon bat dau ngay.',
                style: TextStyle(color: AppColors.textSecondary, height: 1.45),
              ),
              const SizedBox(height: 18),
              ElevatedButton.icon(
                onPressed: () => context.go('/create/scan'),
                icon: const Icon(Icons.document_scanner_outlined),
                label: const Text('Quet don thuoc moi'),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => context.go('/create/edit'),
                      icon: const Icon(Icons.edit_note),
                      label: const Text('Nhap tay'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => context.go('/history'),
                      icon: const Icon(Icons.history_outlined),
                      label: const Text('Lich su'),
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
              title: 'Tra cuu thuoc',
              subtitle: 'Xem thong tin thuoc va hoat chat',
              icon: Icons.search_rounded,
              onTap: () => context.go('/drugs'),
            ),
            _QuickActionItem(
              title: 'Ke hoach',
              subtitle: 'Xem cac lich da tao',
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
                      '$count thao tac dang cho dong bo. Keo xuong de dong bo lai.',
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
            message: e.toString(),
            onRetry: () =>
                ref.read(todayScheduleNotifierProvider.notifier).refresh(),
          ),
          data: (today) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _HeroTodayCard(today: today),
                const SizedBox(height: 16),
                _SectionLabel(
                  title: 'Thuoc hom nay',
                  actionLabel: 'Ke hoach',
                  onAction: () => context.go('/plans'),
                ),
                const SizedBox(height: 10),
                if (today.doses.isEmpty)
                  const _TodayEmptyCard()
                else
                  ...today.doses.map(
                    (dose) => _TodayDoseTile(
                      dose: dose,
                      canMark: canMark,
                      onVerify: () => context.go('/pill-verify', extra: dose),
                      onTaken: () async {
                        final ok = await ref
                            .read(todayScheduleNotifierProvider.notifier)
                            .markDose(dose: dose, status: 'taken');
                        if (!context.mounted) return;
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              ok
                                  ? 'Da uong: ${dose.drugName}'
                                  : 'Da luu tam offline',
                            ),
                            backgroundColor: ok
                                ? AppColors.success
                                : AppColors.warning,
                          ),
                        );
                      },
                      onSkipped: () async {
                        final ok = await ref
                            .read(todayScheduleNotifierProvider.notifier)
                            .markDose(dose: dose, status: 'skipped');
                        if (!context.mounted) return;
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              ok
                                  ? 'Da bo qua: ${dose.drugName}'
                                  : 'Da luu tam offline',
                            ),
                            backgroundColor: ok
                                ? AppColors.warning
                                : AppColors.warning,
                          ),
                        );
                      },
                    ),
                  ),
                const SizedBox(height: 18),
                const _SectionLabel(title: 'Dang su dung'),
                const SizedBox(height: 10),
                ...plans.take(3).map((plan) => _PlanCard(plan: plan)),
                if (plans.length > 3) ...[
                  const SizedBox(height: 8),
                  TextButton.icon(
                    onPressed: () => context.go('/plans'),
                    icon: const Icon(Icons.open_in_new),
                    label: Text('Xem ${plans.length} ke hoach'),
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
    final dateLabel = DateFormat('d MMMM, yyyy', 'vi_VN').format(now);
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Hom nay',
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
          child: const Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.calendar_today_rounded,
                size: 16,
                color: AppColors.primaryDark,
              ),
              SizedBox(width: 6),
              Text('Thuoc hom nay'),
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
          const Text(
            'Theo doi lieu uong hom nay',
            style: TextStyle(
              color: Colors.white,
              fontSize: 14,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '${today.summary.total} lieu can quan tam',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 18),
          Row(
            children: [
              _HeroMetric(label: 'Da uong', value: '${today.summary.taken}'),
              _HeroMetric(label: 'Cho', value: '${today.summary.pending}'),
              _HeroMetric(label: 'Bo qua', value: '${today.summary.skipped}'),
              _HeroMetric(label: 'Missed', value: '${today.summary.missed}'),
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
  const _SectionLabel({required this.title, this.actionLabel, this.onAction});

  final String title;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Text(
          title,
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
        ),
        const Spacer(),
        if (actionLabel != null && onAction != null)
          TextButton(onPressed: onAction, child: Text(actionLabel!)),
      ],
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
                    '${_freqLabel(plan.frequency)} · ${plan.pillsPerDose} vien · ${plan.times.join(', ')}',
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
              child: const Text(
                'Active',
                style: TextStyle(
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

  static String _freqLabel(String freq) {
    switch (freq) {
      case 'twice_daily':
        return '2 lan/ngay';
      case 'three_daily':
        return '3 lan/ngay';
      case 'weekly':
        return 'Hang tuan';
      default:
        return '1 lan/ngay';
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
      child: const Row(
        children: [
          SizedBox(
            width: 22,
            height: 22,
            child: CircularProgressIndicator(strokeWidth: 2.4),
          ),
          SizedBox(width: 14),
          Expanded(child: Text('Dang tai ke hoach hom nay...')),
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
          const Text(
            'Khong tai duoc lich hom nay',
            style: TextStyle(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          Text(message, style: const TextStyle(color: AppColors.textSecondary)),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh),
            label: const Text('Thu lai'),
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
            'Hom nay khong co lieu uong nao.',
            style: TextStyle(fontWeight: FontWeight.w800),
          ),
          SizedBox(height: 4),
          Text(
            'Ban co the xem lich su hoac kiem tra cac ke hoach dang chay.',
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
    required this.onVerify,
    required this.onTaken,
    required this.onSkipped,
  });

  final TodayDose dose;
  final bool canMark;
  final VoidCallback onVerify;
  final VoidCallback onTaken;
  final VoidCallback onSkipped;

  @override
  Widget build(BuildContext context) {
    final status = dose.status;
    final pending = status == 'pending';
    final statusMeta = switch (status) {
      'taken' => ('Da uong', AppColors.success, Icons.check_circle_rounded),
      'skipped' => ('Bo qua', AppColors.warning, Icons.remove_circle_rounded),
      'missed' => ('Missed', AppColors.error, Icons.error_rounded),
      _ => ('Cho den gio', AppColors.primaryDark, Icons.schedule_rounded),
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
                      dose.drugName,
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      dose.dosage?.isNotEmpty == true
                          ? dose.dosage!
                          : '${dose.pillsPerDose ?? 1} vien/lien',
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
                  ],
                ),
              ),
            ],
          ),
          if (pending) ...[
            const SizedBox(height: 14),
            OutlinedButton.icon(
              onPressed: canMark ? onVerify : null,
              icon: const Icon(Icons.photo_camera_back_outlined),
              label: const Text('Kiem tra thuoc truoc khi uong'),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: canMark ? onSkipped : null,
                    child: const Text('Bo qua'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: ElevatedButton(
                    onPressed: canMark ? onTaken : null,
                    child: const Text('Da uong'),
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
