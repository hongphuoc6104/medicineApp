import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../drug/data/drug_repository.dart';
import '../../domain/plan.dart';

class DrugEntrySheet extends StatefulWidget {
  const DrugEntrySheet({super.key, required this.ref, this.initial});

  final WidgetRef ref;
  final PlanDrugItem? initial;

  @override
  State<DrugEntrySheet> createState() => _DrugEntrySheetState();
}

class _DrugEntrySheetState extends State<DrugEntrySheet> {
  late final TextEditingController _nameCtrl;
  late final TextEditingController _dosageCtrl;
  Timer? _debounceTimer;

  List<DrugSearchItem> _suggestions = [];
  bool _loadingSuggestions = false;
  // Tracks last query that produced the current suggestion set — used to
  // avoid clearing the list when the user selects an item and the controller
  // fires a change event with the newly‑selected name.
  String _lastSearchQuery = '';

  @override
  void initState() {
    super.initState();
    _nameCtrl = TextEditingController(text: widget.initial?.name ?? '');
    _dosageCtrl = TextEditingController(text: widget.initial?.dosage ?? '');
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    _nameCtrl.dispose();
    _dosageCtrl.dispose();
    super.dispose();
  }

  // ---------------------------------------------------------------------------
  // Search with debounce
  // ---------------------------------------------------------------------------

  void _onNameChanged(String query) {
    final trimmed = query.trim();

    // Reset suggestions immediately when query is too short — no debounce needed.
    if (trimmed.length < 2) {
      _debounceTimer?.cancel();
      if (mounted) {
        setState(() {
          _suggestions = [];
          _loadingSuggestions = false;
          _lastSearchQuery = '';
        });
      }
      return;
    }

    // Avoid re-searching when user just selected a suggestion (name matches).
    if (trimmed == _lastSearchQuery) return;

    // Show loading immediately so the layout area is stable before results arrive.
    if (!_loadingSuggestions && mounted) {
      setState(() => _loadingSuggestions = true);
    }

    _debounceTimer?.cancel();
    _debounceTimer = Timer(const Duration(milliseconds: 380), () {
      _fetchSuggestions(trimmed);
    });
  }

  Future<void> _fetchSuggestions(String query) async {
    if (!mounted) return;
    try {
      final repo = widget.ref.read(drugRepositoryProvider);
      final page = await repo.search(query, limit: 6);
      if (mounted) {
        setState(() {
          _suggestions = page.items;
          _loadingSuggestions = false;
          _lastSearchQuery = query;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _suggestions = [];
          _loadingSuggestions = false;
        });
      }
    }
  }

  void _selectSuggestion(DrugSearchItem item) {
    _debounceTimer?.cancel();
    setState(() {
      _nameCtrl.text = item.name;
      // Mark so that the onChange from setText doesn't trigger a new search.
      _lastSearchQuery = item.name.trim();
      _suggestions = [];
      _loadingSuggestions = false;
    });
  }

  // ---------------------------------------------------------------------------
  // Submit
  // ---------------------------------------------------------------------------

  void _submit() {
    final name = _nameCtrl.text.trim();
    if (name.isEmpty) return;
    final initial = widget.initial;
    Navigator.pop(
      context,
      PlanDrugItem(
        name: name,
        dosage: _dosageCtrl.text.trim(),
        pillsPerDose: initial?.pillsPerDose ?? 1,
        frequency: initial?.frequency ?? 'daily',
        times: initial?.times,
        totalDays: initial?.totalDays ?? 7,
        notes: initial?.notes ?? '',
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Title
          Text(
            widget.initial == null ? 'Thêm thuốc' : 'Sửa thuốc',
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 16),

          // Drug name field
          TextField(
            controller: _nameCtrl,
            autofocus: true,
            onChanged: _onNameChanged,
            decoration: const InputDecoration(
              labelText: 'Tên thuốc *',
              hintText: 'Nhập ít nhất 2 ký tự để tìm gợi ý...',
              prefixIcon: Icon(Icons.medication_outlined),
            ),
          ),

          // ── Suggestion zone ──────────────────────────────────────────────
          // AnimatedSize keeps the zone height stable while content changes,
          // preventing the layout from jumping when suggestions appear/vanish.
          AnimatedSize(
            duration: const Duration(milliseconds: 200),
            curve: Curves.easeOut,
            alignment: Alignment.topCenter,
            child: _buildSuggestionZone(),
          ),

          const SizedBox(height: 12),

          // Dosage field
          TextField(
            controller: _dosageCtrl,
            decoration: const InputDecoration(
              labelText: 'Liều lượng (tuỳ chọn)',
              hintText: 'VD: 500mg',
              prefixIcon: Icon(Icons.scale_outlined),
            ),
          ),
          const SizedBox(height: 16),

          // Action buttons
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Huỷ'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: ElevatedButton(
                  onPressed: _submit,
                  child: Text(widget.initial == null ? 'Thêm' : 'Lưu'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Suggestion zone widget
  // ---------------------------------------------------------------------------

  Widget _buildSuggestionZone() {
    // Nothing to show — return zero-size widget so AnimatedSize collapses.
    if (!_loadingSuggestions && _suggestions.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      margin: const EdgeInsets.only(top: 6),
      constraints: const BoxConstraints(maxHeight: 220),
      decoration: BoxDecoration(
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(12),
        color: AppColors.surface,
      ),
      child: _loadingSuggestions && _suggestions.isEmpty
          ? const _SuggestionLoadingRow()
          : ListView.separated(
              shrinkWrap: true,
              physics: const ClampingScrollPhysics(),
              itemCount: _suggestions.length,
              separatorBuilder: (_, _) => const Divider(height: 1),
              itemBuilder: (_, i) {
                final item = _suggestions[i];
                return ListTile(
                  dense: true,
                  title: Text(
                    item.name,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  subtitle: item.activeIngredient != null
                      ? Text(
                          item.activeIngredient!,
                          style: const TextStyle(fontSize: 12),
                        )
                      : null,
                  trailing: const Icon(
                    Icons.north_west,
                    size: 14,
                    color: AppColors.textMuted,
                  ),
                  onTap: () => _selectSuggestion(item),
                );
              },
            ),
    );
  }
}

// ---------------------------------------------------------------------------
// Compact loading row inside the suggestion zone
// ---------------------------------------------------------------------------

class _SuggestionLoadingRow extends StatelessWidget {
  const _SuggestionLoadingRow();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(vertical: 14, horizontal: 16),
      child: Row(
        children: [
          SizedBox(
            height: 16,
            width: 16,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
          SizedBox(width: 12),
          Text(
            'Đang tìm gợi ý...',
            style: TextStyle(color: AppColors.textMuted, fontSize: 13),
          ),
        ],
      ),
    );
  }
}
