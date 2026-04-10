import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http_parser/http_parser.dart';

import '../../../core/network/dio_client.dart';
import '../../home/domain/today_schedule.dart';
import '../domain/pill_verification.dart';
import '../domain/pill_reference.dart';

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
        'expectedMedications': dose.expectedMedications.isNotEmpty
            ? dose.expectedMedications
                  .map(
                    (med) => {
                      'planId': med.planId,
                      'drugName': med.drugName,
                      if (med.occurrenceId != null)
                        'occurrenceId': med.occurrenceId,
                      if (med.dosage != null) 'dosage': med.dosage,
                      if (med.pillsPerDose != null)
                        'pillsPerDose': med.pillsPerDose,
                    },
                  )
                  .toList()
            : [
                {
                  'planId': dose.planId,
                  'drugName': dose.drugName,
                  'occurrenceId': dose.occurrenceId,
                  if (dose.dosage != null) 'dosage': dose.dosage,
                  if (dose.pillsPerDose != null)
                    'pillsPerDose': dose.pillsPerDose,
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
    String? assignedPlanId,
    String? assignedDrugName,
  }) async {
    final response = await _dio.post(
      '/pill-verifications/$sessionId/assign',
      data: {
        'detectionIdx': detectionIdx,
        'status': status,
        'assignedPlanId': assignedPlanId,
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

  Future<PillReferenceSet> startReferenceEnrollment({
    required String planId,
    required String drugName,
  }) async {
    final response = await _dio.post(
      '/pill-references/enroll/start',
      data: {'planId': planId, 'drugNameSnapshot': drugName},
    );

    return PillReferenceSet.fromJson(
      response.data['data'] as Map<String, dynamic>,
    );
  }

  Future<PillReferenceSet> uploadReferenceFrame({
    required String referenceSetId,
    required Uint8List imageBytes,
    required String filename,
    String side = 'front',
    String mimeType = 'image/jpeg',
  }) async {
    final formData = FormData.fromMap({
      'file': MultipartFile.fromBytes(
        imageBytes,
        filename: filename,
        contentType: MediaType.parse(mimeType),
      ),
      'side': side,
    });

    final response = await _dio.post(
      '/pill-references/$referenceSetId/frame',
      data: formData,
      options: Options(contentType: 'multipart/form-data'),
    );

    return PillReferenceSet.fromJson(
      response.data['data'] as Map<String, dynamic>,
    );
  }

  Future<PillReferenceSet> finalizeReferenceEnrollment({
    required String referenceSetId,
    List<String> confirmedImageIds = const [],
  }) async {
    final response = await _dio.post(
      '/pill-references/$referenceSetId/finalize',
      data: {'confirmedImageIds': confirmedImageIds},
    );

    return PillReferenceSet.fromJson(
      response.data['data'] as Map<String, dynamic>,
    );
  }

  Future<List<PillReferenceSet>> getReferenceSets({String? planId}) async {
    final response = await _dio.get(
      '/pill-references',
      queryParameters: {
        if (planId != null && planId.isNotEmpty) 'planId': planId,
      },
    );

    final list = response.data['data'] as List<dynamic>? ?? const [];
    return list
        .map((item) => PillReferenceSet.fromJson(item as Map<String, dynamic>))
        .toList();
  }
}

final pillVerificationRepositoryProvider = Provider<PillVerificationRepository>(
  (ref) {
    return PillVerificationRepository(ref.watch(dioProvider));
  },
);
