import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../../core/theme/app_theme.dart';
import '../../home/domain/today_schedule.dart';
import '../data/pill_verification_repository.dart';
import '../domain/pill_reference.dart';

class PillReferenceEnrollmentScreen extends ConsumerStatefulWidget {
  const PillReferenceEnrollmentScreen({super.key, required this.dose});

  final TodayDose dose;

  @override
  ConsumerState<PillReferenceEnrollmentScreen> createState() =>
      _PillReferenceEnrollmentScreenState();
}

class _PillReferenceEnrollmentScreenState
    extends ConsumerState<PillReferenceEnrollmentScreen> {
  final ImagePicker _picker = ImagePicker();

  PillReferenceSet? _referenceSet;
  bool _isLoading = true;
  bool _isSubmitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadOrCreate();
  }

  Future<void> _loadOrCreate() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final repo = ref.read(pillVerificationRepositoryProvider);
      final existing = await repo.getReferenceSets(planId: widget.dose.planId);
      if (existing.isNotEmpty) {
        setState(() {
          _referenceSet = existing.first;
          _isLoading = false;
        });
        return;
      }

      final created = await repo.startReferenceEnrollment(
        planId: widget.dose.planId,
        drugName: widget.dose.drugName,
      );
      setState(() {
        _referenceSet = created;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _addFrame(ImageSource source, {String side = 'front'}) async {
    final set = _referenceSet;
    if (set == null) return;

    final picked = await _picker.pickImage(source: source, imageQuality: 90);
    if (picked == null) return;

    setState(() {
      _isSubmitting = true;
      _error = null;
    });

    try {
      final bytes = await picked.readAsBytes();
      final repo = ref.read(pillVerificationRepositoryProvider);
      final updated = await repo.uploadReferenceFrame(
        referenceSetId: set.id,
        imageBytes: bytes,
        filename: picked.name,
        side: side,
        mimeType: _guessMime(picked.path),
      );

      setState(() {
        _referenceSet = updated;
        _isSubmitting = false;
      });
    } on DioException catch (e) {
      setState(() {
        _error = e.message ?? 'Không thể tải ảnh mẫu';
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

  Future<void> _finalize() async {
    final set = _referenceSet;
    if (set == null || set.images.isEmpty) return;

    setState(() {
      _isSubmitting = true;
      _error = null;
    });

    try {
      final repo = ref.read(pillVerificationRepositoryProvider);
      final updated = await repo.finalizeReferenceEnrollment(
        referenceSetId: set.id,
      );
      setState(() {
        _referenceSet = updated;
        _isSubmitting = false;
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Đã lưu mẫu viên thuốc thành công')),
      );
      Navigator.pop(context, true);
    } on DioException catch (e) {
      setState(() {
        _error = e.message ?? 'Không thể hoàn tất lưu mẫu';
        _isSubmitting = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isSubmitting = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Chụp mẫu viên thuốc')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.dose.drugName,
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Đặt đúng một viên thuốc vào giữa khung hình, nền sáng rõ, không che bóng.',
                  style: TextStyle(color: AppColors.textSecondary),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _TagChip(
                      label: 'Ảnh đã lưu',
                      value: '${_referenceSet?.imageCount ?? 0}',
                    ),
                    _TagChip(
                      label: 'Trạng thái',
                      value: _referenceSet?.status == 'ready'
                          ? 'Sẵn sàng'
                          : 'Đang thu mẫu',
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                _error!,
                style: const TextStyle(color: AppColors.error),
              ),
            ),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _isSubmitting
                      ? null
                      : () => _addFrame(ImageSource.camera, side: 'front'),
                  icon: const Icon(Icons.photo_camera_outlined),
                  label: const Text('Chụp mặt chính'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _isSubmitting
                      ? null
                      : () => _addFrame(ImageSource.camera, side: 'back'),
                  icon: const Icon(Icons.flip_camera_android_outlined),
                  label: const Text('Quét mặt còn lại'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          OutlinedButton.icon(
            onPressed: _isSubmitting
                ? null
                : () => _addFrame(ImageSource.gallery, side: 'other'),
            icon: const Icon(Icons.upload_file_outlined),
            label: const Text('Tải ảnh có sẵn'),
          ),
          const SizedBox(height: 18),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.surfaceSoft,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Danh sách ảnh mẫu',
                  style: TextStyle(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 8),
                if ((_referenceSet?.images ?? const []).isEmpty)
                  const Text(
                    'Chưa có ảnh mẫu. Bạn hãy chụp ít nhất 1 ảnh trước khi hoàn tất.',
                  )
                else
                  ..._referenceSet!.images.map(
                    (img) => Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: Row(
                        children: [
                          const Icon(
                            Icons.check_circle_outline,
                            size: 18,
                            color: AppColors.success,
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Ảnh ${img.side == 'back'
                                  ? 'mặt sau'
                                  : img.side == 'front'
                                  ? 'mặt chính'
                                  : 'bổ sung'}',
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          ElevatedButton.icon(
            onPressed: _isSubmitting || (_referenceSet?.images.isEmpty ?? true)
                ? null
                : _finalize,
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
            label: const Text('Hoàn tất lưu mẫu'),
          ),
        ],
      ),
    );
  }
}

class _TagChip extends StatelessWidget {
  const _TagChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.surfaceHigh,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Text('$label: $value', style: const TextStyle(fontSize: 12)),
    );
  }
}
