import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http_parser/http_parser.dart';

import '../../../core/network/dio_client.dart';
import '../../home/domain/today_schedule.dart';
import '../domain/pill_verification.dart';

class PillVerificationRepository {
  PillVerificationRepository(this._dio);

  final Dio _dio;

  Future<PillVerificationSession> startSession({
    required TodayDose dose,
  }) async {
    final response = await _dio.post(
      '/pill-verifications/start',
      data: {
        'occurrenceId': dose.occurrenceId,
        'planId': dose.planId,
        'scheduledTime': dose.scheduledTime,
        'expectedMedications': [
          {
            'planId': dose.planId,
            'drugName': dose.drugName,
            if (dose.dosage != null) 'dosage': dose.dosage,
            if (dose.pillsPerDose != null) 'pillsPerDose': dose.pillsPerDose,
          },
        ],
      },
    );
    return PillVerificationSession.fromJson(
      response.data['data'] as Map<String, dynamic>,
    );
  }

  Future<PillVerificationSession> uploadImage({
    required String sessionId,
    required Uint8List imageBytes,
    required String filename,
    String mimeType = 'image/jpeg',
  }) async {
    final formData = FormData.fromMap({
      'file': MultipartFile.fromBytes(
        imageBytes,
        filename: filename,
        contentType: MediaType.parse(mimeType),
      ),
    });
    final response = await _dio.post(
      '/pill-verifications/$sessionId/image',
      data: formData,
      options: Options(contentType: 'multipart/form-data'),
    );
    return PillVerificationSession.fromJson(
      response.data['data'] as Map<String, dynamic>,
    );
  }

  Future<PillVerificationSession> assignDetection({
    required String sessionId,
    required int detectionIdx,
    required String status,
    String? assignedDrugName,
  }) async {
    final response = await _dio.post(
      '/pill-verifications/$sessionId/assign',
      data: {
        'detectionIdx': detectionIdx,
        'status': status,
        'assignedDrugName': assignedDrugName,
      },
    );
    return PillVerificationSession.fromJson(
      response.data['data'] as Map<String, dynamic>,
    );
  }

  Future<PillVerificationSession> confirm(String sessionId) async {
    final response = await _dio.post('/pill-verifications/$sessionId/confirm');
    return PillVerificationSession.fromJson(
      response.data['data'] as Map<String, dynamic>,
    );
  }
}

final pillVerificationRepositoryProvider = Provider<PillVerificationRepository>(
  (ref) {
    return PillVerificationRepository(ref.watch(dioProvider));
  },
);
