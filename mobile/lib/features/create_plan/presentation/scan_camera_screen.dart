import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/network/network_error_mapper.dart';
import '../../../core/theme/app_theme.dart';
import '../../../l10n/app_localizations.dart';
import '../data/local_quality_gate.dart';
import '../data/scan_camera_controller.dart';
import '../data/scan_repository.dart';

enum _ScanStage {
  camera,
  previewChecking,
  previewRejected,
  previewWarning,
  waiting,
  error,
}

class ScanCameraScreen extends ConsumerStatefulWidget {
  const ScanCameraScreen({super.key});

  @override
  ConsumerState<ScanCameraScreen> createState() => _ScanCameraScreenState();
}

class _ScanCameraScreenState extends ConsumerState<ScanCameraScreen>
    with WidgetsBindingObserver {
  final _scanCameraCtrl = ScanCameraController();

  _ScanStage _stage = _ScanStage.camera;
  Uint8List? _capturedBytes;
  String? _capturedFilename;
  LocalQualityResult? _qualityResult;
  String? _statusText;
  String? _errorText;
  bool _isCapturing = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _scanCameraCtrl.addListener(_onCameraStateChanged);
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

  Future<void> _openCamera() async {
    await _scanCameraCtrl.initialize();
    if (mounted) setState(() {});
  }

  Future<void> _captureFromCamera() async {
    if (_isCapturing || !_scanCameraCtrl.isReady) return;

    final l10n = AppLocalizations.of(context);
    setState(() {
      _isCapturing = true;
      _errorText = null;
    });

    final bytes = await _scanCameraCtrl.capturePhoto();
    if (!mounted) return;

    setState(() => _isCapturing = false);

    if (bytes == null) {
      setState(() {
        _stage = _ScanStage.error;
        _statusText = l10n.scanCameraCaptureFailed;
        _errorText = l10n.scanCameraCaptureFailed;
      });
      return;
    }

    await _scanCameraCtrl.pause();
    await _analyzeCapturedImage(
      bytes,
      'capture_${DateTime.now().millisecondsSinceEpoch}.jpg',
    );
  }

  Future<void> _analyzeCapturedImage(Uint8List bytes, String filename) async {
    final l10n = AppLocalizations.of(context);
    setState(() {
      _capturedBytes = bytes;
      _capturedFilename = filename;
      _qualityResult = null;
      _stage = _ScanStage.previewChecking;
      _statusText = 'Đang kiểm tra ảnh...';
      _errorText = null;
    });

    try {
      final quality = await assessLocalImageQuality(bytes);
      if (!mounted) return;

      setState(() {
        _qualityResult = quality;
      });

      if (quality.state == 'REJECT') {
        setState(() {
          _stage = _ScanStage.previewRejected;
          _statusText = quality.guidance;
        });
        return;
      }

      if (quality.state == 'WARNING') {
        setState(() {
          _stage = _ScanStage.previewWarning;
          _statusText = quality.guidance;
        });
        return;
      }

      setState(() {
        _stage = _ScanStage.waiting;
        _statusText = l10n.scanCameraUploadingTitle;
      });
      await _uploadCapturedImage(bytes, filename);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _stage = _ScanStage.error;
        _statusText = e.toString();
        _errorText = e.toString();
      });
    }
  }

  Future<void> _continueAfterWarning() async {
    final bytes = _capturedBytes;
    final filename = _capturedFilename;
    if (bytes == null || filename == null) return;

    final l10n = AppLocalizations.of(context);
    setState(() {
      _stage = _ScanStage.waiting;
      _statusText = l10n.scanCameraUploadingTitle;
      _errorText = null;
    });

    await _uploadCapturedImage(bytes, filename);
  }

  Future<void> _retryUpload() async {
    final bytes = _capturedBytes;
    final filename = _capturedFilename;
    if (bytes == null || filename == null) return;

    final l10n = AppLocalizations.of(context);
    setState(() {
      _stage = _ScanStage.waiting;
      _statusText = l10n.scanCameraUploadingTitle;
      _errorText = null;
    });

    await _uploadCapturedImage(bytes, filename);
  }

  Future<void> _uploadCapturedImage(Uint8List bytes, String filename) async {
    final l10n = AppLocalizations.of(context);

    try {
      final repo = ref.read(scanRepositoryProvider);
      final result = await repo.uploadPrescription(
        imageBytes: bytes,
        filename: filename,
      );

      if (!mounted) return;

      if (result.drugs.isEmpty && result.qualityState == 'REJECT') {
        setState(() {
          _stage = _ScanStage.previewRejected;
          _statusText = result.guidance ?? l10n.scanCameraQualityServerReject;
          _qualityResult = const LocalQualityResult(
            state: 'REJECT',
            rejectReason: 'SERVER_REJECT',
            guidance: 'Ảnh có vấn đề, hãy chụp lại.',
            metrics: <String, num>{},
          );
        });
        return;
      }

      if (result.drugs.isEmpty) {
        setState(() {
          _stage = _ScanStage.error;
          _statusText = l10n.scanCameraNodrugFound;
          _errorText = l10n.scanCameraNodrugFound;
        });
        return;
      }

      _clearCapturedState();
      context.go('/create/review', extra: result);
    } catch (e) {
      if (!mounted) return;
      final issue = classifyNetworkIssue(e);
      var message = l10n.scanCameraErrorGeneric;
      switch (issue) {
        case NetworkIssueKind.noConnection:
          message = l10n.scanCameraErrorConnection;
          break;
        case NetworkIssueKind.timeout:
          message = l10n.scanCameraErrorTimeout;
          break;
        case NetworkIssueKind.serviceUnavailable:
        case NetworkIssueKind.serverError:
          message = l10n.scanCameraErrorUnavailable;
          break;
        case NetworkIssueKind.unauthorized:
        case NetworkIssueKind.unknown:
          break;
      }

      setState(() {
        _stage = _ScanStage.error;
        _statusText = message;
        _errorText = message;
      });
    }
  }

  void _clearCapturedState() {
    _capturedBytes = null;
    _capturedFilename = null;
    _qualityResult = null;
    _statusText = null;
    _errorText = null;
    _isCapturing = false;
  }

  Future<void> _retake() async {
    if (_stage == _ScanStage.previewChecking || _stage == _ScanStage.waiting) {
      return;
    }

    await _scanCameraCtrl.resume();
    if (!mounted) return;

    setState(() {
      _stage = _ScanStage.camera;
      _capturedBytes = null;
      _capturedFilename = null;
      _qualityResult = null;
      _statusText = null;
      _errorText = null;
      _isCapturing = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    switch (_stage) {
      case _ScanStage.camera:
        return _buildCameraStage();
      case _ScanStage.previewChecking:
      case _ScanStage.previewRejected:
      case _ScanStage.previewWarning:
      case _ScanStage.waiting:
      case _ScanStage.error:
        return _buildPreviewStage();
    }
  }

  Widget _buildCameraStage() {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Stack(
          children: [
            Positioned.fill(child: _buildCameraFeed()),
            Positioned(top: 0, left: 0, right: 0, child: _buildTopBar()),
            Positioned(
              bottom: 0,
              left: 0,
              right: 0,
              child: _buildCaptureBar(l10n),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPreviewStage() {
    final quality = _qualityResult;
    final isReject = _stage == _ScanStage.previewRejected;
    final isWarning = _stage == _ScanStage.previewWarning;
    final isWaiting = _stage == _ScanStage.waiting;
    final isChecking = _stage == _ScanStage.previewChecking;

    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Column(
          children: [
            _buildTopBar(),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final wide = constraints.maxWidth >= 720;
                    final preview = _PreviewPane(
                      bytes: _capturedBytes,
                      stage: _stage,
                      statusText: _statusText,
                      quality: quality,
                    );
                    final controls = _PreviewControls(
                      isChecking: isChecking,
                      isWaiting: isWaiting,
                      isReject: isReject,
                      isWarning: isWarning,
                      isError: _stage == _ScanStage.error,
                      hasCapturedImage: _capturedBytes != null,
                      errorText: _errorText,
                      onRetake: _retake,
                      onProceed: _continueAfterWarning,
                      onRetryUpload: _retryUpload,
                    );

                    if (wide) {
                      return Row(
                        children: [
                          Expanded(child: preview),
                          const SizedBox(width: 16),
                          Expanded(child: controls),
                        ],
                      );
                    }

                    return Column(
                      children: [
                        Expanded(child: preview),
                        const SizedBox(height: 12),
                        controls,
                      ],
                    );
                  },
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCameraFeed() {
    final camState = _scanCameraCtrl.state;
    final controller = _scanCameraCtrl.cameraController;

    if (camState == ScanCameraState.initializing) {
      return const Center(
        child: CircularProgressIndicator(color: Colors.white),
      );
    }

    if (camState == ScanCameraState.permissionDenied ||
        camState == ScanCameraState.unavailable) {
      final l10n = AppLocalizations.of(context);
      return _buildCameraError(
        icon: camState == ScanCameraState.permissionDenied
            ? Icons.no_photography_outlined
            : Icons.camera_outlined,
        message:
            _scanCameraCtrl.errorMessage ??
            (camState == ScanCameraState.permissionDenied
                ? l10n.scanCameraPermissionDenied
                : l10n.scanCameraUnavailable),
        actionLabel: l10n.commonRetry,
        onAction: _openCamera,
      );
    }

    if (controller != null && controller.value.isInitialized) {
      return ClipRect(
        child: OverflowBox(
          alignment: Alignment.center,
          child: FittedBox(
            fit: BoxFit.cover,
            child: SizedBox(
              width: controller.value.previewSize?.height ?? 1,
              height: controller.value.previewSize?.width ?? 1,
              child: CameraPreview(controller),
            ),
          ),
        ),
      );
    }

    return const SizedBox.shrink();
  }

  Widget _buildTopBar() {
    final l10n = AppLocalizations.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      color: Colors.black45,
      child: Row(
        children: [
          IconButton(
            onPressed: () => context.go('/create'),
            icon: const Icon(Icons.close, color: Colors.white),
            tooltip: l10n.scanCameraClose,
          ),
          Expanded(
            child: Text(
              l10n.scanCameraTitle,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 17,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          IconButton(
            onPressed: _showGuide,
            icon: const Icon(Icons.help_outline, color: Colors.white70),
            tooltip: l10n.scanCameraGuide,
          ),
        ],
      ),
    );
  }

  Widget _buildCaptureBar(AppLocalizations l10n) {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 14, 20, 24),
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
          Text(
            l10n.scanCameraHint,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 13,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 18),
          Center(
            child: GestureDetector(
              onTap: _isCapturing ? null : _captureFromCamera,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 160),
                width: _isCapturing ? 68 : 76,
                height: _isCapturing ? 68 : 76,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: _scanCameraCtrl.isReady
                      ? Colors.white
                      : Colors.white30,
                  border: Border.all(color: Colors.white70, width: 4),
                ),
                child: _isCapturing
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
          ),
        ],
      ),
    );
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

  void _showGuide() {
    final l10n = AppLocalizations.of(context);
    showModalBottomSheet<void>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                l10n.scanCameraGuideTitle,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 12),
              Text(l10n.scanCameraGuideStep1),
              const SizedBox(height: 8),
              Text(l10n.scanCameraGuideStep2),
              const SizedBox(height: 8),
              Text(l10n.scanCameraGuideStep3),
              const SizedBox(height: 8),
              Text(l10n.scanCameraGuideStep4),
            ],
          ),
        ),
      ),
    );
  }
}

