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

  void _applyPlan(Plan plan) {
    _drugCtrl.text = plan.drugName;
    _dosageCtrl.text = plan.dosage ?? '';
    _notesCtrl.text = plan.notes ?? '';
    _frequency = plan.frequency;
    _times = List<String>.from(plan.times.isEmpty ? ['07:00'] : plan.times);
    _pillsPerDose = plan.pillsPerDose;
    _totalDays = plan.totalDays ?? 7;
    _startDate = DateTime.tryParse(plan.startDate) ?? DateTime.now();
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
                      'Chon gio uong',
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
                          label: const Text('Them gio'),
                        ),
                        const Spacer(),
                        ElevatedButton(
                          onPressed: () {
                            setState(() => _times = draft);
                            Navigator.pop(ctx);
                          },
                          child: const Text('Luu'),
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
      setState(() => _error = 'Ten thuoc khong duoc de trong');
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
        PlanDrugItem(
          name: _drugCtrl.text.trim(),
          dosage: _dosageCtrl.text.trim(),
          pillsPerDose: _pillsPerDose,
          frequency: _frequency,
          times: _times,
          totalDays: _totalDays,
          notes: _notesCtrl.text.trim(),
        ),
        DateFormat('yyyy-MM-dd').format(_startDate),
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
      ).showSnackBar(const SnackBar(content: Text('Da cap nhat ke hoach')));
    } on DioException catch (e) {
      setState(() {
        _isSaving = false;
        _error = e.message ?? 'Khong luu duoc ke hoach';
      });
    } catch (e) {
      setState(() {
        _isSaving = false;
        _error = e.toString();
      });
    }
  }

  Future<void> _deactivate() async {
    final current = _plan;
    if (current == null) return;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Ket thuc ke hoach?'),
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
            child: const Text('Ket thuc'),
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
      ).showSnackBar(const SnackBar(content: Text('Da ket thuc ke hoach')));
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
        const SnackBar(content: Text('Da kich hoat lai ke hoach')),
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
        appBar: AppBar(title: const Text('Chi tiet ke hoach')),
        body: Center(child: Text(_error ?? 'Khong tai duoc ke hoach')),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Chi tiet ke hoach')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          TextField(
            controller: _drugCtrl,
            decoration: const InputDecoration(
              labelText: 'Ten thuoc',
              prefixIcon: Icon(Icons.medication_outlined),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _dosageCtrl,
            decoration: const InputDecoration(
              labelText: 'Lieu luong',
              prefixIcon: Icon(Icons.scale_outlined),
            ),
          ),
          const SizedBox(height: 16),
          _sectionLabel('TAN SUAT'),
          const SizedBox(height: 8),
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'daily', label: Text('1 lan')),
              ButtonSegment(value: 'twice_daily', label: Text('2 lan')),
              ButtonSegment(value: 'three_daily', label: Text('3 lan')),
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
                child: _StepperField(
                  label: 'Vien/lan',
                  value: _pillsPerDose,
                  onMinus: _pillsPerDose > 1
                      ? () => setState(() => _pillsPerDose--)
                      : null,
                  onPlus: _pillsPerDose < 20
                      ? () => setState(() => _pillsPerDose++)
                      : null,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _StepperField(
                  label: 'So ngay',
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
              labelText: 'Ghi chu',
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
            label: const Text('Luu thay doi'),
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
                'Ket thuc ke hoach',
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
                'Kich hoat lai',
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
