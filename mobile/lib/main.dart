import 'package:flutter/material.dart';

import 'scan/api_client.dart';
import 'scan/ml_kit_scanner.dart';
import 'scan/scan_screen.dart';

const apiUrl = String.fromEnvironment(
  'RXIE_API_URL',
  defaultValue: 'http://10.0.2.2:8000',
);

void main() {
  runApp(const RxieApp());
}

class RxieApp extends StatelessWidget {
  const RxieApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'RxIE Scanner',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff12645c)),
        useMaterial3: true,
      ),
      home: ScanScreen(
        scanner: MlKitPrescriptionScanner(),
        apiClient: RxieApiClient(baseUrl: apiUrl),
      ),
    );
  }
}
