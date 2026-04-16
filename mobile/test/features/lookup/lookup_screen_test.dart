import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:medicine_app/features/lookup/presentation/lookup_screen.dart';
import 'package:medicine_app/l10n/app_localizations.dart';

Widget _buildTestApp() {
  return ProviderScope(
    child: MaterialApp(
      locale: const Locale('vi'),
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      home: const LookupScreen(),
    ),
  );
}

void main() {
  testWidgets('renders lookup tab sections', (tester) async {
    await tester.pumpWidget(_buildTestApp());
    await tester.pumpAndSettle();

    expect(find.text('Tra cứu'), findsWidgets);
    expect(find.text('Thuốc'), findsOneWidget);
    expect(find.text('Tương tác'), findsOneWidget);
    expect(find.text('Hoạt chất'), findsOneWidget);
    expect(find.text('Tra cứu thuốc'), findsOneWidget);
  });

  testWidgets('shows validation message when checking interactions too early', (
    tester,
  ) async {
    await tester.pumpWidget(_buildTestApp());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Tương tác'));
    await tester.pumpAndSettle();
    expect(find.text('Kiểm tra tương tác theo thuốc'), findsOneWidget);

    await tester.tap(find.text('Kiểm tra tương tác'));
    await tester.pumpAndSettle();

    expect(find.text('Cần chọn ít nhất 2 thuốc để kiểm tra.'), findsOneWidget);
  });
}
