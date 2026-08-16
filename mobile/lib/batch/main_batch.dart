import 'dart:io';
import 'package:flutter/material.dart';
import 'batch_ocr_runner.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const BatchOcrApp());
}

class BatchOcrApp extends StatelessWidget {
  const BatchOcrApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'RxIE Batch OCR',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const BatchOcrScreen(),
    );
  }
}

class BatchOcrScreen extends StatefulWidget {
  const BatchOcrScreen({super.key});

  @override
  State<BatchOcrScreen> createState() => _BatchOcrScreenState();
}

class _BatchOcrScreenState extends State<BatchOcrScreen> {
  final List<String> _logs = [];
  bool _running = false;
  final ScrollController _scrollController = ScrollController();
  final BatchOcrRunner _runner = BatchOcrRunner();

  @override
  void initState() {
    super.initState();
    // Tự động kích hoạt batch OCR khi khởi động
    WidgetsBinding.instance.addPostFrameCallback((_) => _startBatch());
  }

  @override
  void dispose() {
    _runner.close();
    _scrollController.dispose();
    super.dispose();
  }

  void _addLog(String msg) {
    setState(() => _logs.add(msg));
    debugPrint(msg);
    Future.delayed(const Duration(milliseconds: 50), () {
      if (_scrollController.hasClients) {
        _scrollController.jumpTo(_scrollController.position.maxScrollExtent);
      }
    });
  }

  Future<void> _startBatch() async {
    if (_running) return;
    setState(() {
      _running = true;
      _logs.clear();
    });

    _addLog('--- BẮT ĐẦU TIẾN TRÌNH BATCH OCR ---');

    final inputDir = Directory('/data/data/com.medicineapp.medicine_app/files/input');
    final outputDir = Directory('/data/data/com.medicineapp.medicine_app/files/output');

    try {
      await _runner.runBatch(
        inputDir: inputDir,
        outputDir: outputDir,
        onLog: _addLog,
      );
    } catch (e, st) {
      _addLog('Lỗi ngoài ý muốn: $e\n$st');
    } finally {
      if (mounted) {
        setState(() => _running = false);
      }
      _addLog('=== HOÀN TẤT TIẾN TRÌNH ===');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Batch ML Kit OCR Runner'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _running ? null : _startBatch,
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_running) const LinearProgressIndicator(),
            const SizedBox(height: 8),
            Text(
              _running ? 'Đang thực hiện OCR...' : 'Sẵn sàng / Đã hoàn thành',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            Expanded(
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.black87,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: ListView.builder(
                  controller: _scrollController,
                  itemCount: _logs.length,
                  itemBuilder: (context, index) {
                    return Text(
                      _logs[index],
                      style: const TextStyle(
                        color: Colors.greenAccent,
                        fontFamily: 'monospace',
                        fontSize: 12,
                      ),
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
}
