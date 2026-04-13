import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'package:medicine_app/main.dart' as app;

class _QaUser {
  const _QaUser({required this.email, required this.password});

  final String email;
  final String password;
}

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  Future<void> pumpApp(WidgetTester tester) async {
    app.main();
    await tester.pumpAndSettle(const Duration(seconds: 4));
  }

  Future<void> waitFor(
    WidgetTester tester,
    Finder finder, {
    Duration timeout = const Duration(seconds: 45),
  }) async {
    final end = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(end)) {
      await tester.pump(const Duration(milliseconds: 300));
      if (finder.evaluate().isNotEmpty) {
        await tester.pumpAndSettle(const Duration(seconds: 1));
        return;
      }
    }
    expect(finder, findsWidgets);
  }

  Future<void> screenshot(String name) async {
    await binding.takeScreenshot(name);
  }

  Future<void> openRegister(WidgetTester tester) async {
    final registerLink = find.textContaining('Đăng ký').last;
    await tester.ensureVisible(registerLink);
    await tester.tap(registerLink, warnIfMissed: false);
    await tester.pumpAndSettle(const Duration(seconds: 2));
  }

  Future<void> openLogin(WidgetTester tester) async {
    final loginLink = find.textContaining('Đăng nhập').last;
    await tester.ensureVisible(loginLink);
    await tester.tap(loginLink, warnIfMissed: false);
    await tester.pumpAndSettle(const Duration(seconds: 2));
  }

  _QaUser userFromEnv(String prefix) {
    final email = switch (prefix) {
      'QA_EMPTY' => const String.fromEnvironment('QA_EMPTY_EMAIL'),
      'QA_FULL' => const String.fromEnvironment('QA_FULL_EMAIL'),
      _ => '',
    };
    final password = switch (prefix) {
      'QA_EMPTY' => const String.fromEnvironment('QA_EMPTY_PASSWORD'),
      'QA_FULL' => const String.fromEnvironment('QA_FULL_PASSWORD'),
      _ => '',
    };
    if (email.isEmpty || password.isEmpty) {
      throw StateError(
        'Missing dart-define for ${prefix}_EMAIL/${prefix}_PASSWORD',
      );
    }
    return _QaUser(email: email, password: password);
  }

  Future<void> loginWithUi(WidgetTester tester, _QaUser user) async {
    final textFields = find.byType(TextField);
    expect(textFields, findsNWidgets(2));
    await tester.enterText(textFields.at(0), user.email);
    await tester.enterText(textFields.at(1), user.password);
    await tester.tap(find.widgetWithText(ElevatedButton, 'Đăng nhập'));
    await tester.pumpAndSettle(const Duration(seconds: 6));
  }

  Future<void> logoutFromSettings(WidgetTester tester) async {
    await tester.tap(find.byIcon(Icons.settings_outlined).first);
    await tester.pumpAndSettle(const Duration(seconds: 3));
    expect(find.text('Cài đặt'), findsOneWidget);
    await tester.tap(find.widgetWithText(OutlinedButton, 'Đăng xuất'));
    await tester.pumpAndSettle(const Duration(seconds: 4));
  }

  Future<void> tapMaterialBack(WidgetTester tester) async {
    final back = find.byIcon(Icons.arrow_back);
    if (back.evaluate().isNotEmpty) {
      await tester.tap(back.first);
    } else {
      await tester.tapAt(const Offset(32, 48));
    }
    await tester.pumpAndSettle(const Duration(seconds: 2));
  }

  testWidgets('QA smoke with screenshots', (tester) async {
    final emptyUser = userFromEnv('QA_EMPTY');
    final populatedUser = userFromEnv('QA_FULL');

    await binding.convertFlutterSurfaceToImage();
    await pumpApp(tester);

    await waitFor(tester, find.byType(TextField));
    expect(find.text('Quản lý đơn thuốc thông minh'), findsOneWidget);
    await screenshot('02_login_default');

    await openRegister(tester);
    expect(find.text('Tạo tài khoản'), findsOneWidget);
    await screenshot('04_register_default');

    await openLogin(tester);

    await loginWithUi(tester, emptyUser);
    expect(find.textContaining('Bắt đầu quản lý thuốc'), findsOneWidget);
    await screenshot('05_home_empty');

    await tester.tap(find.text('Kế hoạch').last);
    await tester.pumpAndSettle(const Duration(seconds: 2));
    await screenshot('09_plans_list_empty');

    await tester.tap(find.text('Lịch sử').last);
    await tester.pumpAndSettle(const Duration(seconds: 2));
    expect(find.textContaining('Chưa có kế hoạch cũ nào'), findsOneWidget);
    await screenshot('13_history_empty');

    await logoutFromSettings(tester);
    expect(find.text('Uống thuốc'), findsOneWidget);

    await loginWithUi(tester, populatedUser);
    await waitFor(tester, find.text('Trang chủ'));
    await screenshot('06_home_due');

    if (find.text('Đã uống').evaluate().isNotEmpty) {
      await tester.tap(find.text('Đã uống').first);
      await tester.pumpAndSettle(const Duration(seconds: 4));
      await screenshot('06_home_after_taken');
    }

    await tester.tap(find.text('Kế hoạch').last);
    await tester.pumpAndSettle(const Duration(seconds: 3));
    expect(find.text('Paracetamol demo'), findsOneWidget);
    await screenshot('09_plans_list');

    await tester.tap(find.text('Paracetamol demo').first);
    await tester.pumpAndSettle(const Duration(seconds: 3));
    expect(find.text('Chỉnh sửa thuốc và lịch'), findsWidgets);
    await screenshot('10_plan_detail_single');

    await tester.tap(find.text('Chỉnh sửa thuốc và lịch').first);
    await tester.pumpAndSettle(const Duration(seconds: 3));
    await screenshot('12_plan_edit_drugs');

    await tapMaterialBack(tester);
    await tapMaterialBack(tester);

    await tester.tap(find.byIcon(Icons.add_circle_outline).first);
    await tester.pumpAndSettle(const Duration(seconds: 2));
    await waitFor(tester, find.textContaining('Quét'));
    await screenshot('15_create_plan_options');

    await tester.tap(find.textContaining('Dùng lại').first);
    await tester.pumpAndSettle(const Duration(seconds: 3));
    expect(find.textContaining('Dùng lại kế hoạch cũ'), findsOneWidget);
    await screenshot('18_reuse_old_plan');

    await tapMaterialBack(tester);

    await tester.tap(find.text('Lịch sử').last);
    await tester.pumpAndSettle(const Duration(seconds: 3));
    expect(find.text('Kế hoạch cũ'), findsOneWidget);
    await screenshot('14_history_week_grid');

    await tester.tap(find.byIcon(Icons.settings_outlined).first);
    await tester.pumpAndSettle(const Duration(seconds: 2));
    expect(find.text('Cài đặt'), findsOneWidget);
    await screenshot('23_settings');

    await tapMaterialBack(tester);
    await tester.tap(find.text('Trang chủ').last);
    await tester.pumpAndSettle(const Duration(seconds: 2));

    final drugLookup = find.textContaining('Tra cứu thuốc');
    expect(drugLookup, findsWidgets);
    await tester.tap(drugLookup.first);
    await tester.pumpAndSettle(const Duration(seconds: 2));
    expect(find.text('Thông tin thuốc'), findsOneWidget);
    await screenshot('21_drug_search_default');

    final drugField = find.byType(TextField).first;
    await tester.enterText(drugField, 'paracetamol');
    await tester.pumpAndSettle(const Duration(seconds: 4));
    await screenshot('21_drug_search_results');
  });
}
