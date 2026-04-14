import 'package:flutter_test/flutter_test.dart';
import 'package:medicine_app/features/reconciliation/domain/reconciliation_result.dart';

void main() {
  group('Reconciliation Contract Tests', () {
    test('Should parse TransitionOfCare payload correctly', () {
      final jsonResponse = {
        "compareType": "scan_vs_active_plan",
        "summary": {
          "added": 1,
          "removed": 0,
          "substitutions": 0,
          "duplicates": 1,
          "strengthChanged": 0,
          "dosageFormChanged": 0,
          "manualReview": 0,
          "hasChanges": true,
          "requiresManualReview": false
        },
        "transitionOfCare": {
          "know": [
            "Kiểm tra xem có thuốc nào bị trùng hoạt chất hoặc trùng mục đích dùng."
          ],
          "check": [
            "Kiểm tra xem có thuốc nào bị trùng hoạt chất hoặc trùng mục đích dùng."
          ],
          "ask": [
            "Hỏi lại bác sĩ hoặc dược sĩ nếu thấy hai thuốc có vẻ cùng hoạt chất."
          ],
          "riskCards": [
            {
              "level": "warning",
              "label": "Có thể trùng thuốc",
              "detail": "Phát hiện ít nhất một hoạt chất xuất hiện ở nhiều thuốc trong đơn mới."
            }
          ]
        }
      };

      final result = ReconciliationResult.fromJson(jsonResponse);

      expect(result.compareType, "scan_vs_active_plan");
      expect(result.summary.added, 1);
      expect(result.summary.duplicates, 1);
      expect(result.summary.hasChanges, true);

      final toc = result.transitionOfCare;
      expect(toc.know.length, 1);
      expect(toc.check.first, contains("trùng hoạt chất"));
      expect(toc.ask.length, 1);
      
      expect(toc.riskCards.length, 1);
      final card = toc.riskCards.first;
      expect(card.level, "warning");
      expect(card.label, "Có thể trùng thuốc");
    });

    test('Should handle empty TransitionOfCare gracefully', () {
      final jsonResponse = {
        "compareType": "scan_vs_active_plan",
        "summary": {
          "added": 0,
          "removed": 0,
          "substitutions": 0,
          "duplicates": 0,
          "strengthChanged": 0,
          "dosageFormChanged": 0,
          "manualReview": 0,
          "hasChanges": false,
          "requiresManualReview": false
        },
        "transitionOfCare": {
          "know": [],
          "check": [],
          "ask": [],
          "riskCards": []
        }
      };

      final result = ReconciliationResult.fromJson(jsonResponse);
      expect(result.transitionOfCare.riskCards, isEmpty);
      expect(result.summary.hasChanges, false);
    });
    
    test('Should handle missing fields in payload', () {
      final jsonResponse = {
        "compareType": "dispensed_text_vs_active_plan",
        // missing summary and transitionOfCare objects
      };

      final result = ReconciliationResult.fromJson(jsonResponse);
      expect(result.compareType, "dispensed_text_vs_active_plan");
      expect(result.summary.added, 0); // defaults to 0
      expect(result.transitionOfCare.riskCards, isEmpty); // defaults to empty
    });
  });
}