class _PreviewPane extends StatelessWidget {
  const _PreviewPane({
    required this.bytes,
    required this.stage,
    required this.statusText,
    required this.quality,
  });

  final Uint8List? bytes;
  final _ScanStage stage;
  final String? statusText;
  final LocalQualityResult? quality;

  @override
  Widget build(BuildContext context) {
    final isWaiting = stage == _ScanStage.waiting;
    final isReject = stage == _ScanStage.previewRejected;
    final isWarning = stage == _ScanStage.previewWarning;
    final isChecking = stage == _ScanStage.previewChecking;

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(22),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(22),
        child: Stack(
          fit: StackFit.expand,
          children: [
            if (bytes != null)
              Image.memory(
                bytes!,
                fit: BoxFit.cover,
                filterQuality: FilterQuality.medium,
              )
            else
              const ColoredBox(color: Colors.black12),
            Container(color: Colors.black.withValues(alpha: 0.12)),
            Align(
              alignment: Alignment.bottomCenter,
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.bottomCenter,
                    end: Alignment.topCenter,
                    colors: [
                      Colors.black.withValues(alpha: 0.8),
                      Colors.transparent,
                    ],
                  ),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          isWaiting
                              ? Icons.hourglass_top_rounded
                              : isChecking
                              ? Icons.verified_outlined
                              : isReject
                              ? Icons.cancel_outlined
                              : isWarning
                              ? Icons.warning_amber_rounded
                              : Icons.image_outlined,
                          color: Colors.white,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            statusText ?? 'Đang xử lý ảnh...',
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ],
                    ),
                    if (isChecking || isWaiting) ...[
                      const SizedBox(height: 10),
                      const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      ),
                    ],
                    if (quality != null) ...[
                      const SizedBox(height: 10),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          _PreviewBadge('State: ${quality!.state}'),
                          if (quality!.rejectReason != null)
                            _PreviewBadge('Reason: ${quality!.rejectReason}'),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PreviewBadge extends StatelessWidget {
  const _PreviewBadge(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Text(
        label,
        style: const TextStyle(color: Colors.white, fontSize: 12),
      ),
    );
  }
}

class _PreviewControls extends StatelessWidget {
  const _PreviewControls({
    required this.isChecking,
    required this.isWaiting,
    required this.isReject,
    required this.isWarning,
    required this.isError,
    required this.hasCapturedImage,
    required this.errorText,
    required this.onRetake,
    required this.onProceed,
    required this.onRetryUpload,
  });

