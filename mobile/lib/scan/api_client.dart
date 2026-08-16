import 'dart:convert';

import 'package:http/http.dart' as http;

import 'models.dart';

class RxieApiException implements Exception {
  const RxieApiException(this.message);

  final String message;

  @override
  String toString() => message;
}

class RxieApiClient {
  RxieApiClient({required String baseUrl, http.Client? client})
    : _baseUri = Uri.parse(baseUrl),
      _client = client ?? http.Client();

  final Uri _baseUri;
  final http.Client _client;

  Future<List<ExtractedEntity>> extractEntities(EntityRequest request) async {
    final uri = _baseUri.resolve('/entities');
    late final http.Response response;
    try {
      response = await _client
          .post(
            uri,
            headers: const {'content-type': 'application/json'},
            body: jsonEncode(request.toJson()),
          )
          .timeout(const Duration(seconds: 45));
    } catch (error) {
      throw RxieApiException('Không thể kết nối $uri: $error');
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw RxieApiException(
        'FastAPI trả về HTTP ${response.statusCode}: ${response.body}',
      );
    }

    try {
      return parseEntityResponse(jsonDecode(utf8.decode(response.bodyBytes)));
    } on FormatException catch (error) {
      throw RxieApiException('Phản hồi FastAPI không hợp lệ: ${error.message}');
    }
  }
}
