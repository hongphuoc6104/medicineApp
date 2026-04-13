import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../core/theme/app_theme.dart';
import '../../create_plan/data/plan_repository.dart';
import '../../create_plan/domain/plan.dart';
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
      _applyPlan(plan);
      setState(() {
        _plan = plan;
        _isLoading = false;
      });
    } catch (e) {
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
        return StatefulBuilder(
          builder: (ctx, setModalState) {
            return SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
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
                    ...draft.asMap().entries.map((entry) {
                      final idx = entry.key;
                      final value = entry.value;
                      return ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.access_time),
                        title: Text(value),
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
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        OutlinedButton.icon(
                          onPressed: draft.length < 4
                              ? () => setModalState(() => draft.add('21:00'))
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
          'Ke hoach se duoc ngung kich hoat va khong nhac nua.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Huy'),
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
        appBar: AppBar(title: const Text('Chi tiết kế hoạch')),
        body: Center(child: Text(_error ?? 'Không tải được kế hoạch')),
      );
    }

    if (_plan!.drugs.length > 1) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Chi tiết kế hoạch'),
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
            Text(
              _plan!.drugName,
              style: Theme.of(
                context,
              ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 8),
            Text(
              'Từ ${DateFormat('dd/MM/yyyy').format(_startDate)} • $_totalDays ngày',
              style: const TextStyle(color: AppColors.textSecondary),
            ),
            const SizedBox(height: 16),
            _sectionLabel('THUỐC TRONG KẾ HOẠCH'),
            const SizedBox(height: 8),
            ..._plan!.drugs.map(
              (drug) => ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.medication_outlined),
                title: Text(drug.drugName),
                subtitle: drug.dosage != null ? Text(drug.dosage!) : null,
              ),
            ),
            const SizedBox(height: 16),
            _sectionLabel('LỊCH UỐNG'),
            const SizedBox(height: 8),
            ..._plan!.slots.map(
              (slot) => Container(
                margin: const EdgeInsets.only(bottom: 12),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppColors.surfaceHigh),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      slot.time,
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 8),
                    ...slot.items.map(
                      (item) => Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Text('${item.drugName}: ${item.pills} viên'),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            if ((_plan!.notes ?? '').trim().isNotEmpty) ...[
              const SizedBox(height: 8),
              _sectionLabel('GHI CHÚ'),
              const SizedBox(height: 8),
              Text(_plan!.notes!),
            ],
            const SizedBox(height: 12),
            ElevatedButton.icon(
              onPressed: _openDrugEditor,
              icon: const Icon(Icons.edit_note_rounded),
              label: const Text('Chỉnh sửa thuốc và lịch'),
            ),
            const SizedBox(height: 20),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                  _error!,
                  style: const TextStyle(color: AppColors.error),
                ),
              ),
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

    return Scaffold(
      appBar: AppBar(
        title: const Text('Chi tiết kế hoạch'),
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
          TextField(
            controller: _drugCtrl,
            decoration: const InputDecoration(
              labelText: 'Tên thuốc',
              prefixIcon: Icon(Icons.medication_outlined),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _dosageCtrl,
            decoration: const InputDecoration(
              labelText: 'Liều lượng',
              prefixIcon: Icon(Icons.scale_outlined),
            ),
          ),
          const SizedBox(height: 16),
          _sectionLabel('TẦN SUẤT'),
          const SizedBox(height: 8),
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'daily', label: Text('1 lần')),
              ButtonSegment(value: 'twice_daily', label: Text('2 lần')),
              ButtonSegment(value: 'three_daily', label: Text('3 lần')),
            ],
            selected: {_frequency},
            onSelectionChanged: (value) => setState(() {
              _frequency = value.first;
              switch (_frequency) {
                case 'daily':
                  _times = ['07:00'];
                  break;
                case 'twice_daily':
                  _times = ['07:00', '19:00'];
                  break;
                case 'three_daily':
                  _times = ['07:00', '12:00', '19:00'];
                  break;
              }
              _syncDoseScheduleWithTimes();
            }),
          ),
          const SizedBox(height: 16),
          InkWell(
            onTap: _editTimes,
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.surfaceHigh),
              ),
              child: Row(
                children: [
                  const Icon(Icons.access_time),
                  const SizedBox(width: 10),
                  Expanded(child: Text(_times.join(', '))),
                  const Icon(Icons.chevron_right),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child:
                    _doseSchedule.map((item) => item.pills).toSet().length > 1
                    ? Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppColors.surface,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppColors.surfaceHigh),
                        ),
                        child: Column(
                          children: [
                            const Text(
                              'Số viên theo từng giờ',
                              style: TextStyle(color: AppColors.textSecondary),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              _doseSchedule
                                  .map(
                                    (item) =>
                                        '${item.time}: ${item.pills} viên',
                                  )
                                  .join(' · '),
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                      )
                    : _StepperField(
                        label: 'Viên/lần',
                        value: _pillsPerDose,
                        onMinus: _pillsPerDose > 1
                            ? () => setState(() {
                                _pillsPerDose--;
                                _doseSchedule = _doseSchedule
                                    .map(
                                      (item) =>
                                          item.copyWith(pills: _pillsPerDose),
                                    )
                                    .toList();
                              })
                            : null,
                        onPlus: _pillsPerDose < 20
                            ? () => setState(() {
                                _pillsPerDose++;
                                _doseSchedule = _doseSchedule
                                    .map(
                                      (item) =>
                                          item.copyWith(pills: _pillsPerDose),
                                    )
                                    .toList();
                              })
                            : null,
                      ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _StepperField(
                  label: 'Số ngày',
                  value: _totalDays,
                  onMinus: _totalDays > 1
                      ? () => setState(() => _totalDays--)
                      : null,
                  onPlus: _totalDays < 365
                      ? () => setState(() => _totalDays++)
                      : null,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          InkWell(
            onTap: _pickStartDate,
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.surfaceHigh),
              ),
              child: Row(
                children: [
                  const Icon(Icons.calendar_month_outlined),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(DateFormat('dd/MM/yyyy').format(_startDate)),
                  ),
                  const Icon(Icons.chevron_right),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _notesCtrl,
            minLines: 2,
            maxLines: 4,
            decoration: const InputDecoration(
              labelText: 'Ghi chú',
              alignLabelWithHint: true,
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: AppColors.error)),
          ],
          const SizedBox(height: 20),
          ElevatedButton.icon(
            onPressed: _isSaving ? null : _save,
            icon: _isSaving
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.save_outlined),
            label: const Text('Lưu thay đổi'),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
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
