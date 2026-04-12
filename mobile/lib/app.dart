import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/data/auth_notifier.dart';
import 'l10n/app_localizations.dart';

/// Root app widget with Riverpod + GoRouter + healthcare light theme.
///
/// Localization:
///   - default locale: vi (Vietnamese)
///   - delegates: AppLocalizations + Flutter material/cupertino/widgets
class MedicineApp extends ConsumerWidget {
  const MedicineApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(authNotifierProvider);
    final router = ref.watch(routerProvider);

    return MaterialApp.router(
      title: 'Thuốc Của Tôi',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      routerConfig: router,
      // ── Localization ──────────────────────────────────────────────
      locale: const Locale('vi'),
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
    );
  }
}
