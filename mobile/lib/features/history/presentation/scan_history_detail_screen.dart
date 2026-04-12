import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../core/theme/app_theme.dart';
import '../../create_plan/domain/scan_result.dart';
import '../data/scan_history_repository.dart';

class ScanHistoryDetailScreen extends ConsumerStatefulWidget {
  const ScanHistoryDetailScreen({
    super.key,
    required this.scanId,
    this.mode = 'normal',
  });

  final String scanId;

  /// 'reuse' khi đến từ /create/reuse, 'normal' khi đến từ /history.
  final String mode;

  bool get isReuseMode => mode == 'reuse';

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
    
    final scanResult = ScanResult(
      scanId: detail.id,
      drugs: detail.drugs.map((d) => DetectedDrug.fromJson(d)).toList(),
      qualityState: detail.qualityState,
      rejectReason: detail.rejectReason,
      guidance: detail.guidance,
      rejected: false,
    );
        
    context.go('/create/review', extra: scanResult);
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    if (_detail == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Chi tiết lần quét')),
        body: Center(child: Text(_error ?? 'Không tải được chi tiết lần quét')),
      );
    }

    final detail = _detail!;
    final df = DateFormat('dd/MM/yyyy HH:mm');

    return Scaffold(
      appBar: AppBar(title: const Text('Chi tiết lần quét')),
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
                  'Lần quét ${detail.id.substring(0, 8)}',
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
                      label:
                          'Chất lượng: ${detail.qualityState == 'GOOD' ? 'Tốt' : detail.qualityState}',
                      color: detail.qualityState == 'GOOD'
                          ? AppColors.success
                          : AppColors.warning,
                    ),
                    _Chip(
                      label: '${detail.drugCount} thuốc',
                      color: AppColors.primary,
                    ),
                    if (detail.unresolvedCount > 0)
                      _Chip(
                        label: '${detail.unresolvedCount} cần kiểm tra',
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
                    'Lý do: ${detail.rejectReason}',
                    style: const TextStyle(color: AppColors.error),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'Danh sách thuốc',
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
                          drug['name']?.toString() ?? 'Không rõ tên',
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                      ),
                      Text(
                        _mappingStatusLabel(status),
                        style: TextStyle(color: statusColor, fontSize: 12),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  if ((drug['dosage']?.toString() ?? '').isNotEmpty)
                    Text(
                      'Liều lượng: ${drug['dosage']}',
                      style: const TextStyle(
                        color: AppColors.textSecondary,
                        fontSize: 13,
                      ),
                    ),
                  // §3.3 — no raw Conf/Match numbers for end user
                ],
              ),
            );
          }),
          const SizedBox(height: 8),
          ElevatedButton.icon(
            onPressed: detail.drugs.isEmpty ? null : _recreatePlan,
            icon: Icon(
              widget.isReuseMode
                  ? Icons.playlist_add_rounded
                  : Icons.refresh_rounded,
            ),
            label: Text(
              widget.isReuseMode
                  ? 'Dùng lại danh sách thuốc này'
                  : 'Tạo lại kế hoạch từ lần quét này',
            ),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () => context.go('/create/scan'),
            icon: const Icon(Icons.document_scanner_outlined),
            label: const Text('Quét đơn mới'),
          ),
        ],
      ),
    );
  }

  static String _mappingStatusLabel(String status) {
    if (status == 'confirmed') return 'Đã xác nhận';
    if (status == 'unmapped_candidate') return 'Cần kiểm tra lại';
    if (status == 'rejected_noise') return 'Không rõ ràng';
    return status;
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
