import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/widgets.dart';
import 'package:timezone/data/latest_all.dart' as tz;
import 'package:timezone/timezone.dart' as tz;

import '../../features/create_plan/domain/plan.dart';
import '../../l10n/app_localizations.dart';

class NotificationService {
  NotificationService();

  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();
  bool _initialized = false;

  AppLocalizations get _l10n => lookupAppLocalizations(const Locale('vi'));

  AndroidNotificationDetails _androidDetails() {
    return AndroidNotificationDetails(
      'medicine_plan_channel',
      _l10n.notificationChannelName,
      channelDescription: _l10n.notificationChannelDescription,
      importance: Importance.max,
      priority: Priority.high,
      // Wake device screen to show heads-up notification
      fullScreenIntent: true,
    );
  }

  Future<void> initialize() async {
    if (_initialized) {
      return;
    }

    if (kIsWeb) {
      _initialized = true;
      return;
    }

    tz.initializeTimeZones();
    try {
      tz.setLocalLocation(tz.getLocation('Asia/Ho_Chi_Minh'));
    } catch (_) {
      tz.setLocalLocation(tz.UTC);
    }

    const androidSettings = AndroidInitializationSettings(
      '@mipmap/ic_launcher',
    );
    const iosSettings = DarwinInitializationSettings();

    await _plugin.initialize(
      const InitializationSettings(android: androidSettings, iOS: iosSettings),
    );

    final androidPlugin = _plugin
        .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin
        >();
    await androidPlugin?.requestNotificationsPermission();

    final iosPlugin = _plugin
        .resolvePlatformSpecificImplementation<
          IOSFlutterLocalNotificationsPlugin
        >();
    await iosPlugin?.requestPermissions(alert: true, badge: true, sound: true);

    _initialized = true;
  }

  int _hashId(String text) {
    var hash = 17;
    for (final codeUnit in text.codeUnits) {
      hash = 37 * hash + codeUnit;
    }
    return hash.abs() % 2147483647;
  }

  Future<void> schedulePlanNotifications(Plan plan) async {
    await initialize();
    if (kIsWeb) {
      return;
    }
    final l10n = _l10n;
    await cancelPlanNotifications(plan.id);

    final now = DateTime.now();
    final parsedStartDate = DateTime.tryParse(plan.startDate);
    final startDate = parsedStartDate != null
        ? DateTime(
            parsedStartDate.year,
            parsedStartDate.month,
            parsedStartDate.day,
          )
        : DateTime(now.year, now.month, now.day);
    final today = DateTime(now.year, now.month, now.day);
    final anchorDate = startDate.isBefore(today) ? today : startDate;
    final dayCount = plan.totalDays ?? 30;

    for (var dayOffset = 0; dayOffset < dayCount; dayOffset += 1) {
      final date = anchorDate.add(Duration(days: dayOffset));

      for (final hhmm in plan.times) {
        final parts = hhmm.split(':');
        if (parts.length != 2) {
          continue;
        }
        final hour = int.tryParse(parts[0]);
        final minute = int.tryParse(parts[1]);
        if (hour == null || minute == null) {
          continue;
        }

        final scheduled = DateTime(
          date.year,
          date.month,
          date.day,
          hour,
          minute,
        );
        if (!scheduled.isAfter(now)) {
          continue;
        }

        final id = _hashId('${plan.id}:${scheduled.toIso8601String()}');
        final medications = plan.medicationsForTime(
          '${hour.toString().padLeft(2, '0')}:${minute.toString().padLeft(2, '0')}',
        );
        final pills = plan.pillsForTime(
          '${hour.toString().padLeft(2, '0')}:${minute.toString().padLeft(2, '0')}',
        );
        final body = medications.isNotEmpty
            ? medications
                  .map((item) => '${item.drugName} (${item.pills} viên)')
                  .join(', ')
            : (plan.drugName.isNotEmpty
                  ? '${plan.drugName} ($pills viên)'
                  : l10n.notificationDefaultBody);
        try {
          await _plugin.zonedSchedule(
            id,
            l10n.notificationDefaultTitle,
            body,
            tz.TZDateTime.from(scheduled, tz.local),
            NotificationDetails(
              android: _androidDetails(),
              iOS: DarwinNotificationDetails(),
            ),
            // exactAllowWhileIdle delivers at the exact scheduled time even
            // when the device is in idle/Doze mode. Falls back gracefully if
            // OS denies exact-alarm permission (caught below).
            androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
            payload: 'plan:${plan.id}',
          );
        } on PlatformException catch (e) {
          // SecurityException is surfaced as PlatformException when the OS
          // has not granted SCHEDULE_EXACT_ALARM / USE_EXACT_ALARM.
          // Log and skip this slot rather than crashing the app.
          if (kDebugMode) {
            debugPrint(
              '[NotificationService] zonedSchedule skipped for '
              '${plan.id} @ ${scheduled.toIso8601String()}: ${e.message}',
            );
          }
        }
      }
    }
  }

  Future<void> cancelPlanNotifications(String planId) async {
    await initialize();
    if (kIsWeb) {
      return;
    }
    final pending = await _plugin.pendingNotificationRequests();
    for (final req in pending) {
      if (req.payload == 'plan:$planId') {
        await _plugin.cancel(req.id);
      }
    }
  }

  Future<void> rescheduleAllPlans(List<Plan> plans) async {
    await initialize();
    if (kIsWeb) {
      return;
    }
    await _plugin.cancelAll();
    if (kDebugMode) {
      debugPrint('[NotificationService] Reschedule ${plans.length} plans');
    }
    for (final plan in plans) {
      await schedulePlanNotifications(plan);
    }
  }

  Future<void> cancelAllNotifications() async {
    await initialize();
    if (kIsWeb) {
      return;
    }
    await _plugin.cancelAll();
  }
}

final notificationServiceProvider = Provider<NotificationService>((ref) {
  return NotificationService();
});
