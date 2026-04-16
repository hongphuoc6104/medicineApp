import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../core/session/current_user_store.dart';
import '../../../core/theme/app_theme.dart';
import '../../create_plan/data/plan_repository.dart';
import '../../create_plan/domain/plan.dart';
import '../../home/data/plan_cache.dart';
import '../../home/data/plan_notifier.dart';
import '../../home/data/today_schedule_notifier.dart';

class PlanDetailScreen extends ConsumerStatefulWidget {
  const PlanDetailScreen({super.key, required this.planId});

  final String planId;

  @override
  ConsumerState<PlanDetailScreen> createState() => _PlanDetailScreenState();
}

class _PlanDetailScreenState extends ConsumerState<PlanDetailScreen> {
  bool _isLoading = true;
  bool _isSaving = false;
  String? _error;
  Plan? _plan;
  late final TextEditingController _drugCtrl;
  late final TextEditingController _dosageCtrl;
  late final TextEditingController _notesCtrl;
  late DateTime _startDate;
  List<String> _times = ['07:00'];
  String _frequency = 'daily';
  int _pillsPerDose = 1;
  List<DoseScheduleItem> _doseSchedule = const [];
  int _totalDays = 7;

  @override
  void initState() {
    super.initState();
    _drugCtrl = TextEditingController();
    _dosageCtrl = TextEditingController();
    _notesCtrl = TextEditingController();
    _load();
  }

