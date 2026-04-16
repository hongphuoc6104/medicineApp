import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/network/network_error_mapper.dart';
import '../../../core/theme/app_theme.dart';
import '../../../l10n/app_localizations.dart';
import '../../lookup/data/drug_interaction_repository.dart';
import '../data/plan_interaction_checker.dart';
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
  PlanInteractionSummary _interactionSummary = PlanInteractionSummary.empty();
  bool _isCheckingInteractions = false;
  String? _interactionError;
  int _interactionRequestId = 0;

  @override
  void initState() {
    super.initState();
    _drugs = List<DetectedDrug>.from(widget.result.drugs);
    _refreshInteractionSummary();
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
    _refreshInteractionSummary();
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
        _refreshInteractionSummary();
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
      _refreshInteractionSummary();
    }
  }

  Future<void> _continue() async {
    if (_interactionSummary.hasInteractions) {
      final proceed = await _showInteractionConfirmDialog();
      if (!proceed) {
        return;
      }
    }

    final items = _drugs
        .map((d) => PlanDrugItem(name: d.name, dosage: d.dosage ?? ''))
        .toList();
    if (!mounted) {
      return;
    }
    // Skip edit_drugs step — go directly to schedule (plan §6.4, §8.1)
    context.go('/create/schedule', extra: items);
  }

  Future<void> _refreshInteractionSummary() async {
    final requestId = ++_interactionRequestId;
    setState(() {
      _isCheckingInteractions = true;
      _interactionError = null;
    });

    try {
      final checker = ref.read(planInteractionCheckerProvider);
      final summary = await checker.checkDetectedDrugs(_drugs);
      if (!mounted || requestId != _interactionRequestId) {
        return;
      }
      setState(() {
        _interactionSummary = summary;
        _isCheckingInteractions = false;
      });
    } catch (e) {
      if (!mounted || requestId != _interactionRequestId) {
        return;
      }
      setState(() {
        _isCheckingInteractions = false;
        _interactionError = toFriendlyNetworkMessage(
          e,
          genericMessage:
              'Không thể kiểm tra tương tác thuốc lúc này. Vui lòng thử lại.',
        );
      });
    }
  }

  String? _severityForDrug(DetectedDrug drug) {
    return _interactionSummary.severityForDrugName(drug.name);
  }

  Future<bool> _showInteractionConfirmDialog() async {
    final l10n = AppLocalizations.of(context);
    final severity = _severityLabel(l10n, _interactionSummary.highestSeverity);

    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Xác nhận tiếp tục dù có tương tác?'),
        content: Text(
          'Phát hiện ${_interactionSummary.totalInteractions} cặp tương tác '
          '(mức cao nhất: $severity). '
          'Bạn nên kiểm tra lại danh sách thuốc trước khi lập lịch.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: Text(l10n.commonCancel),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Vẫn tiếp tục lập lịch'),
          ),
        ],
      ),
    );

    return result == true;
  }

  String _severityLabel(AppLocalizations l10n, String severity) {
    switch (severity) {
      case 'contraindicated':
        return l10n.lookupSeverityContraindicated;
      case 'major':
        return l10n.lookupSeverityMajor;
      case 'moderate':
        return l10n.lookupSeverityModerate;
      case 'minor':
        return l10n.lookupSeverityMinor;
      case 'caution':
        return l10n.lookupSeverityCaution;
      default:
        return l10n.lookupSeverityUnknown;
    }
  }

  String _interactionPairLabel(InteractionItem item) {
    final first = item.drugA.trim().isNotEmpty
        ? item.drugA.trim()
        : item.ingredientA.trim();
    final second = item.drugB.trim().isNotEmpty
        ? item.drugB.trim()
        : item.ingredientB.trim();

    if (first.isEmpty && second.isEmpty) {
      return 'Cặp chưa xác định';
    }
    if (second.isEmpty) {
      return first;
    }
    return '$first + $second';
  }

  Widget _buildInteractionPanel(AppLocalizations l10n) {
    if (_isCheckingInteractions) {
      return Container(
        margin: const EdgeInsets.only(top: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppColors.surfaceSoft,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.border),
        ),
        child: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Đang tự động kiểm tra tương tác thuốc...',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
            SizedBox(height: 8),
            LinearProgressIndicator(minHeight: 3),
          ],
        ),
      );
    }

    if (_interactionError != null) {
      return Container(
        margin: const EdgeInsets.only(top: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppColors.error.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.error.withValues(alpha: 0.35)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.error_outline, color: AppColors.error, size: 18),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                _interactionError!,
                style: const TextStyle(color: AppColors.error),
              ),
            ),
            TextButton(
              onPressed: _refreshInteractionSummary,
              child: Text(l10n.commonRetry),
            ),
          ],
        ),
      );
    }

    if (_interactionSummary.requestedDrugNames.length < 2) {
      return Container(
        margin: const EdgeInsets.only(top: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppColors.surfaceSoft,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.border),
        ),
        child: const Text(
          'Cần ít nhất 2 thuốc để kiểm tra tương tác tự động.',
          style: TextStyle(color: AppColors.textSecondary),
        ),
      );
    }

    if (!_interactionSummary.hasInteractions) {
      return Container(
        margin: const EdgeInsets.only(top: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppColors.success.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.success.withValues(alpha: 0.4)),
        ),
        child: const Row(
          children: [
            Icon(Icons.verified_user_outlined, color: AppColors.success),
            SizedBox(width: 8),
            Expanded(
              child: Text(
                'Chưa ghi nhận tương tác giữa các thuốc đã chọn.',
                style: TextStyle(
                  color: AppColors.success,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      );
    }

    final result = _interactionSummary.result;
    final items = (result?.interactions ?? const []).take(3).toList();
    final severity = _severityLabel(l10n, _interactionSummary.highestSeverity);

    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.error.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.error.withValues(alpha: 0.45)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.warning_amber_rounded,
                color: AppColors.error,
                size: 20,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Phát hiện tương tác mức $severity',
                  style: const TextStyle(
                    color: AppColors.error,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            '${_interactionSummary.totalInteractions} cặp tương tác trong danh sách.',
            style: const TextStyle(color: AppColors.error),
          ),
          if (items.isNotEmpty) ...[
            const SizedBox(height: 10),
            for (final item in items)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(
                  '- ${_interactionPairLabel(item)}: ${item.warning.isNotEmpty ? item.warning : _severityLabel(l10n, item.severity)}',
                  style: const TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 12,
                    height: 1.35,
                  ),
                ),
              ),
          ],
        ],
      ),
    );
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
                    hintText: l10n.scanReviewSearchHint,
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
                _buildInteractionPanel(l10n),
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
                      final severity = _severityForDrug(drug);
                      final hasInteractionRisk = severity != null;
                      return Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: hasInteractionRisk
                              ? AppColors.error.withValues(alpha: 0.06)
                              : AppColors.surface,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: hasInteractionRisk
                                ? AppColors.error.withValues(alpha: 0.55)
                                : AppColors.surfaceHigh,
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (hasInteractionRisk) ...[
                              Row(
                                children: [
                                  const Icon(
                                    Icons.warning_amber_rounded,
                                    size: 16,
                                    color: AppColors.error,
                                  ),
                                  const SizedBox(width: 4),
                                  Text(
                                    'Có tương tác (${_severityLabel(l10n, severity)})',
                                    style: const TextStyle(
                                      color: AppColors.error,
                                      fontWeight: FontWeight.w700,
                                      fontSize: 12,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 6),
                            ],
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
                                l10n.scanReviewOcrRaw(drug.ocrText),
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
                  onPressed: (_drugs.isEmpty || _isCheckingInteractions)
                      ? null
                      : _continue,
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
