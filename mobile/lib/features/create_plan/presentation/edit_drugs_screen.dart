import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../domain/plan.dart';
import 'widgets/drug_entry_sheet.dart';

/// Screen: Nhập tay hoặc chỉnh sửa nâng cao danh sách thuốc → lập lịch.
/// Vai trò còn lại: nhập tay từ đầu (từ /create/edit không có initial drugs)
/// hoặc chỉnh sửa nâng cao trước khi lập lịch.
class EditDrugsScreen extends ConsumerStatefulWidget {
  /// Pre-filled drugs từ OCR hoặc trống cho nhập tay.
  final List<PlanDrugItem> initialDrugs;

  const EditDrugsScreen({super.key, this.initialDrugs = const []});

  @override
  ConsumerState<EditDrugsScreen> createState() => _EditDrugsScreenState();
}

class _EditDrugsScreenState extends ConsumerState<EditDrugsScreen> {
  late List<PlanDrugItem> _drugs;

  @override
  void initState() {
    super.initState();
    _drugs = List.from(widget.initialDrugs);
  }

  // -------------------------------------------------------------------------
  // Add drug — with DB search suggestion
  // -------------------------------------------------------------------------

  Future<void> _addDrug() async {
    final result = await showModalBottomSheet<PlanDrugItem?>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => DrugEntrySheet(ref: ref),
    );
    if (result != null) {
      setState(() => _drugs.add(result));
    }
  }

  // -------------------------------------------------------------------------
  // Edit drug — with DB search suggestion
  // -------------------------------------------------------------------------

  Future<void> _editDrug(int index) async {
    final current = _drugs[index];
    final result = await showModalBottomSheet<PlanDrugItem?>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => DrugEntrySheet(ref: ref, initial: current),
    );
    if (result != null) {
      setState(() => _drugs[index] = result);
    }
  }

  void _removeDrug(int index) {
    setState(() => _drugs.removeAt(index));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Danh sách thuốc'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/create'),
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _addDrug,
        backgroundColor: AppColors.primary,
        tooltip: 'Thêm thuốc',
        child: const Icon(Icons.add),
      ),
      body: Column(
        children: [
          // Drug list
          Expanded(
            child: _drugs.isEmpty
                ? _buildEmpty()
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _drugs.length,
                    itemBuilder: (ctx, i) => _buildDrugCard(i),
                  ),
          ),

          // Bottom action
          Padding(
            padding: const EdgeInsets.all(16),
            child: ElevatedButton(
              onPressed: _drugs.isEmpty
                  ? null
                  : () => context.go('/create/schedule', extra: _drugs),
              style: ElevatedButton.styleFrom(
                minimumSize: const Size.fromHeight(50),
              ),
              child: Text('Tiếp tục — ${_drugs.length} thuốc'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmpty() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.medication_outlined, size: 56, color: AppColors.textMuted),
          const SizedBox(height: 12),
          Text(
            'Chưa có thuốc nào',
            style: TextStyle(color: AppColors.textMuted, fontSize: 16),
          ),
          const SizedBox(height: 8),
          Text(
            'Bấm + để thêm thuốc',
            style: TextStyle(color: AppColors.textMuted, fontSize: 13),
          ),
        ],
      ),
    );
  }

  Widget _buildDrugCard(int index) {
    final drug = _drugs[index];
    return Card(
      color: AppColors.surface,
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: AppColors.primary.withValues(alpha: 0.15),
          child: Icon(Icons.medication, color: AppColors.primary, size: 20),
        ),
        title: Text(
          drug.name,
          style: const TextStyle(fontWeight: FontWeight.w500),
        ),
        subtitle: drug.dosage.isNotEmpty
            ? Text(
                drug.dosage,
                style: TextStyle(color: AppColors.textSecondary),
              )
            : null,
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              icon: const Icon(Icons.edit_outlined, size: 20),
              onPressed: () => _editDrug(index),
            ),
            IconButton(
              icon: Icon(
                Icons.delete_outline,
                size: 20,
                color: AppColors.error,
              ),
              onPressed: () => _removeDrug(index),
            ),
          ],
        ),
      ),
    );
  }
}
