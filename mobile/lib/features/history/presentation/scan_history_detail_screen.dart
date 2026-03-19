import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../core/theme/app_theme.dart';
import '../../create_plan/domain/plan.dart';
import '../data/scan_history_repository.dart';

class ScanHistoryDetailScreen extends ConsumerStatefulWidget {
  const ScanHistoryDetailScreen({super.key, required this.scanId});

  final String scanId;

  @override
  ConsumerState<ScanHistoryDetailScreen> createState() =>
      _ScanHistoryDetailScreenState();
}

class _ScanHistoryDetailScreenState
    extends ConsumerState<ScanHistoryDetailScreen> {
  bool _isLoading = true;
  String? _error;
  ScanHistoryDetail? _detail;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final repo = ref.read(scanHistoryRepositoryProvider);
      final detail = await repo.getHistoryDetail(widget.scanId);
      setState(() {
        _detail = detail;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  void _recreatePlan() {
    final detail = _detail;
    if (detail == null) return;
    final items = detail.drugs
        .map(
          (drug) => PlanDrugItem(
            name:
                drug['name']?.toString() ??
                drug['ocrText']?.toString() ??
                'Thuoc',
            dosage: drug['dosage']?.toString() ?? '',
          ),
        )
        .where((item) => item.name.trim().isNotEmpty)
        .toList();
    context.go('/create/edit', extra: items);
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    if (_detail == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Chi tiet lan quet')),
        body: Center(child: Text(_error ?? 'Khong tai duoc chi tiet lan quet')),
      );
    }

    final detail = _detail!;
    final df = DateFormat('dd/MM/yyyy HH:mm');

    return Scaffold(
      appBar: AppBar(title: const Text('Chi tiet lan quet')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
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
                  'Lan quet ${detail.id.substring(0, 8)}',
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                Text(df.format(detail.scannedAt.toLocal())),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _Chip(
                      label: 'Chat luong ${detail.qualityState}',
                      color: detail.qualityState == 'GOOD'
                          ? AppColors.success
                          : AppColors.warning,
                    ),
                    _Chip(
                      label: '${detail.drugCount} thuoc',
                      color: AppColors.primary,
                    ),
                    if (detail.unresolvedCount > 0)
                      _Chip(
                        label: '${detail.unresolvedCount} can review',
                        color: AppColors.warning,
                      ),
                  ],
                ),
                if (detail.guidance != null && detail.guidance!.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Text(
                    detail.guidance!,
                    style: const TextStyle(color: AppColors.textSecondary),
                  ),
                ],
                if (detail.rejectReason != null &&
                    detail.rejectReason!.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(
                    'Ly do: ${detail.rejectReason}',
                    style: const TextStyle(color: AppColors.error),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'Danh sach thuoc',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 10),
          ...detail.drugs.map((drug) {
            final status = drug['mappingStatus']?.toString() ?? 'confirmed';
            final statusColor = status == 'confirmed'
                ? AppColors.success
                : AppColors.warning;
            return Container(
              margin: const EdgeInsets.only(bottom: 10),
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
                          drug['name']?.toString() ?? 'Khong ro ten',
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                      ),
                      Text(
                        status,
                        style: TextStyle(color: statusColor, fontSize: 12),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  if ((drug['ocrText']?.toString() ?? '').isNotEmpty)
                    Text(
                      'OCR: ${drug['ocrText']}',
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
                      _PlainChip(
                        label:
                            'Conf ${(double.tryParse('${drug['confidence'] ?? 0}') ?? 0).toStringAsFixed(2)}',
                      ),
                      _PlainChip(
                        label:
                            'Match ${(double.tryParse('${drug['matchScore'] ?? 0}') ?? 0).toStringAsFixed(2)}',
                      ),
                    ],
                  ),
                ],
              ),
            );
          }),
          const SizedBox(height: 8),
          ElevatedButton.icon(
            onPressed: detail.drugs.isEmpty ? null : _recreatePlan,
            icon: const Icon(Icons.restart_alt),
            label: const Text('Tao lai ke hoach tu lan quet nay'),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () => context.go('/create/scan'),
            icon: const Icon(Icons.document_scanner_outlined),
            label: const Text('Quet don moi'),
          ),
        ],
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(label, style: TextStyle(color: color, fontSize: 12)),
    );
  }
}

class _PlainChip extends StatelessWidget {
  const _PlainChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.surfaceHigh,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Text(label, style: const TextStyle(fontSize: 11)),
    );
  }
}
