import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../../create_plan/data/plan_repository.dart';
import '../../create_plan/domain/plan.dart';

class PlanListScreen extends ConsumerStatefulWidget {
  const PlanListScreen({super.key});

  @override
  ConsumerState<PlanListScreen> createState() => _PlanListScreenState();
}

class _PlanListScreenState extends ConsumerState<PlanListScreen> {
  bool _isLoading = true;
  String? _error;
  List<Plan> _plans = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final repo = ref.read(planRepositoryProvider);
      final plans = await repo.getPlans(activeOnly: false);
      setState(() {
        _plans = plans;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final activePlans = _plans.where((plan) => plan.isActive).toList();
    final inactivePlans = _plans.where((plan) => !plan.isActive).toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Ke hoach'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add_circle_outline),
            onPressed: () => context.go('/create'),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _isLoading
            ? ListView(
                children: [
                  SizedBox(
                    height: 500,
                    child: Center(child: CircularProgressIndicator()),
                  ),
                ],
              )
            : _error != null
            ? ListView(
                children: [
                  SizedBox(
                    height: 500,
                    child: Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(
                              Icons.error_outline,
                              color: AppColors.error,
                              size: 48,
                            ),
                            const SizedBox(height: 16),
                            Text(_error!, textAlign: TextAlign.center),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              )
            : ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  _SummaryHeader(
                    activeCount: activePlans.length,
                    totalCount: _plans.length,
                  ),
                  const SizedBox(height: 20),
                  _SectionTitle(
                    title: 'Dang kich hoat',
                    subtitle: activePlans.isEmpty
                        ? 'Chua co ke hoach nao dang chay'
                        : '${activePlans.length} ke hoach dang nhac thuoc',
                  ),
                  const SizedBox(height: 10),
                  if (activePlans.isEmpty)
                    _EmptyPlanCard(
                      message:
                          'Ban chua co ke hoach dang kich hoat. Quet don moi hoac tao thu cong.',
                    )
                  else
                    ...activePlans.map((plan) => _PlanTile(plan: plan)),
                  const SizedBox(height: 20),
                  _SectionTitle(
                    title: 'Da ket thuc',
                    subtitle: inactivePlans.isEmpty
                        ? 'Chua co ke hoach da ket thuc'
                        : '${inactivePlans.length} ke hoach luu trong lich su',
                  ),
                  const SizedBox(height: 10),
                  if (inactivePlans.isEmpty)
                    _EmptyPlanCard(
                      message:
                          'Ke hoach ket thuc se xuat hien o day de ban xem lai.',
                    )
                  else
                    ...inactivePlans.map((plan) => _PlanTile(plan: plan)),
                  const SizedBox(height: 16),
                ],
              ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.go('/create'),
        backgroundColor: AppColors.primary,
        icon: const Icon(Icons.add),
        label: const Text('Tao ke hoach'),
      ),
    );
  }
}

class _SummaryHeader extends StatelessWidget {
  const _SummaryHeader({required this.activeCount, required this.totalCount});

  final int activeCount;
  final int totalCount;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.surfaceHigh),
      ),
      child: Row(
        children: [
          Expanded(
            child: _SummaryMetric(label: 'Dang chay', value: '$activeCount'),
          ),
          Expanded(
            child: _SummaryMetric(label: 'Tong', value: '$totalCount'),
          ),
          Expanded(
            child: _SummaryMetric(
              label: 'Trang thai',
              value: activeCount > 0 ? 'On' : 'Empty',
            ),
          ),
        ],
      ),
    );
  }
}

class _SummaryMetric extends StatelessWidget {
  const _SummaryMetric({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          value,
          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
        ),
      ],
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 18),
        ),
        const SizedBox(height: 2),
        Text(
          subtitle,
          style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
        ),
      ],
    );
  }
}

class _EmptyPlanCard extends StatelessWidget {
  const _EmptyPlanCard({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.surfaceHigh),
      ),
      child: Text(
        message,
        style: const TextStyle(color: AppColors.textSecondary),
      ),
    );
  }
}

class _PlanTile extends ConsumerWidget {
  const _PlanTile({required this.plan});

  final Plan plan;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final statusColor = plan.isActive ? AppColors.success : AppColors.textMuted;
    final statusLabel = plan.isActive ? 'Dang chay' : 'Da ket thuc';

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.surfaceHigh),
      ),
      child: ListTile(
        onTap: () => context.go('/plans/${plan.id}'),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: CircleAvatar(
          backgroundColor: AppColors.primary.withValues(alpha: 0.15),
          child: const Icon(
            Icons.medication_outlined,
            color: AppColors.primary,
          ),
        ),
        title: Text(
          plan.drugName,
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        subtitle: Text(
          '${_freqLabel(plan.frequency)} · ${plan.times.join(', ')}',
          style: const TextStyle(color: AppColors.textSecondary),
        ),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              statusLabel,
              style: TextStyle(color: statusColor, fontSize: 12),
            ),
            const SizedBox(height: 4),
            Text(
              '${plan.pillsPerDose} vien/lan',
              style: const TextStyle(fontSize: 12),
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
      case 'as_needed':
        return 'Khi can';
      default:
        return '1 lan/ngay';
    }
  }
}
