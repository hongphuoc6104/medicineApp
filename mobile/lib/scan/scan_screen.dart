import 'package:flutter/material.dart';

import 'api_client.dart';
import 'models.dart';
import 'scanner.dart';

class ScanScreen extends StatefulWidget {
  const ScanScreen({required this.scanner, required this.apiClient, super.key});

  final PrescriptionScanner scanner;
  final RxieApiClient apiClient;

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  bool _busy = false;
  String? _error;
  List<ExtractedEntity> _entities = const [];

  Future<void> _scan() async {
    setState(() {
      _busy = true;
      _error = null;
      _entities = const [];
    });

    try {
      final request = await widget.scanner.scan();
      if (request == null) return;
      final entities = await widget.apiClient.extractEntities(request);
      if (mounted) setState(() => _entities = entities);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  void dispose() {
    widget.scanner.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('RxIE Scanner')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Icon(Icons.document_scanner_outlined, size: 64),
              const SizedBox(height: 12),
              Text(
                'Quét đơn thuốc và gửi văn bản OCR tới FastAPI. Ảnh không được tải lên.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
              const SizedBox(height: 20),
              FilledButton.icon(
                onPressed: _busy ? null : _scan,
                icon: const Icon(Icons.camera_alt_outlined),
                label: Text(_busy ? 'Đang xử lý...' : 'Quét đơn thuốc'),
              ),
              const SizedBox(height: 20),
              if (_busy) const LinearProgressIndicator(),
              if (_error case final error?)
                Card(
                  color: Theme.of(context).colorScheme.errorContainer,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: SelectableText(error),
                  ),
                ),
              if (!_busy && _error == null && _entities.isEmpty)
                const Expanded(
                  child: Center(child: Text('Chưa có kết quả trích xuất.')),
                ),
              if (_entities.isNotEmpty)
                Expanded(
                  child: ListView.separated(
                    itemCount: _entities.length,
                    separatorBuilder: (_, _) => const Divider(height: 1),
                    itemBuilder: (context, index) {
                      final entity = _entities[index];
                      final confidence = entity.confidence;
                      return ListTile(
                        title: Text(entity.text),
                        subtitle: Text(entity.type),
                        trailing: Text(
                          confidence == null
                              ? 'N/A'
                              : '${(confidence * 100).toStringAsFixed(1)}%',
                        ),
                      );
                    },
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
