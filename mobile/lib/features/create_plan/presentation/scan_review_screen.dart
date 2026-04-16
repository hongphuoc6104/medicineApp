import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../../../l10n/app_localizations.dart';
import '../domain/plan.dart';
import '../domain/scan_result.dart';
import 'widgets/drug_entry_sheet.dart';

class ScanReviewScreen extends ConsumerStatefulWidget {
  const ScanReviewScreen({super.key, required this.result});

  final ScanResult result;

  @override
  ConsumerState<ScanReviewScreen> createState() => _ScanReviewScreenState();
}

class _ScanReviewScreenState extends ConsumerState<ScanReviewScreen> {
  late List<DetectedDrug> _drugs;
  final _searchCtrl = TextEditingController();

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
      final haystack = '${drug.name} ${drug.ocrText}'.toLowerCase();
      return q.isEmpty || haystack.contains(q);
    }).toList()..sort((a, b) {
      if (a.needsReview && !b.needsReview) return -1;
      if (!a.needsReview && b.needsReview) return 1;
      return 0;
    });
  }

  void _removeDrug(DetectedDrug drug) {
    setState(() => _drugs.remove(drug));
  }

  Future<void> _editDrug(DetectedDrug drug) async {
    final current = drug;
    final initial = PlanDrugItem(
      name: current.name,
      dosage: current.dosage ?? '',
    );

    final result = await showModalBottomSheet<PlanDrugItem?>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => DrugEntrySheet(ref: ref, initial: initial),
    );

    if (result != null) {
      final index = _drugs.indexOf(current);
      if (index >= 0) {
        setState(() {
          _drugs[index] = DetectedDrug(
            name: result.name,
            dosage: result.dosage,
            confidence: current.confidence,
            matchScore: current.matchScore,
            mappingStatus: 'confirmed',
            ocrText: current.ocrText,
            mappedDrugName: result.name,
            frequency: current.frequency,
            sources: current.sources,
          );
        });
      }
    }
  }

  Future<void> _addDrugManually() async {
    final result = await showModalBottomSheet<PlanDrugItem?>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => DrugEntrySheet(ref: ref),
    );

    if (result != null) {
      setState(() {
        _drugs.add(
          DetectedDrug(
            name: result.name,
            dosage: result.dosage,
            mappingStatus: 'confirmed',
            confidence: 1.0,
          ),
        );
      });
    }
  }

  void _continue() {
    final items = _drugs
        .map((d) => PlanDrugItem(name: d.name, dosage: d.dosage ?? ''))
        .toList();
    // Skip edit_drugs step — go directly to schedule (plan §6.4, §8.1)
    context.go('/create/schedule', extra: items);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final visible = _visibleDrugs;

    return Scaffold(
      appBar: AppBar(title: Text(l10n.scanReviewTitle)),
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
                  widget.result.guidance ?? l10n.scanReviewDefaultGuidance,
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _StatusChip(
                      label: l10n.scanReviewDrugCount(_drugs.length),
                      color: AppColors.primary,
                    ),
                    if ((widget.result.guidance ?? '').isNotEmpty)
                      _StatusChip(
                        label: 'Gợi ý: ${widget.result.guidance}',
                        color: AppColors.info,
                      ),
                  ],
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _searchCtrl,
                  onChanged: (_) => setState(() {}),
                  decoration: InputDecoration(
                    hintText: 'Tìm thuốc trong danh sách',
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: _searchCtrl.text.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.clear),
                            onPressed: () {
                              _searchCtrl.clear();
                              setState(() {});
                            },
                          )
                        : null,
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: visible.isEmpty
                ? Center(
                    child: Text(
                      l10n.scanReviewEmptyFilter,
                      style: const TextStyle(color: AppColors.textSecondary),
                    ),
                  )
                : ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                    itemCount: visible.length,
                    separatorBuilder: (context, index) =>
                        const SizedBox(height: 10),
                    itemBuilder: (context, index) {
                      final drug = visible[index];
                      final hasDbSuggestion =
                          drug.mappedDrugName != null &&
                          drug.mappedDrugName!.isNotEmpty &&
                          drug.mappedDrugName!.toLowerCase().trim() !=
                              drug.name.toLowerCase().trim();
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
                                      fontSize: 15,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            if (hasDbSuggestion) ...[
                              const SizedBox(height: 4),
                              Row(
                                children: [
                                  const Icon(
                                    Icons.info_outline,
                                    size: 14,
                                    color: AppColors.info,
                                  ),
                                  const SizedBox(width: 4),
                                  Expanded(
                                    child: Text(
                                      l10n.scanReviewStandardName(
                                        drug.mappedDrugName!,
                                      ),
                                      style: const TextStyle(
                                        color: AppColors.info,
                                        fontSize: 12,
                                      ),
                                      overflow: TextOverflow.ellipsis,
                                      maxLines: 1,
                                    ),
                                  ),
                                ],
                              ),
                            ],
                            if (drug.ocrText.isNotEmpty &&
                                drug.ocrText.toLowerCase().trim() !=
                                    drug.name.toLowerCase().trim()) ...[
                              const SizedBox(height: 4),
                              Text(
                                'OCR: ${drug.ocrText}',
                                style: const TextStyle(
                                  color: AppColors.textSecondary,
                                  fontSize: 12,
                                ),
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ],
                            const SizedBox(height: 10),
                            Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              children: [
                                OutlinedButton.icon(
                                  onPressed: () => _editDrug(drug),
                                  icon: const Icon(
                                    Icons.edit_outlined,
                                    size: 16,
                                  ),
                                  label: Text(l10n.scanReviewEdit),
                                ),
                                OutlinedButton.icon(
                                  onPressed: () => _removeDrug(drug),
                                  style: OutlinedButton.styleFrom(
                                    foregroundColor: AppColors.error,
                                  ),
                                  icon: const Icon(
                                    Icons.delete_outline,
                                    size: 16,
                                  ),
                                  label: Text(l10n.scanReviewRemove),
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
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _addDrugManually,
                        icon: const Icon(Icons.add, size: 18),
                        label: Text(l10n.scanReviewAddDrug),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => context.go('/create/scan'),
                        icon: const Icon(
                          Icons.document_scanner_outlined,
                          size: 18,
                        ),
                        label: Text(l10n.scanReviewRescan),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                ElevatedButton.icon(
                  onPressed: _drugs.isEmpty ? null : _continue,
                  icon: const Icon(Icons.arrow_forward),
                  label: Text(l10n.scanReviewContinue(_drugs.length)),
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size.fromHeight(50),
                  ),
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
