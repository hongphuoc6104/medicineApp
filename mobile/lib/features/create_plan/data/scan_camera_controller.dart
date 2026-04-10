import 'dart:async';

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';

/// Lifecycle state of the camera controller.
enum ScanCameraState {
  initializing,
  ready,
  capturing,
  unavailable,
  permissionDenied,
}

/// Manages the Flutter camera lifecycle for the scan screen.
///
/// Keeps all camera logic outside the widget body.
/// Dispose must be called when the screen leaves the tree.
class ScanCameraController extends ChangeNotifier {
  ScanCameraState _state = ScanCameraState.initializing;
  CameraController? _cameraController;
  String? _errorMessage;

  ScanCameraState get state => _state;
  CameraController? get cameraController => _cameraController;
  String? get errorMessage => _errorMessage;

  /// Optional callback to notify the UI that an auto-capture was performed.
  Function(Uint8List bytes)? onAutoCaptured;

  bool _isEvaluatingFrame = false;
  DateTime _lastEvaluateTime = DateTime.now();

  bool get isReady =>
      _state == ScanCameraState.ready &&
      _cameraController != null &&
      _cameraController!.value.isInitialized;

  /// Initialize and start live preview using the first back camera.
  Future<void> initialize() async {
    _setState(ScanCameraState.initializing);

    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        _errorMessage = 'Không tìm thấy camera trên thiết bị.';
        _setState(ScanCameraState.unavailable);
        return;
      }

      // Prefer back camera; fallback to first available.
      final camera = cameras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.back,
        orElse: () => cameras.first,
      );

      // Note: Do not force ImageFormatGroup.jpeg since we want to use startImageStream.
      // Flutter will use YUV420 on Android and BGRA8888 on iOS by default.
      final controller = CameraController(
        camera,
        ResolutionPreset.max,
        enableAudio: false,
      );

      await controller.initialize();

      _cameraController = controller;
      _errorMessage = null;
      _setState(ScanCameraState.ready);

      // Start the auto-capture stream
      await _startAutoCaptureStream();
    } on CameraException catch (e) {
      if (e.code == 'CameraAccessDenied' ||
          e.code == 'CameraAccessDeniedWithoutPrompt' ||
          e.code == 'CameraAccessRestricted') {
        _errorMessage =
            'Quyền camera bị từ chối. Vui lòng cấp quyền trong Cài đặt.';
        _setState(ScanCameraState.permissionDenied);
      } else {
        _errorMessage = 'Không thể khởi động camera: ${e.description}';
        _setState(ScanCameraState.unavailable);
      }
    } catch (e) {
      _errorMessage = 'Lỗi camera không xác định: $e';
      _setState(ScanCameraState.unavailable);
    }
  }

  /// Capture a single frame from the live preview.
  /// Returns JPEG bytes or null if capture failed.
  Future<Uint8List?> capturePhoto() async {
    if (!isReady) return null;
    _setState(ScanCameraState.capturing);
    try {
      final xfile = await _cameraController!.takePicture();
      final bytes = await xfile.readAsBytes();
      _setState(ScanCameraState.ready);
      return bytes;
    } catch (e) {
      _errorMessage = 'Chụp ảnh thất bại: $e';
      _setState(ScanCameraState.ready);
      return null;
    }
  }

  /// Called when the app is paused (e.g. home button pressed).
  Future<void> pause() async {
    if (_cameraController != null && _cameraController!.value.isInitialized) {
      await _cameraController!.pausePreview();
    }
  }

  /// Called when the app is resumed.
  Future<void> resume() async {
    if (_cameraController != null && _cameraController!.value.isInitialized) {
      await _cameraController!.resumePreview();
    }
  }

  void _setState(ScanCameraState newState) {
    _state = newState;
    notifyListeners();
  }

  Future<void> _startAutoCaptureStream() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) return;
    if (_cameraController!.value.isStreamingImages) return;

    try {
      await _cameraController!.startImageStream((CameraImage image) {
        if (_state != ScanCameraState.ready) return;
        if (_isEvaluatingFrame) return;

        // Limiting frame evaluation rate to 1 FPS
        if (DateTime.now().difference(_lastEvaluateTime).inMilliseconds < 1000) return;

        _isEvaluatingFrame = true;
        _lastEvaluateTime = DateTime.now();

        final formatType = image.format.group == ImageFormatGroup.bgra8888 ? 1 : 0;
        final data = {
          'width': image.width,
          'height': image.height,
          'bytes': image.planes[0].bytes,
          'format': formatType,
        };

        compute(_evaluateImageFrame, data).then((result) async {
          if (_state != ScanCameraState.ready) {
            _isEvaluatingFrame = false;
            return;
          }

          final double edgeScore = result['edgeScore'] as double;
          final double glareRatio = result['glareRatio'] as double;

          // Auto-capture criteria
          if (edgeScore >= 16.0 && glareRatio < 0.1) {
            _setState(ScanCameraState.capturing);
            try {
              await _cameraController!.stopImageStream();
              await Future.delayed(const Duration(milliseconds: 200));
              final xfile = await _cameraController!.takePicture();
              final bytes = await xfile.readAsBytes();
              _setState(ScanCameraState.ready);
              onAutoCaptured?.call(bytes);
            } catch (e) {
              _errorMessage = 'Lỗi tự động chụp: $e';
              _setState(ScanCameraState.ready);
              _startAutoCaptureStream(); // Restart stream on failure
            }
          }
          _isEvaluatingFrame = false;
        }).catchError((_) {
          _isEvaluatingFrame = false;
        });
      });
    } catch (e) {
      // Ignored if stream fails
    }
  }

  @override
  void dispose() {
    if (_cameraController?.value.isStreamingImages == true) {
      _cameraController?.stopImageStream();
    }
    _cameraController?.dispose();
    super.dispose();
  }
}

// Runs in an isolate to prevent UI stutters
Map<String, dynamic> _evaluateImageFrame(Map<String, dynamic> data) {
  final int width = data['width'];
  final int height = data['height'];
  final Uint8List bytes = data['bytes'];
  final int format = data['format']; // 0 for YUV (plane 0 is Y), 1 for BGRA

  int brightPixels = 0;
  double edgeSum = 0;
  int count = 0;

  // Sample every 4th pixel to make it extremely fast
  for (int y = 5; y < height - 5; y += 4) {
    for (int x = 5; x < width - 5; x += 4) {
      int val = 0;
      int left = 0;
      if (format == 0) {
        // YUV: Plane 0 is pure Luminance (Y)
        int idx = y * width + x;
        val = bytes[idx];
        left = bytes[idx - 1]; // pixel to the left
      } else {
        // BGRA: Plane 0 is interleaved B G R A
        int idx = (y * width + x) * 4;
        val = (0.299 * bytes[idx + 2] + 0.587 * bytes[idx + 1] + 0.114 * bytes[idx]).round();
        left = (0.299 * bytes[idx - 4 + 2] + 0.587 * bytes[idx - 4 + 1] + 0.114 * bytes[idx - 4]).round();
      }

      if (val >= 245) brightPixels++;
      edgeSum += (val - left).abs();
      count++;
    }
  }

  return {
    'glareRatio': brightPixels / count,
    'edgeScore': edgeSum / count,
  };
}
