import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../core/notifications/notification_service.dart';
import '../../../core/theme/app_theme.dart';
import '../../home/data/plan_notifier.dart';
import '../../settings/data/settings_repository.dart';
import '../data/plan_repository.dart';
import '../domain/plan.dart';

class SetScheduleScreen extends ConsumerStatefulWidget {
  const SetScheduleScreen({super.key, required this.drugs});

  final List<PlanDrugItem> drugs;

  @override
  ConsumerState<SetScheduleScreen> createState() => _SetScheduleScreenState();
}

class _SetScheduleScreenState extends ConsumerState<SetScheduleScreen> {
  late DateTime _startDate;
  late DateTime _endDate;
  int _currentIndex = 0;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _startDate = DateTime.now();
    final firstDays = widget.drugs.isEmpty ? 7 : widget.drugs.first.totalDays;
    _endDate = _startDate.add(Duration(days: firstDays - 1));
  }

  PlanDrugItem get _currentDrug => widget.drugs[_currentIndex];

  String get _startDateStr => DateFormat('yyyy-MM-dd').format(_startDate);

  Future<void> _pickDate({required bool isStart}) async {
    final initial = isStart ? _startDate : _endDate;
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime.now().subtract(const Duration(days: 7)),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked == null) return;
    setState(() {
      if (isStart) {
        _startDate = picked;
        if (_endDate.isBefore(_startDate)) {
          _endDate = _startDate;
        }
      } else {
        _endDate = picked;
      }
      final totalDays = _endDate.difference(_startDate).inDays + 1;
      _currentDrug.totalDays = totalDays < 1 ? 1 : totalDays;
    });
  }

  Future<void> _pickTime(int index) async {
    final parts = _currentDrug.times[index].split(':');
    final picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay(
        hour: int.tryParse(parts.first) ?? 8,
        minute: int.tryParse(parts.last) ?? 0,
      ),
    );
    if (picked == null) return;
    setState(() {
      _currentDrug.times[index] =
          '${picked.hour.toString().padLeft(2, '0')}:${picked.minute.toString().padLeft(2, '0')}';
    });
  }

  void _applyCurrentToAll() {
    final current = _currentDrug.copyWith();
    setState(() {
      for (var i = 0; i < widget.drugs.length; i++) {
        if (i == _currentIndex) continue;
        widget.drugs[i] = widget.drugs[i].copyWith(
          frequency: current.frequency,
          times: List<String>.from(current.times),
          pillsPerDose: current.pillsPerDose,
          totalDays: current.totalDays,
          notes: current.notes,
        );
      }
      _endDate = _startDate.add(Duration(days: current.totalDays - 1));
    });
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Da ap dung lich uong cho toan bo don thuoc'),
      ),
    );
  }

  void _setFrequency(String value) {
    setState(() {
      _currentDrug.frequency = value;
      switch (value) {
        case 'daily':
          _currentDrug.times = ['08:00'];
          break;
        case 'twice_daily':
          _currentDrug.times = ['08:00', '17:00'];
          break;
        case 'three_daily':
          _currentDrug.times = ['08:00', '12:00', '18:00'];
          break;
      }
    });
  }

  Future<void> _savePlans() async {
    setState(() => _isSaving = true);
    try {
      final repo = ref.read(planRepositoryProvider);
      final notificationService = ref.read(notificationServiceProvider);
      final settingsRepo = ref.read(settingsRepositoryProvider);
      final remindersEnabled = await settingsRepo.getRemindersEnabled();
      for (final drug in widget.drugs) {
        final created = await repo.createPlan(drug, _startDateStr);
        if (remindersEnabled) {
          try {
            await notificationService.schedulePlanNotifications(created);
          } catch (e) {
            if (kDebugMode) {
              debugPrint(
                '[SetScheduleScreen] Notification scheduling failed: $e',
              );
            }
          }
        }
      }

      if (!mounted) return;
      ref.invalidate(planNotifierProvider);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Da tao ${widget.drugs.length} ke hoach uong thuoc'),
          backgroundColor: AppColors.success,
        ),
      );
      context.go('/home');
    } on DioException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            e.type == DioExceptionType.connectionError
                ? 'Khong ket noi duoc server'
                : 'Khong the luu ke hoach',
          ),
          backgroundColor: AppColors.error,
        ),
      );
      setState(() => _isSaving = false);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Loi: $e'), backgroundColor: AppColors.error),
      );
      setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final drug = _currentDrug;
    final isLast = _currentIndex == widget.drugs.length - 1;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dat lich uong thuoc'),
        leading: IconButton(
          onPressed: () => Navigator.pop(context),
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 120),
        children: [
          _HeaderStepper(
            currentIndex: _currentIndex,
            total: widget.drugs.length,
          ),
          const SizedBox(height: 18),
          _CardShell(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const _FieldLabel('Ten thuoc'),
                const SizedBox(height: 8),
                TextField(
                  controller: TextEditingController(text: drug.name),
                  readOnly: true,
                  decoration: const InputDecoration(
                    prefixIcon: Icon(Icons.medication_outlined),
                  ),
                ),
                const SizedBox(height: 18),
                const _FieldLabel('Ban dung thuoc trong bao lau?'),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: _DateCard(
                        label: 'Bat dau',
                        value: DateFormat('dd/MM').format(_startDate),
                        onTap: () => _pickDate(isStart: true),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _DateCard(
                        label: 'Ket thuc',
                        value: DateFormat('dd/MM').format(_endDate),
                        onTap: () => _pickDate(isStart: false),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                const _FieldLabel('Ban dung thuoc bao lau mot lan?'),
                const SizedBox(height: 10),
                SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(value: 'daily', label: Text('1 lan/ngay')),
                    ButtonSegment(
                      value: 'twice_daily',
                      label: Text('2 lan/ngay'),
                    ),
                    ButtonSegment(
                      value: 'three_daily',
                      label: Text('3 lan/ngay'),
                    ),
                  ],
                  selected: {drug.frequency},
                  onSelectionChanged: (values) => _setFrequency(values.first),
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: const [
                    _WeekChip(label: 'T2', selected: true),
                    _WeekChip(label: 'T3', selected: true),
                    _WeekChip(label: 'T4', selected: true),
                    _WeekChip(label: 'T5', selected: true),
                    _WeekChip(label: 'T6', selected: true),
                    _WeekChip(label: 'T7', selected: true),
                    _WeekChip(label: 'CN', selected: true),
                  ],
                ),
                const SizedBox(height: 14),
                OutlinedButton(
                  onPressed: _applyCurrentToAll,
                  child: const Text('Ap dung lich uong cho toan bo don thuoc'),
                ),
                const SizedBox(height: 18),
                const _FieldLabel('Ban hay dat gio uong thuoc'),
                const SizedBox(height: 10),
                ...drug.times.asMap().entries.map(
                  (entry) => _TimeRow(
                    time: entry.value,
                    onEdit: () => _pickTime(entry.key),
                  ),
                ),
                const SizedBox(height: 18),
                const _FieldLabel('Ban uong bao nhieu vien 1 lan?'),
                const SizedBox(height: 10),
                _DoseStepper(
                  value: drug.pillsPerDose,
                  onMinus: drug.pillsPerDose > 1
                      ? () => setState(() => drug.pillsPerDose--)
                      : null,
                  onPlus: drug.pillsPerDose < 10
                      ? () => setState(() => drug.pillsPerDose++)
                      : null,
                ),
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceSoft,
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: Text(
                    '${drug.pillsPerDose} vien x ${drug.times.length} lan/ngay, tu ${DateFormat('dd/MM').format(_startDate)} den ${DateFormat('dd/MM').format(_endDate)}',
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      color: AppColors.primaryDark,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      bottomNavigationBar: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 6, 20, 20),
          child: Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: _currentIndex > 0
                      ? () => setState(() => _currentIndex--)
                      : () => context.go('/create/edit', extra: widget.drugs),
                  child: Text(_currentIndex > 0 ? 'Thuoc truoc' : 'Quay lai'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: ElevatedButton(
                  onPressed: _isSaving
                      ? null
                      : () {
                          if (isLast) {
                            _savePlans();
                          } else {
                            setState(() => _currentIndex++);
                          }
                        },
                  child: _isSaving
                      ? const SizedBox(
                          height: 18,
                          width: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : Text(isLast ? 'Luu' : 'Thuoc sau'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _HeaderStepper extends StatelessWidget {
  const _HeaderStepper({required this.currentIndex, required this.total});

  final int currentIndex;
  final int total;

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
          Container(
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Icon(
              Icons.schedule_rounded,
              color: AppColors.primaryDark,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Dat lich cho tung thuoc',
                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 18),
                ),
                const SizedBox(height: 4),
                Text(
                  'Thuoc ${currentIndex + 1}/$total',
                  style: const TextStyle(color: AppColors.textSecondary),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _CardShell extends StatelessWidget {
  const _CardShell({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: AppColors.border),
      ),
      child: child,
    );
  }
}

class _FieldLabel extends StatelessWidget {
  const _FieldLabel(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Text(
      label,
      style: const TextStyle(
        fontWeight: FontWeight.w800,
        color: AppColors.textSecondary,
      ),
    );
  }
}

class _DateCard extends StatelessWidget {
  const _DateCard({
    required this.label,
    required this.value,
    required this.onTap,
  });

  final String label;
  final String value;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Ink(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.surfaceSoft,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: AppColors.border),
        ),
        child: Row(
          children: [
            const Icon(
              Icons.calendar_month_rounded,
              color: AppColors.primaryDark,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: const TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 12,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    value,
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _WeekChip extends StatelessWidget {
  const _WeekChip({required this.label, required this.selected});

  final String label;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 42,
      height: 42,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: selected ? AppColors.primary : AppColors.surfaceSoft,
        borderRadius: BorderRadius.circular(21),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: selected ? Colors.white : AppColors.textPrimary,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _TimeRow extends StatelessWidget {
  const _TimeRow({required this.time, required this.onEdit});

  final String time;
  final VoidCallback onEdit;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.surfaceSoft,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(
        children: [
          const Icon(Icons.access_time_rounded, color: AppColors.textMuted),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              time,
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
            ),
          ),
          IconButton(
            onPressed: onEdit,
            icon: const Icon(Icons.edit_rounded, color: AppColors.primaryDark),
          ),
        ],
      ),
    );
  }
}

class _DoseStepper extends StatelessWidget {
  const _DoseStepper({
    required this.value,
    required this.onMinus,
    required this.onPlus,
  });

  final int value;
  final VoidCallback? onMinus;
  final VoidCallback? onPlus;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        _StepButton(icon: Icons.remove_rounded, onTap: onMinus),
        const SizedBox(width: 10),
        Expanded(
          child: Container(
            height: 54,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: AppColors.surfaceSoft,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: AppColors.border),
            ),
            child: Text(
              '$value',
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900),
            ),
          ),
        ),
        const SizedBox(width: 10),
        _StepButton(icon: Icons.add_rounded, onTap: onPlus),
      ],
    );
  }
}

class _StepButton extends StatelessWidget {
  const _StepButton({required this.icon, required this.onTap});

  final IconData icon;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Ink(
        width: 54,
        height: 54,
        decoration: BoxDecoration(
          color: onTap == null ? AppColors.surfaceHigh : AppColors.surface,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: AppColors.border),
        ),
        child: Icon(
          icon,
          color: onTap == null ? AppColors.textMuted : AppColors.primaryDark,
        ),
      ),
    );
  }
}
