import 'dart:typed_data';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../../core/theme/app_theme.dart';
import '../data/local_quality_gate.dart';
import '../data/scan_repository.dart';
import '../domain/scan_result.dart';

class _QueuedCapture {
  _QueuedCapture({required this.bytes, required this.filename});

  final Uint8List bytes;
  final String filename;
  String status = 'PENDING';
  String message = '';
}

/// Screen: choose/capture image → upload → OCR.
class ScanCameraScreen extends ConsumerStatefulWidget {
  const ScanCameraScreen({super.key});

  @override
  ConsumerState<ScanCameraScreen> createState() => _ScanCameraScreenState();
}

class _ScanCameraScreenState extends ConsumerState<ScanCameraScreen> {
  final _picker = ImagePicker();
  final List<_QueuedCapture> _captures = [];
  bool _isUploading = false;
  String? _error;
  String? _sessionId;
  String? _qualityBanner;
  bool _converged = false;
  final Map<String, DetectedDrug> _mergedDrugs = {};

  Future<_QueuedCapture> _buildQueuedCapture(
    Uint8List bytes,
    String filename,
  ) async {
    final quality = await assessLocalImageQuality(bytes);
    final capture = _QueuedCapture(bytes: bytes, filename: filename);
    capture.status = switch (quality.state) {
      'GOOD' => 'READY',
      'WARNING' => 'WARNING',
      'REJECT' => 'REJECT',
      _ => 'PENDING',
    };
    capture.message = quality.guidance;
    return capture;
  }

  Future<void> _pickImage(ImageSource source) async {
    try {
      final picked = await _picker.pickImage(
        source: source,
        maxWidth: 2048,
        maxHeight: 2048,
        imageQuality: 85,
      );
      if (picked == null) return;

      final bytes = await picked.readAsBytes();

      // File size check
      if (bytes.lengthInBytes > 10 * 1024 * 1024) {
        setState(() => _error = 'Ảnh quá lớn, vui lòng chọn ảnh <10MB');
        return;
      }

      final capture = await _buildQueuedCapture(bytes, picked.name);

      setState(() {
        _captures.add(capture);
        _error = null;
      });
    } catch (e) {
      setState(() => _error = 'Không thể chọn ảnh: $e');
    }
  }

  Future<void> _pickMultiFromGallery() async {
    try {
      final pickedList = await _picker.pickMultiImage(
        maxWidth: 2048,
        maxHeight: 2048,
        imageQuality: 85,
      );
      if (pickedList.isEmpty) return;

      final newCaptures = <_QueuedCapture>[];
      for (final picked in pickedList) {
        final bytes = await picked.readAsBytes();
        if (bytes.lengthInBytes > 10 * 1024 * 1024) {
          continue;
        }
        newCaptures.add(await _buildQueuedCapture(bytes, picked.name));
      }

      setState(() {
        _captures.addAll(newCaptures);
        _error = null;
      });
    } catch (e) {
      setState(() => _error = 'Không thể chọn nhiều ảnh: $e');
    }
  }

  void _mergeDrugs(List<DetectedDrug> drugs) {
    for (final d in drugs) {
      final key = d.name.trim().toLowerCase();
      if (key.isEmpty) continue;
      final old = _mergedDrugs[key];
      if (old == null || d.confidence > old.confidence) {
        _mergedDrugs[key] = d;
      }
    }
  }

