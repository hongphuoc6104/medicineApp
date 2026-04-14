import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../../create_plan/domain/scan_result.dart';
import '../data/reconciliation_repository.dart';
import '../domain/reconciliation_result.dart';
import 'transition_of_care_cards.dart';

class ScanDispensedReviewScreen extends ConsumerStatefulWidget {
  const ScanDispensedReviewScreen({super.key, required this.result});

  final ScanResult result;

  @override
  ConsumerState<ScanDispensedReviewScreen> createState() => _ScanDispensedReviewScreenState();
}

class _ScanDispensedReviewScreenState extends ConsumerState<ScanDispensedReviewScreen> {
  ReconciliationResult? _reconciliation;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadReconciliation();
  }

  Future<void> _loadReconciliation() async {
    try {
      final repo = ref.read(reconciliationRepositoryProvider);
      final payload = {
        'sourceRef': widget.result.scanId,
        'items': widget.result.drugs.map((d) => {
          'ocrText': d.name,
          'matchedDrugName': d.mappedDrugName,
          'mappingStatus': d.mappingStatus,
          'confidence': d.confidence,
        }).toList()
      };
      
      final result = await repo.compareDispensedTextVsActivePlan(payload);
      if (mounted) {
        setState(() {
          _reconciliation = result;
          _isLoading = false;
        });
      }
    } catch (e) {
      debugPrint('Reconciliation load error: $e');
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Kiểm tra thuốc đã mua'),
        leading: IconButton(
          onPressed: () => context.go('/home'),
          icon: const Icon(Icons.close),
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_isLoading)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 32),
                  child: Center(child: CircularProgressIndicator()),
                ),
                
              if (!_isLoading && _reconciliation != null) ...[
                if (_reconciliation!.summary.hasChanges)
                  TransitionOfCareWidget(
                    transitionOfCare: _reconciliation!.transitionOfCare,
                  )
                else
                  Container(
                    width: double.infinity,
                    margin: const EdgeInsets.only(bottom: 16),
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AppColors.success.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: AppColors.success),
                    ),
                    child: const Row(
                      children: [
                        Icon(Icons.check_circle, color: AppColors.success),
                        SizedBox(width: 8),
                        Expanded(child: Text('Loại thuốc bạn scan hoàn toàn trùng khớp với lịch uống thuốc hiện tại.', style: TextStyle(fontWeight: FontWeight.bold))),
                      ],
                    ),
                  ),
                  
                const SizedBox(height: 16),
                const Text(
                  'Danh sách hoạt chất trích xuất được',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                Expanded(
                  child: ListView.builder(
                    itemCount: widget.result.drugs.length,
                    itemBuilder: (ctx, index) {
                      final drug = widget.result.drugs[index];
                      return ListTile(
                        leading: const Icon(Icons.medication_rounded, color: AppColors.primary),
                        title: Text(drug.mappedDrugName ?? drug.name),
                        subtitle: drug.mappedDrugName != null ? Text('Original text: ${drug.name}') : null,
                        contentPadding: EdgeInsets.zero,
                      );
                    },
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
