import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/login_screen.dart';
import '../../features/auth/presentation/register_screen.dart';
import '../../shared/widgets/main_shell.dart';
import '../../features/home/presentation/home_screen.dart';
import '../../features/create_plan/presentation/create_plan_screen.dart';
import '../../features/create_plan/presentation/scan_camera_screen.dart';
import '../../features/create_plan/presentation/scan_review_screen.dart';
import '../../features/create_plan/presentation/edit_drugs_screen.dart';
import '../../features/create_plan/presentation/set_schedule_screen.dart';
import '../../features/create_plan/domain/plan.dart';
import '../../features/create_plan/domain/scan_result.dart';
import '../../features/drug/presentation/drug_search_screen.dart';
import '../../features/drug/presentation/drug_detail_screen.dart';
import '../../features/drug/data/drug_repository.dart';
import '../../features/history/presentation/history_screen.dart';
import '../../features/history/presentation/scan_history_detail_screen.dart';
import '../../features/plan/presentation/plan_detail_screen.dart';
import '../../features/plan/presentation/plan_list_screen.dart';
import '../../features/pill_verification/presentation/pill_verification_screen.dart';
import '../../features/settings/presentation/settings_screen.dart';
import '../../features/home/domain/today_schedule.dart';

/// Tri-state auth: loading (cold start) → authenticated / unauthenticated.
enum AuthStatus { loading, authenticated, unauthenticated }

/// Auth state notifier — tracks authentication status.
class AuthStateNotifier extends Notifier<AuthStatus> {
  @override
  AuthStatus build() => AuthStatus.loading;

  void setAuthenticated() => state = AuthStatus.authenticated;
  void setUnauthenticated() => state = AuthStatus.unauthenticated;
}

final authStateProvider = NotifierProvider<AuthStateNotifier, AuthStatus>(
  AuthStateNotifier.new,
);

final routerProvider = Provider<GoRouter>((ref) {
  final authStatus = ref.watch(authStateProvider);

  return GoRouter(
    initialLocation: '/boot',
    redirect: (context, state) {
      final onAuthPage =
          state.matchedLocation == '/login' ||
          state.matchedLocation == '/register';
      final onBoot = state.matchedLocation == '/boot';

      if (authStatus == AuthStatus.loading) {
        return onBoot ? null : '/boot';
      }

      if (authStatus == AuthStatus.unauthenticated) {
        return onAuthPage ? null : '/login';
      }

      if (onBoot || onAuthPage) return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/boot', builder: (context, state) => const _BootScreen()),
      // ── Auth (outside bottom nav) ──
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegisterScreen(),
      ),

      // ── Create Plan Flow (outside bottom nav) ──
      GoRoute(
        path: '/create/scan',
        builder: (context, state) => const ScanCameraScreen(),
      ),
      GoRoute(
        path: '/create/edit',
        builder: (context, state) {
          final drugs = state.extra as List<PlanDrugItem>? ?? [];
          return EditDrugsScreen(initialDrugs: drugs);
        },
      ),
      GoRoute(
        path: '/create/review',
        builder: (context, state) {
          final result = state.extra as ScanResult?;
          return ScanReviewScreen(
            result: result ?? const ScanResult(scanId: '', drugs: []),
          );
        },
      ),
      GoRoute(
        path: '/create/schedule',
        builder: (context, state) {
          final drugs = state.extra as List<PlanDrugItem>? ?? [];
          return SetScheduleScreen(drugs: drugs);
        },
      ),

      // ── Main Shell (Bottom Nav — 4 tabs) ──
      ShellRoute(
        builder: (context, state, child) => MainShell(child: child),
        routes: [
          GoRoute(
            path: '/home',
            pageBuilder: (context, state) =>
                const NoTransitionPage(child: HomeScreen()),
          ),
          GoRoute(
            path: '/create',
            pageBuilder: (context, state) =>
                const NoTransitionPage(child: CreatePlanScreen()),
          ),
          GoRoute(
            path: '/plans',
            pageBuilder: (context, state) =>
                const NoTransitionPage(child: PlanListScreen()),
          ),
          GoRoute(
            path: '/plans/:id',
            builder: (context, state) =>
                PlanDetailScreen(planId: state.pathParameters['id'] ?? ''),
          ),
          GoRoute(
            path: '/pill-verify',
            builder: (context, state) {
              final dose = state.extra as TodayDose?;
              return PillVerificationScreen(
                dose:
                    dose ??
                    const TodayDose(
                      occurrenceId: '',
                      planId: '',
                      drugName: '',
                      time: '',
                      scheduledTime: '',
                      status: 'pending',
                    ),
              );
            },
          ),
          GoRoute(
            path: '/drugs',
            pageBuilder: (context, state) =>
                const NoTransitionPage(child: DrugSearchScreen()),
          ),
          GoRoute(
            path: '/drugs/detail',
            builder: (context, state) {
              final extra = state.extra as Map<String, dynamic>?;
              final details = extra?['details'];
              return DrugDetailScreen(
                details: details is DrugDetails
                    ? details
                    : const DrugDetails(name: 'Thong tin thuoc'),
                activeIngredient: extra?['activeIngredient'] as String?,
              );
            },
          ),
          GoRoute(
            path: '/history',
            pageBuilder: (context, state) =>
                const NoTransitionPage(child: HistoryScreen()),
          ),
          GoRoute(
            path: '/history/scan/:id',
            builder: (context, state) => ScanHistoryDetailScreen(
              scanId: state.pathParameters['id'] ?? '',
            ),
          ),
          GoRoute(
            path: '/settings',
            builder: (context, state) => const SettingsScreen(),
          ),
        ],
      ),
    ],
  );
});

class _BootScreen extends StatelessWidget {
  const _BootScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(body: Center(child: CircularProgressIndicator()));
  }
}
