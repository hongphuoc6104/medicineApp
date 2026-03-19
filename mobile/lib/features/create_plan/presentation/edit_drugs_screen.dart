import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../domain/plan.dart';

/// Screen: edit drug list after scan/manual → next step: set schedule.
class EditDrugsScreen extends ConsumerStatefulWidget {
  /// Pre-filled drugs from OCR or empty for manual input.
  final List<PlanDrugItem> initialDrugs;

  const EditDrugsScreen({super.key, this.initialDrugs = const []});

  @override
  ConsumerState<EditDrugsScreen> createState() => _EditDrugsScreenState();
}

class _EditDrugsScreenState extends ConsumerState<EditDrugsScreen> {
  late List<PlanDrugItem> _drugs;
  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _drugs = List.from(widget.initialDrugs);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _addDrug() {
    showDialog(
      context: context,
      builder: (ctx) {
        final nameCtrl = TextEditingController();
        final dosageCtrl = TextEditingController();
        return AlertDialog(
          title: const Text('Thêm thuốc'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameCtrl,
                autofocus: true,
                decoration: const InputDecoration(
                  hintText: 'Tên thuốc *',
                  prefixIcon: Icon(Icons.medication),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: dosageCtrl,
                decoration: const InputDecoration(
                  hintText: 'Liều (VD: 500mg)',
                  prefixIcon: Icon(Icons.scale),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Hủy'),
            ),
            ElevatedButton(
              onPressed: () {
                final name = nameCtrl.text.trim();
                if (name.isEmpty) return;
                setState(() {
                  _drugs.add(PlanDrugItem(
                    name: name,
                    dosage: dosageCtrl.text.trim(),
                  ));
                });
                Navigator.pop(ctx);
              },
              child: const Text('Thêm'),
            ),
          ],
        );
      },
    );
  }

  void _editDrug(int index) {
    final drug = _drugs[index];
    final nameCtrl = TextEditingController(text: drug.name);
    final dosageCtrl = TextEditingController(text: drug.dosage);

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Sửa thuốc'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameCtrl,
              decoration: const InputDecoration(
                hintText: 'Tên thuốc',
                prefixIcon: Icon(Icons.medication),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: dosageCtrl,
              decoration: const InputDecoration(
                hintText: 'Liều (VD: 500mg)',
                prefixIcon: Icon(Icons.scale),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Hủy'),
          ),
          ElevatedButton(
            onPressed: () {
              final name = nameCtrl.text.trim();
              if (name.isEmpty) return;
              setState(() {
                _drugs[index].name = name;
                _drugs[index].dosage = dosageCtrl.text.trim();
              });
              Navigator.pop(ctx);
            },
            child: const Text('Lưu'),
          ),
        ],
      ),
    );
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
            'Bấm + để thêm thuốc thủ công',
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
        title: Text(drug.name, style: const TextStyle(fontWeight: FontWeight.w500)),
        subtitle: drug.dosage.isNotEmpty
            ? Text(drug.dosage, style: TextStyle(color: AppColors.textSecondary))
            : null,
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              icon: const Icon(Icons.edit_outlined, size: 20),
              onPressed: () => _editDrug(index),
            ),
            IconButton(
              icon: Icon(Icons.delete_outline, size: 20, color: AppColors.error),
              onPressed: () => _removeDrug(index),
            ),
          ],
        ),
      ),
    );
  }
}