  Future<void> _uploadAndScan() async {
    if (_captures.isEmpty) return;

    final queuedForUpload = _captures
        .where((cap) => cap.status != 'REJECT')
        .toList();
    if (queuedForUpload.isEmpty) {
      setState(() {
        _error =
            'Tất cả ảnh đều bị loại từ kiểm tra cục bộ. Hãy chụp lại rõ hơn.';
      });
      return;
    }

    setState(() {
      _isUploading = true;
      _error = null;
    });

    try {
      final repo = ref.read(scanRepositoryProvider);
      _sessionId = await repo.startSession();
      _mergedDrugs.clear();
      _converged = false;
      ScanResult? finalResult;

      for (final cap in queuedForUpload) {
        if (_converged) break;

        setState(() {
          cap.status = 'PROCESSING';
          cap.message = 'Đang kiểm tra chất lượng và nhận diện...';
        });

        final result = await repo.addImageToSession(
          sessionId: _sessionId!,
          imageBytes: cap.bytes,
          filename: cap.filename,
        );

        _mergeDrugs(result.drugs);

        setState(() {
          _qualityBanner = result.qualityState;
          _converged = result.converged;
          if (result.qualityState == 'REJECT' || result.rejected) {
            cap.status = 'REJECT';
            cap.message =
                result.rejectReason ??
                result.guidance ??
                'Ảnh có vấn đề, vui lòng chụp lại.';
          } else if (result.qualityState == 'WARNING') {
            cap.status = 'WARNING';
            cap.message =
                result.guidance ?? 'Ảnh tạm ổn, nên cải thiện góc chụp.';
          } else {
            cap.status = 'GOOD';
            cap.message = result.guidance ?? 'Ảnh tốt.';
          }
        });
      }

      if (_sessionId != null) {
        finalResult = await repo.stopSession(_sessionId!);
        _mergeDrugs(finalResult.drugs);
      }

      if (!mounted) return;

      if (_mergedDrugs.isEmpty) {
        setState(() {
          _isUploading = false;
          _error = 'Không nhận diện được thuốc nào. Thử lại hoặc nhập tay.';
        });
        return;
      }

      final reviewResult =
          finalResult ??
          ScanResult(
            scanId: _sessionId ?? '',
            sessionId: _sessionId,
            drugs: _mergedDrugs.values
                .map(
                  (d) => DetectedDrug(
                    name: d.name,
                    dosage: d.dosage,
                    confidence: d.confidence,
                  ),
                )
                .toList(),
            qualityState: _qualityBanner ?? 'GOOD',
            converged: _converged,
          );

      context.go('/create/review', extra: reviewResult);
    } catch (e) {
      if (!mounted) return;
      String msg = 'Đã xảy ra lỗi khi quét';
      if (e.toString().contains('503')) {
        msg = 'Dịch vụ AI tạm thời không khả dụng';
      } else if (e.toString().contains('timeout') ||
          e.toString().contains('Timeout')) {
        msg = 'Quá thời gian, thử lại sau';
      } else if (e.toString().contains('connection')) {
        msg = 'Không kết nối được server';
      }
      setState(() {
        _isUploading = false;
        _error = msg;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: _isUploading ? _buildLoading() : _buildContent(),
    );
  }

  Widget _buildLoading() {
    return Container(
      color: Colors.white,
      alignment: Alignment.center,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(
            width: 60,
            height: 60,
            child: CircularProgressIndicator(
              strokeWidth: 4,
              color: AppColors.info,
            ),
          ),
          const SizedBox(height: 20),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 40),
            child: Text(
              'Hay doi vai giay de chung toi trich xuat thong tin tu don thuoc cua ban...',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: AppColors.textPrimary,
                fontSize: 18,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildContent() {
    return SafeArea(
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 10, 18, 0),
            child: Row(
              children: [
                IconButton(
                  onPressed: () => context.go('/create'),
                  icon: const Icon(
                    Icons.close_rounded,
                    color: Colors.white,
                    size: 32,
                  ),
                ),
                const Spacer(),
                if (_captures.isNotEmpty)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.28),
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Text(
                      '${_captures.length} anh',
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
              ],
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(18, 8, 18, 0),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(26),
                child: Container(
                  color: Colors.black,
                  child: Stack(
                    children: [
                      Positioned.fill(
                        child: _captures.isNotEmpty
                            ? _buildCaptureList()
                            : Container(
                                decoration: const BoxDecoration(
                                  gradient: LinearGradient(
                                    colors: [
                                      Color(0xFF32454E),
                                      Color(0xFF172127),
                                    ],
                                    begin: Alignment.topCenter,
                                    end: Alignment.bottomCenter,
                                  ),
                                ),
                                child: const Center(
                                  child: Padding(
                                    padding: EdgeInsets.symmetric(
                                      horizontal: 32,
                                    ),
                                    child: Text(
                                      'Can giua don thuoc trong khung va giu may on dinh truoc khi chup.',
                                      textAlign: TextAlign.center,
                                      style: TextStyle(
                                        color: Colors.white70,
                                        fontSize: 18,
                                        height: 1.4,
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                      ),
                      const Positioned(
                        top: 22,
                        left: 22,
                        child: _CornerMark(top: true, left: true),
                      ),
                      const Positioned(
                        top: 22,
                        right: 22,
                        child: _CornerMark(top: true, left: false),
                      ),
                      const Positioned(
                        bottom: 120,
                        left: 22,
                        child: _CornerMark(top: false, left: true),
                      ),
                      const Positioned(
                        bottom: 120,
                        right: 22,
                        child: _CornerMark(top: false, left: false),
                      ),
                      const Center(
                        child: Icon(
                          Icons.add_rounded,
                          color: Colors.white,
                          size: 72,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          Container(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
            decoration: const BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.vertical(top: Radius.circular(30)),
            ),
            child: Column(
              children: [
                if (_qualityBanner != null) ...[
                  _buildQualityBanner(_qualityBanner!),
                  const SizedBox(height: 10),
                ],
                if (_error != null) ...[
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppColors.error.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.error_outline, color: AppColors.error),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            _error!,
                            style: const TextStyle(color: AppColors.error),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 10),
                ],
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _pickImage(ImageSource.gallery),
                        icon: const Icon(Icons.upload_file_rounded),
                        label: Text(kIsWeb ? 'Tai len' : 'Tai len'),
                      ),
                    ),
                    const SizedBox(width: 16),
                    InkWell(
                      onTap: !kIsWeb
                          ? () => _pickImage(ImageSource.camera)
                          : null,
                      borderRadius: BorderRadius.circular(999),
                      child: Ink(
                        width: 72,
                        height: 72,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: AppColors.primary,
                          border: Border.all(
                            color: AppColors.primaryDark,
                            width: 4,
                          ),
                        ),
                        child: const Icon(
                          Icons.circle,
                          color: Colors.white,
                          size: 34,
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _showGuide,
                        icon: const Icon(Icons.help_outline_rounded),
                        label: const Text('Huong dan'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                if (_captures.length > 1)
                  TextButton.icon(
                    onPressed: _pickMultiFromGallery,
                    icon: const Icon(Icons.collections_outlined),
                    label: const Text('Them nhieu anh lien tiep'),
                  )
                else
                  TextButton.icon(
                    onPressed: _pickMultiFromGallery,
                    icon: const Icon(Icons.collections_outlined),
                    label: const Text('Chon nhieu anh'),
                  ),
                const SizedBox(height: 8),
                ElevatedButton.icon(
                  onPressed: _captures.isNotEmpty ? _uploadAndScan : null,
                  icon: const Icon(Icons.document_scanner_outlined),
                  label: const Text('Bat dau quet'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _showGuide() {
    showModalBottomSheet<void>(
      context: context,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: const [
              Text(
                'Huong dan chup don thuoc',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
              ),
              SizedBox(height: 12),
              Text('1. Dat don thuoc tron ven trong khung.'),
              SizedBox(height: 8),
              Text('2. Giu may dung va tranh bong den / loe sang.'),
              SizedBox(height: 8),
              Text('3. Neu anh canh kho doc, chup them 1-2 anh o goc dep hon.'),
              SizedBox(height: 8),
              Text('4. Neu van khong doc duoc, ban co the nhap tay thay the.'),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCaptureList() {
    return ListView.builder(
      padding: const EdgeInsets.all(8),
      itemCount: _captures.length,
      itemBuilder: (context, index) {
        final item = _captures[index];
        final color = switch (item.status) {
          'READY' => AppColors.primary,
          'GOOD' => Colors.green,
          'WARNING' => Colors.orange,
          'REJECT' => Colors.red,
          'PROCESSING' => AppColors.primary,
          _ => AppColors.textMuted,
        };
        return Container(
          margin: const EdgeInsets.only(bottom: 8),
          decoration: BoxDecoration(
            color: Colors.black.withValues(alpha: 0.32),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: Colors.white.withValues(alpha: 0.16)),
          ),
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: color.withValues(alpha: 0.18),
              child: Icon(Icons.image, color: color),
            ),
            title: Text(
              item.filename,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w700,
              ),
            ),
            subtitle: Text(
              item.message.isEmpty ? 'Chua xu ly' : item.message,
              style: const TextStyle(color: Colors.white70),
            ),
            trailing: Text(
              item.status,
              style: TextStyle(color: color, fontWeight: FontWeight.w800),
            ),
          ),
        );
      },
    );
  }

  Widget _buildQualityBanner(String state) {
    final (label, color) = switch (state) {
      'GOOD' => ('Ảnh tốt', Colors.green),
      'WARNING' => ('Ảnh tạm ổn, nên chỉnh góc', Colors.orange),
      'REJECT' => ('Ảnh có vấn đề, cần chụp lại', Colors.red),
      _ => ('Đang đánh giá ảnh', AppColors.primary),
    };

    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(Icons.verified_outlined, color: color, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              label,
              style: TextStyle(color: color, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class _CornerMark extends StatelessWidget {
  const _CornerMark({required this.top, required this.left});

  final bool top;
  final bool left;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 34,
      height: 34,
      child: CustomPaint(
        painter: _CornerPainter(top: top, left: left),
      ),
    );
  }
}

class _CornerPainter extends CustomPainter {
  _CornerPainter({required this.top, required this.left});

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