  final bool isChecking;
  final bool isWaiting;
  final bool isReject;
  final bool isWarning;
  final bool isError;
  final bool hasCapturedImage;
  final String? errorText;
  final VoidCallback onRetake;
  final VoidCallback onProceed;
  final VoidCallback onRetryUpload;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    String title;
    String subtitle;
    if (isChecking) {
      title = 'Đang kiểm tra ảnh';
      subtitle = 'Ứng dụng đang đánh giá chất lượng ảnh.';
    } else if (isWaiting) {
      title = 'Đang chờ xử lý ảnh';
      subtitle = 'Ảnh đã đạt, hệ thống đang xử lý.';
    } else if (isReject) {
      title = 'Ảnh chưa đạt';
      subtitle = errorText ?? 'Bạn nên chụp lại để kết quả chính xác hơn.';
    } else if (isWarning) {
      title = 'Ảnh tạm ổn';
      subtitle = errorText ?? 'Bạn có thể chụp lại hoặc vẫn tiếp tục.';
    } else {
      title = 'Ảnh đã chụp';
      subtitle = errorText ?? 'Kiểm tra ảnh hoặc chụp lại nếu cần.';
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(22),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            title,
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          Text(
            subtitle,
            style: const TextStyle(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 18),
          if (isChecking) ...[
            const LinearProgressIndicator(minHeight: 3),
            const SizedBox(height: 18),
          ],
          if (isWaiting) ...[
            const LinearProgressIndicator(minHeight: 3),
            const SizedBox(height: 18),
          ],
          if (isWarning) ...[
            ElevatedButton.icon(
              onPressed: onProceed,
              icon: const Icon(Icons.arrow_forward),
              label: Text(l10n.scanCameraProceed),
            ),
            const SizedBox(height: 10),
          ],
          if (isError && hasCapturedImage) ...[
            ElevatedButton.icon(
              onPressed: onRetryUpload,
              icon: const Icon(Icons.refresh),
              label: Text(l10n.commonRetry),
            ),
            const SizedBox(height: 10),
          ],
          OutlinedButton.icon(
            onPressed: (isChecking || isWaiting) ? null : onRetake,
            icon: const Icon(Icons.camera_alt_outlined),
            label: Text(l10n.scanCameraRetake),
          ),
        ],
      ),
    );
  }
}
