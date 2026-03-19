import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../../drug/data/drug_repository.dart';
import '../domain/plan.dart';
import '../domain/scan_result.dart';

class ScanReviewScreen extends ConsumerStatefulWidget {
  const ScanReviewScreen({super.key, required this.result});

  final ScanResult result;

  @override
  ConsumerState<ScanReviewScreen> createState() => _ScanReviewScreenState();
}

class _ScanReviewScreenState extends ConsumerState<ScanReviewScreen> {
  late List<DetectedDrug> _drugs;
  final _searchCtrl = TextEditingController();
  bool _onlyNeedsReview = false;

  @override
  void initState() {
    super.initState();
    _drugs = List<DetectedDrug>.from(widget.result.drugs);
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  List<DetectedDrug> get _visibleDrugs {
    final q = _searchCtrl.text.trim().toLowerCase();
    return _drugs.where((drug) {
      final matchesReview = !_onlyNeedsReview || drug.needsReview;
      final haystack = '${drug.name} ${drug.ocrText}'.toLowerCase();
      final matchesSearch = q.isEmpty || haystack.contains(q);
      return matchesReview && matchesSearch;
    }).toList();
  }

  void _removeDrug(DetectedDrug drug) {
    setState(() => _drugs.remove(drug));
  }

  void _replaceDrug(DetectedDrug target, String newName) {
    final index = _drugs.indexOf(target);
    if (index < 0) return;
    final current = _drugs[index];
    setState(() {
      _drugs[index] = DetectedDrug(
        name: newName,
        dosage: current.dosage,
        confidence: current.confidence,
        matchScore: current.matchScore,
        mappingStatus: 'confirmed',
        ocrText: current.ocrText,
        mappedDrugName: newName,
        frequency: current.frequency,
        sources: current.sources,
      );
    });
  }

  void _editDrug(DetectedDrug drug) {
    final current = drug;
    final ctrl = TextEditingController(text: current.name);
    final dosageCtrl = TextEditingController(text: current.dosage ?? '');
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Xac nhan ten thuoc'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: ctrl,
              decoration: const InputDecoration(labelText: 'Ten thuoc'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: dosageCtrl,
              decoration: const InputDecoration(labelText: 'Lieu luong'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Huy'),
          ),
          ElevatedButton(
            onPressed: () {
              final index = _drugs.indexOf(current);
              if (index >= 0) {
                setState(() {
                  _drugs[index] = DetectedDrug(
                    name: ctrl.text.trim().isEmpty
                        ? current.name
                        : ctrl.text.trim(),
                    dosage: dosageCtrl.text.trim(),
                    confidence: current.confidence,
                    matchScore: current.matchScore,
                    mappingStatus: 'confirmed',
                    ocrText: current.ocrText,
                    mappedDrugName: current.mappedDrugName,
                    frequency: current.frequency,
                    sources: current.sources,
                  );
                });
              }
              Navigator.pop(ctx);
            },
            child: const Text('Luu'),
          ),
        ],
      ),
    );
  }

  Future<void> _findCorrectDrug(DetectedDrug drug) async {
    final repo = ref.read(drugRepositoryProvider);
    final ctrl = TextEditingController(text: drug.name);
    List<DrugSearchItem> results = [];
    bool loading = false;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setModalState) {
            Future<void> runSearch(String query) async {
              if (query.trim().length < 2) {
                setModalState(() => results = []);
                return;
              }
              setModalState(() => loading = true);
              try {
                final page = await repo.search(query.trim(), limit: 8);
                setModalState(() {
                  results = page.items;
                  loading = false;
                });
              } catch (_) {
                setModalState(() => loading = false);
              }
            }

            return SafeArea(
              child: Padding(
                padding: EdgeInsets.only(
                  left: 16,
                  right: 16,
                  top: 16,
                  bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextField(
                      controller: ctrl,
                      autofocus: true,
                      onChanged: runSearch,
                      decoration: const InputDecoration(
                        hintText: 'Tim thuoc dung...',
                        prefixIcon: Icon(Icons.search),
                      ),
                    ),
                    const SizedBox(height: 12),
                    SizedBox(
                      height: 320,
                      child: loading
                          ? const Center(child: CircularProgressIndicator())
                          : results.isEmpty
                          ? const Center(
                              child: Text(
                                'Nhap it nhat 2 ky tu de tim trong co so du lieu thuoc',
                                textAlign: TextAlign.center,
                              ),
                            )
                          : ListView.separated(
                              itemCount: results.length,
                              separatorBuilder: (context, index) =>
                                  const Divider(height: 1),
                              itemBuilder: (context, index) {
                                final item = results[index];
                                return ListTile(
                                  title: Text(item.name),
                                  subtitle: Text(
                                    item.activeIngredient ??
                                        'Khong ro hoat chat',
                                  ),
                                  trailing: Text(item.score.toStringAsFixed(2)),
                                  onTap: () {
                                    _replaceDrug(drug, item.name);
                                    Navigator.pop(ctx);
                                  },
                                );
                              },
                            ),
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

  void _continue() {
    final items = _drugs
        .map((d) => PlanDrugItem(name: d.name, dosage: d.dosage ?? ''))
        .toList();
    context.go('/create/edit', extra: items);
  }

  @override
  Widget build(BuildContext context) {
    final needsReviewCount = _drugs.where((d) => d.needsReview).length;
    final visible = _visibleDrugs;

    return Scaffold(
      appBar: AppBar(title: const Text('Xac nhan ket qua quet')),
      body: Column(
        children: [
          Container(
            width: double.infinity,
            margin: const EdgeInsets.all(16),
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppColors.surfaceHigh),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.result.guidance ??
                      'Kiem tra danh sach thuoc truoc khi lap lich.',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _StatusChip(
                      label: 'Chat luong: ${widget.result.qualityState}',
                      color: widget.result.qualityState == 'GOOD'
                          ? AppColors.success
                          : AppColors.warning,
                    ),
                    _StatusChip(
                      label: '${_drugs.length} thuoc',
                      color: AppColors.primary,
                    ),
                    if (needsReviewCount > 0)
                      _StatusChip(
                        label: '$needsReviewCount can kiem tra',
                        color: AppColors.warning,
                      ),
                  ],
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _searchCtrl,
                  onChanged: (_) => setState(() {}),
                  decoration: InputDecoration(
                    hintText: 'Loc theo ten hoac OCR text',
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: IconButton(
                      icon: const Icon(Icons.clear),
                      onPressed: () {
                        _searchCtrl.clear();
                        setState(() {});
                      },
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                SwitchListTile.adaptive(
                  value: _onlyNeedsReview,
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Chi hien thuoc can review'),
                  subtitle: const Text(
                    'An cac thuoc da map chac de review nhanh hon',
                  ),
                  onChanged: (value) =>
                      setState(() => _onlyNeedsReview = value),
                ),
              ],
            ),
          ),
          Expanded(
            child: visible.isEmpty
                ? const Center(
                    child: Text(
                      'Khong co thuoc nao khop voi bo loc hien tai',
                      style: TextStyle(color: AppColors.textSecondary),
                    ),
                  )
                : ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                    itemCount: visible.length,
                    separatorBuilder: (context, index) =>
                        const SizedBox(height: 10),
                    itemBuilder: (context, index) {
                      final drug = visible[index];
                      final statusColor =
                          drug.mappingStatus == 'confirmed' && !drug.needsReview
                          ? AppColors.success
                          : AppColors.warning;
                      final statusLabel =
                          drug.mappingStatus == 'confirmed' && !drug.needsReview
                          ? 'Da map chac'
                          : drug.mappingStatus == 'confirmed'
                          ? 'Nen kiem tra'
                          : 'Chua map chac';
                      return Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: AppColors.surface,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: AppColors.surfaceHigh),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    drug.name,
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 8,
                                    vertical: 4,
                                  ),
                                  decoration: BoxDecoration(
                                    color: statusColor.withValues(alpha: 0.12),
                                    borderRadius: BorderRadius.circular(20),
                                  ),
                                  child: Text(
                                    statusLabel,
                                    style: TextStyle(
                                      color: statusColor,
                                      fontSize: 11,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 6),
                            Text(
                              drug.ocrText.isNotEmpty
                                  ? 'OCR: ${drug.ocrText}'
                                  : 'Khong co text goc',
                              style: const TextStyle(
                                color: AppColors.textSecondary,
                                fontSize: 12,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              children: [
                                _MetaChip(
                                  label:
                                      'Conf ${(drug.confidence * 100).round()}%',
                                ),
                                _MetaChip(
                                  label:
                                      'Match ${(drug.matchScore * 100).round()}%',
                                ),
                                if (drug.frequency > 1)
                                  _MetaChip(label: '${drug.frequency} anh'),
                              ],
                            ),
                            const SizedBox(height: 10),
                            Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              children: [
                                OutlinedButton.icon(
                                  onPressed: () => _editDrug(drug),
                                  icon: const Icon(Icons.edit_outlined),
                                  label: const Text('Sua'),
                                ),
                                OutlinedButton.icon(
                                  onPressed: () => _findCorrectDrug(drug),
                                  icon: const Icon(Icons.search),
                                  label: const Text('Tim dung'),
                                ),
                                OutlinedButton.icon(
                                  onPressed: () => _removeDrug(drug),
                                  icon: const Icon(
                                    Icons.delete_outline,
                                    color: AppColors.error,
                                  ),
                                  label: const Text(
                                    'Loai bo',
                                    style: TextStyle(color: AppColors.error),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      );
                    },
                  ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                OutlinedButton.icon(
                  onPressed: () =>
                      context.go('/create/edit', extra: const <PlanDrugItem>[]),
                  icon: const Icon(Icons.edit_note),
                  label: const Text('Nhap tay thay the'),
                ),
                const SizedBox(height: 8),
                ElevatedButton.icon(
                  onPressed: _drugs.isEmpty ? null : _continue,
                  icon: const Icon(Icons.arrow_forward),
                  label: const Text('Tiep tuc lap lich'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(label, style: TextStyle(color: color, fontSize: 12)),
    );
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.surfaceHigh,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(label, style: const TextStyle(fontSize: 11)),
    );
  }
}