  @override
  void dispose() {
    _drugCtrl.dispose();
    _dosageCtrl.dispose();
    _notesCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final repo = ref.read(planRepositoryProvider);
      final plan = await repo.getPlanById(widget.planId);
      final userStore = ref.read(currentUserStoreProvider);
      final userId = await userStore.getCurrentUserId();
      if (userId != null && userId.isNotEmpty) {
        final cache = ref.read(planCacheProvider);
        final cachedAll = await cache.load(userId: userId, activeOnly: false);
        final mergedById = <String, Plan>{
          for (final item in cachedAll) item.id: item,
        };
        mergedById[plan.id] = plan;
        final merged = mergedById.values.toList();
        await cache.save(userId: userId, activeOnly: false, plans: merged);
      }
      _applyPlan(plan);
      setState(() {
        _plan = plan;
        _isLoading = false;
      });
    } catch (e) {
      final userStore = ref.read(currentUserStoreProvider);
      final userId = await userStore.getCurrentUserId();
      if (userId != null && userId.isNotEmpty) {
        final cache = ref.read(planCacheProvider);
        final cached = await cache.load(userId: userId, activeOnly: false);
        final matched = cached.where((item) => item.id == widget.planId);
        if (matched.isNotEmpty) {
          final offlinePlan = matched.first;
          _applyPlan(offlinePlan);
          setState(() {
            _plan = offlinePlan;
            _error = 'Đang hiển thị dữ liệu offline cho kế hoạch này.';
            _isLoading = false;
          });
          return;
        }
      }

      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  void _openDrugEditor() {
    final current = _plan;
    if (current == null) return;

    context.go('/create/edit', extra: PlanEditFlowArgs.fromPlan(current));
  }

  void _handleBack() {
    if (Navigator.of(context).canPop()) {
      Navigator.of(context).pop();
      return;
    }
    context.go('/plans');
  }

  void _applyPlan(Plan plan) {
    _drugCtrl.text = plan.drugName;
    _dosageCtrl.text = plan.dosage ?? '';
    _notesCtrl.text = plan.notes ?? '';
    _frequency = plan.frequency;
    _times = List<String>.from(plan.times.isEmpty ? ['07:00'] : plan.times);
    _pillsPerDose = plan.pillsPerDose;
    _doseSchedule = plan.doseSchedule.map((item) => item.copyWith()).toList();
    _totalDays = plan.totalDays ?? 7;
    _startDate = DateTime.tryParse(plan.startDate) ?? DateTime.now();
  }

  void _syncDoseScheduleWithTimes() {
    final existing = {for (final item in _doseSchedule) item.time: item.pills};
    _doseSchedule =
        _times
            .map(
              (time) => DoseScheduleItem(
                time: time,
                pills: existing[time] ?? _pillsPerDose,
              ),
            )
            .toList()
          ..sort((a, b) => a.time.compareTo(b.time));
    if (_doseSchedule.isNotEmpty) {
      _pillsPerDose = _doseSchedule.first.pills;
    }
  }

  Future<void> _pickStartDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _startDate,
      firstDate: DateTime.now().subtract(const Duration(days: 30)),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked != null) {
      setState(() => _startDate = picked);
    }
  }

  Future<void> _editTimes() async {
    final draft = List<String>.from(_times);
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) {
        return DraggableScrollableSheet(
          initialChildSize: 0.55,
          minChildSize: 0.35,
          maxChildSize: 0.9,
          expand: false,
          builder: (context, scrollController) {
            return StatefulBuilder(
              builder: (ctx, setModalState) {
                return SafeArea(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Chọn giờ uống',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Expanded(
                          child: ListView(
                            controller: scrollController,
                            children: [
                              ...draft.asMap().entries.map((entry) {
                                final idx = entry.key;
                                final value = entry.value;
                                return ListTile(
                                  contentPadding: EdgeInsets.zero,
                                  leading: const Icon(Icons.access_time),
                                  title: Text(
                                    value,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                  trailing: IconButton(
                                    icon: const Icon(Icons.edit_outlined),
                                    onPressed: () async {
                                      final parts = value.split(':');
                                      final picked = await showTimePicker(
                                        context: ctx,
                                        initialTime: TimeOfDay(
                                          hour: int.parse(parts[0]),
                                          minute: int.parse(parts[1]),
                                        ),
                                      );
                                      if (picked != null) {
                                        setModalState(() {
                                          draft[idx] =
                                              '${picked.hour.toString().padLeft(2, '0')}:${picked.minute.toString().padLeft(2, '0')}';
                                        });
                                      }
                                    },
                                  ),
                                );
                              }),
                            ],
                          ),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            OutlinedButton.icon(
                              onPressed: draft.length < 4
                                  ? () =>
                                        setModalState(() => draft.add('21:00'))
                                  : null,
                              icon: const Icon(Icons.add),
                              label: const Text('Thêm giờ'),
                            ),
                            const Spacer(),
                            ElevatedButton(
                              onPressed: () {
                                setState(() {
                                  _times = draft;
                                  _syncDoseScheduleWithTimes();
                                });
                                Navigator.pop(ctx);
                              },
                              child: const Text('Lưu'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            );
          },
        );
      },
    );
  }

  Future<void> _save() async {
    final current = _plan;
    if (current == null) {
      return;
    }
    if (_drugCtrl.text.trim().isEmpty) {
      setState(() => _error = 'Tên thuốc không được để trống');
      return;
    }
    setState(() {
      _isSaving = true;
      _error = null;
    });
    try {
      final repo = ref.read(planRepositoryProvider);
      final updated = await repo.updatePlan(
        current.id,
        _buildUpdatedPlan(current),
      );
      ref.invalidate(planNotifierProvider);
      ref.invalidate(todayScheduleNotifierProvider);
      setState(() {
        _plan = updated;
        _isSaving = false;
      });
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Đã cập nhật kế hoạch')));
    } on DioException catch (e) {
      setState(() {
        _isSaving = false;
        _error = e.message ?? 'Không lưu được kế hoạch';
      });
    } catch (e) {
      setState(() {
        _isSaving = false;
        _error = e.toString();
      });
    }
  }

  Plan _buildUpdatedPlan(Plan current) {
    final normalizedTitle = _drugCtrl.text.trim();
    final normalizedNotes = _notesCtrl.text.trim();
    final startDate = DateFormat('yyyy-MM-dd').format(_startDate);
    final endDate = _startDate.add(Duration(days: _totalDays - 1));
    final endDateStr = DateFormat('yyyy-MM-dd').format(endDate);

    if (current.drugs.length <= 1) {
      final drugId = current.drugs.isNotEmpty
          ? current.drugs.first.id
          : 'plan-drug-0';
      final drugs = [
        PlanMedication(
          id: drugId,
          drugName: normalizedTitle,
          dosage: _dosageCtrl.text.trim().isEmpty
              ? null
              : _dosageCtrl.text.trim(),
          notes: normalizedNotes.isEmpty ? null : normalizedNotes,
          sortOrder: 0,
        ),
      ];
      final slots = _doseSchedule
          .asMap()
          .entries
          .map(
            (entry) => PlanSlot(
              id: current.slots.length > entry.key
                  ? current.slots[entry.key].id
                  : '',
              time: entry.value.time,
              sortOrder: entry.key,
              items: [
                PlanSlotMedication(
                  drugId: drugId,
                  drugName: normalizedTitle,
                  dosage: _dosageCtrl.text.trim().isEmpty
                      ? null
                      : _dosageCtrl.text.trim(),
                  pills: entry.value.pills,
                ),
              ],
            ),
          )
          .toList();

      return current.copyWith(
        title: normalizedTitle,
        drugs: drugs,
        slots: slots,
        totalDays: _totalDays,
        startDate: startDate,
        endDate: endDateStr,
        notes: normalizedNotes,
      );
    }

    // Multi-drug plans keep group structure; this screen only updates common metadata.
    return current.copyWith(
      title: current.title,
      totalDays: _totalDays,
      startDate: startDate,
      endDate: endDateStr,
      notes: normalizedNotes,
    );
  }

  Future<void> _deactivate() async {
    final current = _plan;
    if (current == null) return;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Kết thúc kế hoạch?'),
        content: const Text(
          'Kế hoạch sẽ được ngừng kích hoạt và không nhắc nữa.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Hủy'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Kết thúc'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      final repo = ref.read(planRepositoryProvider);
      await repo.deletePlan(current.id);
      ref.invalidate(planNotifierProvider);
      ref.invalidate(todayScheduleNotifierProvider);
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Đã kết thúc kế hoạch')));
      context.go('/plans');
    } catch (e) {
      setState(() => _error = e.toString());
    }
  }

  Future<void> _reactivate() async {
    final current = _plan;
    if (current == null) return;
    try {
      final repo = ref.read(planRepositoryProvider);
      final updated = await repo.setPlanActive(current.id, true);
      ref.invalidate(planNotifierProvider);
      ref.invalidate(todayScheduleNotifierProvider);
      setState(() => _plan = updated);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Đã kích hoạt lại kế hoạch')),
      );
    } catch (e) {
      setState(() => _error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    if (_plan == null) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Chi tiết kế hoạch'),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: _handleBack,
          ),
        ),
        body: Center(child: Text(_error ?? 'Không tải được kế hoạch')),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Chi tiết kế hoạch'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: _handleBack,
        ),
        actions: [
          IconButton(
            onPressed: _openDrugEditor,
            icon: const Icon(Icons.edit_note_rounded),
            tooltip: 'Sửa thuốc và lịch',
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _sectionCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _plan!.drugName,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w900,
                  ),
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 6),
                Text(
                  'Từ ${DateFormat('dd/MM/yyyy').format(_startDate)} • $_totalDays ngày',
                  style: const TextStyle(color: AppColors.textSecondary),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _pill(
                      'Thuốc ${_plan!.drugs.length}',
                      AppColors.primaryDark,
                    ),
                    _pill('Giờ ${_plan!.slots.length}', AppColors.info),
                    _pill(
                      _plan!.isActive ? 'Đang chạy' : 'Đã kết thúc',
                      _plan!.isActive ? AppColors.success : AppColors.textMuted,
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          _sectionLabel('THUỐC TRONG KẾ HOẠCH'),
          const SizedBox(height: 8),
          ..._plan!.drugs.map(
            (drug) => _sectionCard(
              margin: const EdgeInsets.only(bottom: 10),
              child: Row(
                children: [
                  const Icon(
                    Icons.medication_outlined,
                    color: AppColors.primaryDark,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          drug.drugName,
                          style: const TextStyle(fontWeight: FontWeight.w700),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (drug.dosage != null) ...[
                          const SizedBox(height: 2),
                          Text(
                            drug.dosage!,
                            style: const TextStyle(
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 6),
          _sectionLabel('LỊCH UỐNG'),
          const SizedBox(height: 8),
          ..._plan!.slots.map(
            (slot) => _sectionCard(
              margin: const EdgeInsets.only(bottom: 10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(
                        Icons.access_time,
                        size: 18,
                        color: AppColors.primaryDark,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        slot.time,
                        style: const TextStyle(fontWeight: FontWeight.w800),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  ...slot.items.map(
                    (item) => Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: Text(
                        '${item.drugName}: ${item.pills} viên',
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          if ((_plan!.notes ?? '').trim().isNotEmpty) ...[
            const SizedBox(height: 6),
            _sectionLabel('GHI CHÚ'),
            const SizedBox(height: 8),
            _sectionCard(child: Text(_plan!.notes!)),
          ],
          const SizedBox(height: 16),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                _error!,
                style: const TextStyle(color: AppColors.error),
              ),
            ),
          ElevatedButton.icon(
            onPressed: _openDrugEditor,
            icon: const Icon(Icons.edit_note_rounded),
            label: const Text('Chỉnh sửa thuốc và lịch'),
          ),
          const SizedBox(height: 8),
          if (_plan!.isActive)
            OutlinedButton.icon(
              onPressed: _deactivate,
              icon: const Icon(
                Icons.pause_circle_outline,
                color: AppColors.error,
              ),
              label: const Text(
                'Kết thúc kế hoạch',
                style: TextStyle(color: AppColors.error),
              ),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppColors.error),
              ),
            )
          else
            OutlinedButton.icon(
              onPressed: _reactivate,
              icon: const Icon(
                Icons.play_circle_outline,
                color: AppColors.success,
              ),
              label: const Text(
                'Kích hoạt lại',
                style: TextStyle(color: AppColors.success),
              ),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppColors.success),
              ),
            ),
        ],
      ),
    );
  }

  Widget _sectionCard({required Widget child, EdgeInsetsGeometry? margin}) {
    return Container(
      margin: margin,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.surfaceHigh),
      ),
      child: child,
    );
  }

  Widget _pill(String label, Color color) {
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
          fontWeight: FontWeight.w700,
          fontSize: 12,
        ),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }

  Widget _sectionLabel(String text) => Text(
    text,
    style: const TextStyle(
      color: AppColors.textMuted,
      fontSize: 12,
      fontWeight: FontWeight.w700,
      letterSpacing: 1.1,
    ),
  );
}

class _StepperField extends StatelessWidget {
  const _StepperField({
    required this.label,
    required this.value,
    required this.onMinus,
    required this.onPlus,
  });

  final String label;
  final int value;
  final VoidCallback? onMinus;
  final VoidCallback? onPlus;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.surfaceHigh),
      ),
      child: Column(
        children: [
          Text(label, style: const TextStyle(color: AppColors.textSecondary)),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              IconButton(
                onPressed: onMinus,
                icon: const Icon(Icons.remove_circle_outline),
              ),
              Text(
                '$value',
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
              IconButton(
                onPressed: onPlus,
                icon: const Icon(Icons.add_circle_outline),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
