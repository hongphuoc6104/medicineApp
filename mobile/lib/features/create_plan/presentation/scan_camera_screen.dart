import 'dart:typed_data';

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../../core/theme/app_theme.dart';
import '../data/local_quality_gate.dart';
import '../data/scan_camera_controller.dart';
import '../data/scan_repository.dart';

// ---------------------------------------------------------------------------
// Screen states
// ---------------------------------------------------------------------------

enum _ScreenMode {
  /// Live camera preview is shown.
  cameraPreview,

  /// Uploading image to server.
  uploading,
}

// ---------------------------------------------------------------------------
// Screen widget — Primary "1 ảnh đẹp" flow
// ---------------------------------------------------------------------------

class ScanCameraScreen extends ConsumerStatefulWidget {
  const ScanCameraScreen({super.key});

  @override
  ConsumerState<ScanCameraScreen> createState() => _ScanCameraScreenState();
}

class _ScanCameraScreenState extends ConsumerState<ScanCameraScreen>
    with WidgetsBindingObserver {
  final _picker = ImagePicker();
  final _scanCameraCtrl = ScanCameraController();

  _ScreenMode _mode = _ScreenMode.cameraPreview;
  String? _error;
  String? _qualityBanner;
  String? _qualityGuidance;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _scanCameraCtrl.addListener(_onCameraStateChanged);
    _scanCameraCtrl.onAutoCaptured = (bytes) {
      if (mounted) {
        _processAndUpload(bytes, 'auto_capture_${DateTime.now().millisecondsSinceEpoch}.jpg');
      }
    };
    // Camera preview must open immediately on screen entry (plan §3.2 / §6.2)
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && !kIsWeb) {
        _openCamera();
      }
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _scanCameraCtrl.removeListener(_onCameraStateChanged);
    _scanCameraCtrl.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.inactive ||
        state == AppLifecycleState.paused) {
      _scanCameraCtrl.pause();
    } else if (state == AppLifecycleState.resumed) {
      _scanCameraCtrl.resume();
    }
  }

  void _onCameraStateChanged() {
    if (!mounted) return;
    setState(() {});
  }

  // -------------------------------------------------------------------------
  // Camera actions
  // -------------------------------------------------------------------------

  Future<void> _openCamera() async {
    await _scanCameraCtrl.initialize();
    if (mounted) setState(() {});
  }

  Future<void> _captureFromCamera() async {
    final bytes = await _scanCameraCtrl.capturePhoto();
    if (bytes == null) {
      setState(() => _error = 'Chụp ảnh thất bại. Thử lại.');
      return;
    }
    await _processAndUpload(
      bytes,
      'capture_${DateTime.now().millisecondsSinceEpoch}.jpg',
    );
  }

  Future<void> _pickFromGallery() async {
    try {
      final picked = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 2048,
        maxHeight: 2048,
        imageQuality: 85,
      );
      if (picked == null) return;
      final bytes = await picked.readAsBytes();
      if (bytes.lengthInBytes > 10 * 1024 * 1024) {
        setState(() => _error = 'Ảnh quá lớn, vui lòng chọn ảnh < 10MB');
        return;
      }
      await _processAndUpload(bytes, picked.name);
    } catch (e) {
      setState(() => _error = 'Không thể mở thư viện ảnh: $e');
    }
  }

  // -------------------------------------------------------------------------
  // Local quality check → upload → navigate to review
  // -------------------------------------------------------------------------

  Future<void> _processAndUpload(Uint8List bytes, String filename) async {
    // Step 1: local quality gate
    final quality = await assessLocalImageQuality(bytes);

    if (quality.state == 'REJECT') {
      setState(() {
        _qualityBanner = 'REJECT';
        _qualityGuidance = quality.guidance;
        _error = null;
      });
      _scanCameraCtrl.startAutoCaptureStream();
      return;
    }

    if (quality.state == 'WARNING') {
      // Show banner but allow user to choose to proceed or retake
      setState(() {
        _qualityBanner = 'WARNING';
        _qualityGuidance = quality.guidance;
        _error = null;
      });
      // Give user a chance to decide — show bottom sheet
      final shouldProceed = await _showQualityWarning(
        guidance: quality.guidance,
        rejectReason: quality.rejectReason,
      );
      if (!shouldProceed) {
        _scanCameraCtrl.startAutoCaptureStream();
        return;
      }
    }

    // Step 2: upload and scan
    setState(() {
      _mode = _ScreenMode.uploading;
      _error = null;
      _qualityBanner = null;
    });

    try {
      final repo = ref.read(scanRepositoryProvider);
      final result = await repo.uploadPrescription(
        imageBytes: bytes,
        filename: filename,
      );

      if (!mounted) return;

      if (result.drugs.isEmpty && result.qualityState == 'REJECT') {
        setState(() {
          _mode = _ScreenMode.cameraPreview;
          _qualityBanner = 'REJECT';
          _qualityGuidance =
              result.guidance ?? 'Ảnh có vấn đề, thử chụp lại rõ hơn.';
        });
        _scanCameraCtrl.startAutoCaptureStream();
        return;
      }

      if (result.drugs.isEmpty) {
        setState(() {
          _mode = _ScreenMode.cameraPreview;
          _error = 'Không nhận diện được thuốc nào. Hãy thử lại hoặc nhập tay.';
        });
        _scanCameraCtrl.startAutoCaptureStream();
        return;
      }

      context.go('/create/review', extra: result);
    } catch (e) {
      if (!mounted) return;
      var msg = 'Đã xảy ra lỗi khi quét';
      if (e.toString().contains('503')) {
        msg = 'Dịch vụ AI tạm thời không khả dụng';
      } else if (e.toString().contains('timeout') ||
          e.toString().contains('Timeout')) {
        msg = 'Quá thời gian chờ, vui lòng thử lại';
      } else if (e.toString().contains('connection')) {
        msg = 'Không kết nối được máy chủ';
      }
      setState(() {
        _mode = _ScreenMode.cameraPreview;
        _error = msg;
      });
      _scanCameraCtrl.startAutoCaptureStream();
    }
  }

  Future<bool> _showQualityWarning({
    required String? guidance,
    String? rejectReason,
  }) async {
    // Chọn icon và tiêu đề phù hợp với từng loại lỗi
    IconData warningIcon;
    String warningTitle;
    switch (rejectReason) {
      case 'BLURRY_IMAGE':
        warningIcon = Icons.blur_on_outlined;
        warningTitle = 'Ảnh bị mờ';
        break;
      case 'GLARE_IMAGE':
        warningIcon = Icons.wb_sunny_outlined;
        warningTitle = 'Ảnh bị chói';
        break;
      case 'CONTENT_CUTOFF':
        warningIcon = Icons.crop_outlined;
        warningTitle = 'Ảnh bị cắt thiếu';
        break;
      default:
        warningIcon = Icons.warning_amber_rounded;
        warningTitle = 'Ảnh chưa đủ sắc nét';
    }

    final result = await showModalBottomSheet<bool>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Icon(warningIcon, color: AppColors.warning, size: 28),
                  const SizedBox(width: 10),
                  Text(
                    warningTitle,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                guidance ?? 'Ảnh có thể ảnh hưởng đến kết quả nhận diện.',
                style: const TextStyle(color: AppColors.textSecondary),
              ),
              const SizedBox(height: 20),
              ElevatedButton.icon(
                onPressed: () => Navigator.pop(ctx, false),
                icon: const Icon(Icons.camera_alt_outlined),
                label: const Text('Chụp lại'),
              ),
              const SizedBox(height: 8),
              OutlinedButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Vẫn tiếp tục quét'),
              ),
            ],
          ),
        ),
      ),
    );
    return result ?? false;
  }

  // -------------------------------------------------------------------------
  // Build
  // -------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    if (_mode == _ScreenMode.uploading) {
      return _buildUploadingOverlay();
    }
    return _buildCameraPreview();
  }

  // -------------------------------------------------------------------------
  // Uploading overlay
  // -------------------------------------------------------------------------

  Widget _buildUploadingOverlay() {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              SizedBox(
                width: 64,
                height: 64,
                child: CircularProgressIndicator(
                  strokeWidth: 4,
                  color: AppColors.primary,
                ),
              ),
              const SizedBox(height: 24),
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 40),
                child: Text(
                  'Đang trích xuất thông tin từ đơn thuốc...',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(height: 12),
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 40),
                child: Text(
                  'Quá trình này mất khoảng 10–20 giây',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: AppColors.textSecondary),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // -------------------------------------------------------------------------
  // Live camera preview (primary mode)
  // -------------------------------------------------------------------------

  Widget _buildCameraPreview() {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Stack(
          children: [
            // Camera feed or state messages
            Positioned.fill(child: _buildCameraBody()),

            // Top bar
            Positioned(top: 0, left: 0, right: 0, child: _buildCameraTopBar()),

            // Quality / error banner
            if (_qualityBanner != null || _error != null)
              Positioned(
                top: 60,
                left: 16,
                right: 16,
                child: _qualityBanner != null
                    ? _buildQualityFeedback()
                    : _buildErrorFeedback(_error!),
              ),

            // Bottom controls
            Positioned(
              bottom: 0,
              left: 0,
              right: 0,
              child: _buildCameraBottomBar(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCameraBody() {
    final camState = _scanCameraCtrl.state;

    if (camState == ScanCameraState.initializing) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(color: Colors.white),
            SizedBox(height: 16),
            Text(
              'Đang khởi động camera...',
              style: TextStyle(color: Colors.white70),
            ),
          ],
        ),
      );
    }

    if (camState == ScanCameraState.permissionDenied) {
      return _buildCameraError(
        icon: Icons.no_photography_outlined,
        message:
            _scanCameraCtrl.errorMessage ??
            'Quyền camera bị từ chối. Vào Cài đặt để cấp quyền.',
        actionLabel: 'Dùng Thư viện',
        onAction: _pickFromGallery,
      );
    }

    if (camState == ScanCameraState.unavailable) {
      return _buildCameraError(
        icon: Icons.camera_outlined,
        message: _scanCameraCtrl.errorMessage ?? 'Camera không khả dụng.',
        actionLabel: 'Dùng Thư viện',
        onAction: _pickFromGallery,
      );
    }

    // Ready or capturing
    if (_scanCameraCtrl.cameraController != null &&
        _scanCameraCtrl.cameraController!.value.isInitialized) {
      return GestureDetector(
        onTap: () {
          if (_scanCameraCtrl.state != ScanCameraState.capturing) {
            _captureFromCamera();
          }
        },
        child: ClipRect(
          child: OverflowBox(
            alignment: Alignment.center,
            child: FittedBox(
              fit: BoxFit.cover,
              child: SizedBox(
                width:
                    _scanCameraCtrl.cameraController!.value.previewSize?.height ??
                    1,
                height:
                    _scanCameraCtrl.cameraController!.value.previewSize?.width ??
                    1,
                child: CameraPreview(_scanCameraCtrl.cameraController!),
              ),
            ),
          ),
        ),
      );
    }

    return const SizedBox.shrink();
  }

  Widget _buildCameraError({
    required IconData icon,
    required String message,
    required String actionLabel,
    required VoidCallback onAction,
  }) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: Colors.white54, size: 64),
            const SizedBox(height: 16),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white70, fontSize: 15),
            ),
            const SizedBox(height: 24),
            ElevatedButton(onPressed: onAction, child: Text(actionLabel)),
          ],
        ),
      ),
    );
  }

  Widget _buildCameraTopBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      color: Colors.black54,
      child: Row(
        children: [
          IconButton(
            onPressed: () => context.go('/create'),
            icon: const Icon(Icons.close, color: Colors.white),
            tooltip: 'Đóng',
          ),
          const Expanded(
            child: Text(
              'Chụp đơn thuốc',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white,
                fontSize: 17,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          // Guidance icon
          IconButton(
            onPressed: _showGuide,
            icon: const Icon(Icons.help_outline, color: Colors.white70),
            tooltip: 'Hướng dẫn',
          ),
        ],
      ),
    );
  }

  Widget _buildCameraBottomBar() {
    final isCapturing = _scanCameraCtrl.state == ScanCameraState.capturing;

    return Container(
      padding: const EdgeInsets.fromLTRB(24, 20, 24, 36),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.bottomCenter,
          end: Alignment.topCenter,
          colors: [Colors.black87, Colors.transparent],
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Guidance hint
          const Text(
            'Đưa danh sách thuốc vào khung hình\nvà chạm màn hình để chụp',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white70, fontSize: 13, height: 1.4),
          ),
          const SizedBox(height: 18),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // Gallery fallback
              _CameraIconBtn(
                icon: Icons.photo_library_outlined,
                label: 'Thư viện',
                onTap: _pickFromGallery,
              ),

              // Capture button
              GestureDetector(
                onTap: isCapturing ? null : _captureFromCamera,
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 160),
                  width: isCapturing ? 68 : 72,
                  height: isCapturing ? 68 : 72,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: _scanCameraCtrl.isReady
                        ? Colors.white
                        : Colors.white30,
                    border: Border.all(color: Colors.white70, width: 4),
                  ),
                  child: isCapturing
                      ? const Padding(
                          padding: EdgeInsets.all(18),
                          child: CircularProgressIndicator(
                            strokeWidth: 2.5,
                            color: Colors.black54,
                          ),
                        )
                      : const Icon(
                          Icons.camera_alt,
                          color: Colors.black87,
                          size: 30,
                        ),
                ),
              ),

              // Retry / manual entry
              _CameraIconBtn(
                icon: Icons.edit_note_rounded,
                label: 'Nhập tay',
                onTap: () => context.go('/create/edit'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildQualityFeedback() {
    final isReject = _qualityBanner == 'REJECT';
    final color = isReject ? AppColors.error : AppColors.warning;
    final icon = isReject ? Icons.cancel_outlined : Icons.warning_amber_outlined;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.92),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Icon(icon, color: Colors.white, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  _qualityGuidance ?? (isReject ? 'Ảnh có vấn đề, hãy chụp lại.' : 'Ảnh chưa tối ưu.'),
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
                ),
              ),
              TextButton(
                onPressed: () => setState(() {
                  _qualityBanner = null;
                  _qualityGuidance = null;
                }),
                child: const Text('OK', style: TextStyle(color: Colors.white)),
              ),
            ],
          ),
          if (isReject) ...[
            const SizedBox(height: 6),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () => setState(() {
                  _qualityBanner = null;
                  _qualityGuidance = null;
                }),
                icon: const Icon(Icons.camera_alt_outlined, color: Colors.white, size: 16),
                label: const Text('Chụp lại', style: TextStyle(color: Colors.white)),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: Colors.white38),
                  padding: const EdgeInsets.symmetric(vertical: 8),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildErrorFeedback(String message) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.error.withValues(alpha: 0.92),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: Colors.white, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          TextButton(
            onPressed: () => setState(() => _error = null),
            child: const Text('OK', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  void _showGuide() {
    showModalBottomSheet<void>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: const [
              Text(
                'Hướng dẫn quét đơn thuốc',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
              ),
              SizedBox(height: 12),
              Text('1. Đưa vùng hiển thị tên thuốc vào giữa khung hình.'),
              SizedBox(height: 8),
              Text('2. Giữ máy ổn định, tránh chỗ quá chói sáng.'),
              SizedBox(height: 8),
              Text('3. Ứng dụng sẽ TỰ ĐỘNG CHỤP khi ảnh đủ rõ nét.'),
              SizedBox(height: 8),
              Text('4. Hoặc bạn có thể chạm vào màn hình / bấm nút để tự chụp.'),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Helper widget for camera bottom bar icon buttons
// ---------------------------------------------------------------------------

class _CameraIconBtn extends StatelessWidget {
  const _CameraIconBtn({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: const BoxDecoration(
              color: Colors.white24,
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: Colors.white, size: 26),
          ),
          const SizedBox(height: 6),
          Text(
            label,
            style: const TextStyle(color: Colors.white70, fontSize: 11),
          ),
        ],
      ),
    );
  }
}
