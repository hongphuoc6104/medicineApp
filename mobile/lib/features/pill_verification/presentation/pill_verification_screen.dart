import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../../core/theme/app_theme.dart';
import '../../create_plan/data/plan_repository.dart';
import '../../home/data/today_schedule_notifier.dart';
import '../../home/domain/today_schedule.dart';
import '../data/pill_verification_repository.dart';
import '../domain/pill_verification.dart';

class PillVerificationScreen extends ConsumerStatefulWidget {
  const PillVerificationScreen({super.key, required this.dose});

  final TodayDose dose;

  @override
  ConsumerState<PillVerificationScreen> createState() =>
      _PillVerificationScreenState();
}

class _PillVerificationScreenState
    extends ConsumerState<PillVerificationScreen> {
  final _picker = ImagePicker();
  PillVerificationSession? _session;
  bool _isLoading = true;
  bool _isSubmitting = false;
  String? _error;
  XFile? _imageFile;

  @override
  void initState() {
    super.initState();
    _start();
  }

  Future<void> _start() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final repo = ref.read(pillVerificationRepositoryProvider);
      final session = await repo.startSession(dose: widget.dose);
      setState(() {
        _session = session;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _pickAndUpload(ImageSource source) async {
    final picked = await _picker.pickImage(source: source, imageQuality: 90);
    if (picked == null || _session == null) {
      return;
    }

    setState(() {
      _imageFile = picked;
      _isSubmitting = true;
      _error = null;
    });
    try {
      final bytes = await picked.readAsBytes();
      final repo = ref.read(pillVerificationRepositoryProvider);
      final session = await repo.uploadImage(
        sessionId: _session!.sessionId,
        imageBytes: bytes,
        filename: picked.name,
        mimeType: _guessMime(picked.path),
      );
      setState(() {
        _session = session;
        _isSubmitting = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isSubmitting = false;
      });
    }
  }

  String _guessMime(String path) {
    final lower = path.toLowerCase();
    if (lower.endsWith('.png')) return 'image/png';
    if (lower.endsWith('.webp')) return 'image/webp';
    return 'image/jpeg';
  }

  Future<void> _assign(PillDetectionItem item, String value) async {
    if (_session == null) return;

    setState(() {
      _isSubmitting = true;
      _error = null;
    });

    try {
      final repo = ref.read(pillVerificationRepositoryProvider);
      final status = value == '__uncertain__'
          ? 'uncertain'
          : value == '__unknown__'
          ? 'unknown'
          : value == '__extra__'
          ? 'extra'
          : 'assigned';

      String? assignedDrugName;
      String? assignedPlanId;
      if (status == 'assigned') {
        final expected = _session!.expectedMedications.firstWhere(
          (med) => med.drugName == value,
          orElse: () => const ExpectedMedication(planId: '', drugName: ''),
        );
        assignedDrugName = expected.drugName.isNotEmpty
            ? expected.drugName
            : value;
        assignedPlanId = expected.planId.isNotEmpty ? expected.planId : null;
      }

      final session = await repo.assignDetection(
        sessionId: _session!.sessionId,
        detectionIdx: item.detectionIdx,
        status: status,
        assignedPlanId: assignedPlanId,
        assignedDrugName: assignedDrugName,
      );
      setState(() {
        _session = session;
        _isSubmitting = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isSubmitting = false;
      });
    }
  }

  Future<void> _confirmAndMarkTaken() async {
    final session = _session;
    if (session == null) return;
    setState(() => _isSubmitting = true);
    try {
      final repo = ref.read(pillVerificationRepositoryProvider);
      await repo.confirm(session.sessionId);
      final planRepo = ref.read(planRepositoryProvider);
      await planRepo.logDose(
        planId: widget.dose.planId,
        scheduledTime: widget.dose.scheduledTime,
        status: 'taken',
        occurrenceId: widget.dose.occurrenceId,
      );
      await ref.read(todayScheduleNotifierProvider.notifier).refresh();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Đã xác minh viên thuốc và đánh dấu đã uống'),
        ),
      );
      context.go('/home');
    } on DioException catch (e) {
      setState(() {
        _error = e.message ?? 'Không thể xác nhận';
        _isSubmitting = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isSubmitting = false;
      });
    }
  }

  String _detectionTitle(PillDetectionItem item) {
    if (item.assignedDrugName != null && item.assignedDrugName!.isNotEmpty) {
      return item.assignedDrugName!;
    }
    return 'Viên ${item.detectionIdx + 1}';
  }

  List<DropdownMenuItem<String>> _buildAssignmentItems(
    PillDetectionItem item,
    List<ExpectedMedication> expected,
  ) {
    final fromSuggestions = item.suggestions
        .map((s) => s['drugName']?.toString() ?? '')
        .where((name) => name.isNotEmpty)
        .toSet();

    final expectedNames = expected.map((med) => med.drugName).toSet();
    final mergedNames = <String>{...fromSuggestions, ...expectedNames};

    return [
      ...mergedNames.map(
        (name) => DropdownMenuItem<String>(value: name, child: Text(name)),
      ),
      const DropdownMenuItem<String>(
        value: '__uncertain__',
        child: Text('Không chắc viên này là thuốc nào'),
      ),
      const DropdownMenuItem<String>(
        value: '__unknown__',
        child: Text('Viên lạ'),
      ),
      const DropdownMenuItem<String>(
        value: '__extra__',
        child: Text('Viên dư so với liều này'),
      ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    if (_session == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Xác minh viên thuốc')),
        body: Center(
          child: Text(_error ?? 'Không khởi tạo được phiên xác minh'),
        ),
      );
    }

    final expected = _session!.expectedMedications;
    final detections = _session!.detections;

    return Scaffold(
      appBar: AppBar(title: const Text('Ảnh viên thuốc')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 10, 20, 120),
        children: [
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(28),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.dose.drugName,
                  style: const TextStyle(
                    fontWeight: FontWeight.w900,
                    fontSize: 22,
                  ),
                ),
                const SizedBox(height: 6),
                const Text(
                  'Xác minh đúng loại thuốc và số viên bạn chuẩn bị uống cho khung giờ này.',
                  style: TextStyle(color: AppColors.textSecondary),
                ),
                const SizedBox(height: 14),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _SummaryChip(
                      label: 'Đã phát hiện',
                      value: '${_session!.summary.totalDetections}',
                    ),
                    _SummaryChip(
                      label: 'Đã gán',
                      value: '${_session!.summary.assigned}',
                    ),
                    _SummaryChip(
                      label: 'Không chắc',
                      value: '${_session!.summary.uncertain}',
                    ),
                    _SummaryChip(
                      label: 'Thiếu',
                      value: '${_session!.summary.missingExpected}',
                    ),
                  ],
                ),
                if (_session!.referenceCoverage.hasMissing) ...[
                  const SizedBox(height: 10),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppColors.warning.withValues(alpha: 0.14),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      'Thiếu ảnh mẫu cho: ${_session!.referenceCoverage.missingDrugNames.join(', ')}',
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),
          _buildImagePanel(),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: AppColors.error)),
          ],
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: AppColors.surfaceSoft,
              borderRadius: BorderRadius.circular(26),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Rà soát kết quả xác minh',
                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 18),
                ),
                const SizedBox(height: 14),
                _HeaderRow(),
                const SizedBox(height: 8),
                if (detections.isEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 18),
                    child: Text(
                      'Chưa có viên nào được phát hiện. Hãy chụp ảnh để bắt đầu.',
                    ),
                  )
                else
                  ...detections.map((item) {
                    final currentValue = item.assignmentStatus == 'assigned'
                        ? item.assignedDrugName
                        : item.assignmentStatus == 'uncertain'
                        ? '__uncertain__'
                        : item.assignmentStatus == 'unknown'
                        ? '__unknown__'
                        : item.assignmentStatus == 'extra'
                        ? '__extra__'
                        : null;

                    return Container(
                      margin: const EdgeInsets.only(bottom: 10),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(18),
                        border: Border.all(color: AppColors.border),
                      ),
                      child: Column(
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Text(
                                  _detectionTitle(item),
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                              ),
                              SizedBox(
                                width: 110,
                                child: Text(
                                  expected.isNotEmpty &&
                                          expected.first.pillsPerDose != null
                                      ? '${expected.first.pillsPerDose} viên'
                                      : '1 viên',
                                  textAlign: TextAlign.center,
                                  style: const TextStyle(
                                    color: AppColors.textSecondary,
                                  ),
                                ),
                              ),
                              Container(
                                width: 58,
                                height: 42,
                                decoration: BoxDecoration(
                                  color: AppColors.surfaceSoft,
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                alignment: Alignment.center,
                                child: Text(item.confidence.toStringAsFixed(2)),
                              ),
                              IconButton(
                                onPressed: _isSubmitting
                                    ? null
                                    : () => _assign(item, '__extra__'),
                                icon: const Icon(
                                  Icons.delete_outline,
                                  color: AppColors.error,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          DropdownButtonFormField<String>(
                            initialValue: currentValue,
                            items: _buildAssignmentItems(item, expected),
                            hint: const Text('Gán viên này'),
                            onChanged: _isSubmitting
                                ? null
                                : (value) {
                                    if (value != null) _assign(item, value);
                                  },
                          ),
                        ],
                      ),
                    );
                  }),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _isSubmitting
                            ? null
                            : () => _pickAndUpload(ImageSource.camera),
                        icon: const Icon(Icons.camera_alt_outlined),
                        label: const Text('Chụp lại ảnh'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: _isSubmitting || detections.isEmpty
                            ? null
                            : _confirmAndMarkTaken,
                        icon: _isSubmitting
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Icon(Icons.verified_outlined),
                        label: const Text('Xác nhận đã uống'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildImagePanel() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        children: [
          Container(
            height: 280,
            decoration: BoxDecoration(
              color: Colors.black,
              borderRadius: BorderRadius.circular(24),
            ),
            child: Stack(
              fit: StackFit.expand,
              children: [
                if (_imageFile != null)
                  FutureBuilder<Uint8List>(
                    future: _imageFile!.readAsBytes(),
                    builder: (context, snapshot) {
                      if (!snapshot.hasData) {
                        return const Center(child: CircularProgressIndicator());
                      }
                      return ClipRRect(
                        borderRadius: BorderRadius.circular(24),
                        child: Image.memory(snapshot.data!, fit: BoxFit.cover),
                      );
                    },
                  )
                else
                  const Center(
                    child: Padding(
                      padding: EdgeInsets.symmetric(horizontal: 24),
                      child: Text(
                        'Chụp ảnh viên thuốc cho lần uống này',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Colors.white70,
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ),
                const Positioned(
                  top: 20,
                  left: 20,
                  child: _ScanCorner(top: true, left: true),
                ),
                const Positioned(
                  top: 20,
                  right: 20,
                  child: _ScanCorner(top: true, left: false),
                ),
                const Positioned(
                  bottom: 20,
                  left: 20,
                  child: _ScanCorner(top: false, left: true),
                ),
                const Positioned(
                  bottom: 20,
                  right: 20,
                  child: _ScanCorner(top: false, left: false),
                ),
                const Center(
                  child: Icon(Icons.add_rounded, color: Colors.white, size: 58),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _isSubmitting
                      ? null
                      : () => _pickAndUpload(ImageSource.gallery),
                  icon: const Icon(Icons.upload_file_rounded),
                  label: const Text('Tải lên'),
                ),
              ),
              const SizedBox(width: 14),
              InkWell(
                onTap: _isSubmitting
                    ? null
                    : () => _pickAndUpload(ImageSource.camera),
                borderRadius: BorderRadius.circular(999),
                child: Ink(
                  width: 72,
                  height: 72,
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    shape: BoxShape.circle,
                    border: Border.all(color: AppColors.primaryDark, width: 4),
                  ),
                  child: const Icon(
                    Icons.circle,
                    color: Colors.white,
                    size: 34,
                  ),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text(
                          'Giữ các viên thuốc tách nhau và chụp ở nơi đủ ánh sáng.',
                        ),
                      ),
                    );
                  },
                  icon: const Icon(Icons.help_outline_rounded),
                  label: const Text('Hướng dẫn'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SummaryChip extends StatelessWidget {
  const _SummaryChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.surfaceHigh,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text('$label: $value', style: const TextStyle(fontSize: 12)),
    );
  }
}

class _HeaderRow extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return const Row(
      children: [
        Expanded(
          flex: 4,
          child: Text(
            'Tên thuốc',
            style: TextStyle(
              color: AppColors.textSecondary,
              fontWeight: FontWeight.w800,
              fontSize: 12,
            ),
          ),
        ),
        Expanded(
          flex: 2,
          child: Text(
            'Liều dùng',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: AppColors.textSecondary,
              fontWeight: FontWeight.w800,
              fontSize: 12,
            ),
          ),
        ),
        SizedBox(
          width: 58,
          child: Text(
            'Độ tin cậy',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: AppColors.textSecondary,
              fontWeight: FontWeight.w800,
              fontSize: 12,
            ),
          ),
        ),
        SizedBox(
          width: 40,
          child: Text(
            'Xóa',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: AppColors.textSecondary,
              fontWeight: FontWeight.w800,
              fontSize: 12,
            ),
          ),
        ),
      ],
    );
  }
}

class _ScanCorner extends StatelessWidget {
  const _ScanCorner({required this.top, required this.left});

  final bool top;
  final bool left;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 34,
      height: 34,
      child: CustomPaint(
        painter: _ScanCornerPainter(top: top, left: left),
      ),
    );
  }
}

class _ScanCornerPainter extends CustomPainter {
  _ScanCornerPainter({required this.top, required this.left});

  final bool top;
  final bool left;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    final path = Path();
    if (top && left) {
      path.moveTo(size.width, 0);
      path.lineTo(0, 0);
      path.lineTo(0, size.height);
    } else if (top && !left) {
      path.moveTo(0, 0);
      path.lineTo(size.width, 0);
      path.lineTo(size.width, size.height);
    } else if (!top && left) {
      path.moveTo(0, 0);
      path.lineTo(0, size.height);
      path.lineTo(size.width, size.height);
    } else {
      path.moveTo(size.width, 0);
      path.lineTo(size.width, size.height);
      path.lineTo(0, size.height);
    }
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
