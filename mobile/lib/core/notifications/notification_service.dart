import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/widgets.dart';
import 'package:timezone/data/latest_all.dart' as tz;
import 'package:timezone/timezone.dart' as tz;

import '../../features/create_plan/domain/plan.dart';
import '../../l10n/app_localizations.dart';

const _notificationChannelId = 'medicine_plan_channel';
const _takenActionId = 'taken';
const _iosDoseCategoryId = 'dose_actions';

class NotificationActionEvent {
  const NotificationActionEvent({
    required this.actionId,
    required this.planId,
    required this.occurrenceId,
    required this.scheduledTime,
    required this.kind,
    required this.title,
  });

  final String actionId;
  final String planId;
  final String occurrenceId;
  final String scheduledTime;
  final String kind;
  final String title;

  bool get isTakenAction => actionId == _takenActionId;
}

class NotificationService {
  NotificationService._();

  static final NotificationService instance = NotificationService._();

  factory NotificationService() => instance;

  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();
  final StreamController<NotificationActionEvent> _actionController =
      StreamController<NotificationActionEvent>.broadcast();
  final List<NotificationActionEvent> _pendingLaunchEvents = [];
  bool _initialized = false;

  AppLocalizations get _l10n => lookupAppLocalizations(const Locale('vi'));

  Stream<NotificationActionEvent> get actionEvents => _actionController.stream;

  List<NotificationActionEvent> takePendingLaunchEvents() {
    final pending = List<NotificationActionEvent>.from(_pendingLaunchEvents);
    _pendingLaunchEvents.clear();
    return pending;
  }

  AndroidNotificationDetails _androidDetails({
    bool includeTakenAction = false,
  }) {
    return AndroidNotificationDetails(
      _notificationChannelId,
      _l10n.notificationChannelName,
      channelDescription: _l10n.notificationChannelDescription,
      importance: Importance.max,
      priority: Priority.high,
      fullScreenIntent: true,
      actions: includeTakenAction
          ? <AndroidNotificationAction>[
              const AndroidNotificationAction(
                _takenActionId,
                'Đã uống',
                showsUserInterface: true,
                cancelNotification: true,
              ),
            ]
          : null,
    );
  }

  DarwinNotificationDetails _iosDetails({bool includeTakenAction = false}) {
    return DarwinNotificationDetails(
      categoryIdentifier: includeTakenAction ? _iosDoseCategoryId : null,
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
    final iosSettings = DarwinInitializationSettings(
      notificationCategories: <DarwinNotificationCategory>[
        DarwinNotificationCategory(
          _iosDoseCategoryId,
          actions: <DarwinNotificationAction>[
            DarwinNotificationAction.plain(
              _takenActionId,
              'Đã uống',
              options: <DarwinNotificationActionOption>{
                DarwinNotificationActionOption.foreground,
              },
            ),
          ],
        ),
      ],
    );

    await _plugin.initialize(
      InitializationSettings(android: androidSettings, iOS: iosSettings),
      onDidReceiveNotificationResponse: _handleNotificationResponse,
    );

    final launchDetails = await _plugin.getNotificationAppLaunchDetails();
    final launchResponse = launchDetails?.notificationResponse;
    if (launchDetails?.didNotificationLaunchApp == true &&
        launchResponse != null) {
      _queueNotificationEvent(launchResponse);
    }

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

  void _handleNotificationResponse(NotificationResponse response) {
    _queueNotificationEvent(response);
  }

  void _queueNotificationEvent(NotificationResponse response) {
    final payload = response.payload;
    if (payload == null || payload.isEmpty) {
      return;
    }

    try {
      final json = jsonDecode(payload) as Map<String, dynamic>;
      final event = NotificationActionEvent(
        actionId: response.actionId ?? '',
        planId: json['planId']?.toString() ?? '',
        occurrenceId: json['occurrenceId']?.toString() ?? '',
        scheduledTime: json['scheduledTime']?.toString() ?? '',
        kind: json['kind']?.toString() ?? 'unknown',
        title: json['title']?.toString() ?? '',
      );
      if (event.occurrenceId.isEmpty || event.planId.isEmpty) {
        return;
      }

      if (_actionController.hasListener) {
        _actionController.add(event);
      } else {
        _pendingLaunchEvents.add(event);
      }
    } catch (_) {
      return;
    }
  }

  int _hashId(String text) {
    var hash = 17;
    for (final codeUnit in text.codeUnits) {
      hash = 37 * hash + codeUnit;
    }
    return hash.abs() % 2147483647;
  }

  String _dateKey(DateTime date) {
    final y = date.year.toString().padLeft(4, '0');
    final m = date.month.toString().padLeft(2, '0');
    final d = date.day.toString().padLeft(2, '0');
    return '$y-$m-$d';
  }

  String _slotBody(PlanSlot slot) {
    if (slot.items.isEmpty) {
      return _l10n.notificationDefaultBody;
    }

    return slot.items
        .map((item) => '${item.drugName} (${item.pills} viên)')
        .join(', ');
  }

  String _payload({
    required String planId,
    required String occurrenceId,
    required String scheduledTime,
    required String kind,
    required String title,
  }) {
    return jsonEncode({
      'planId': planId,
      'occurrenceId': occurrenceId,
      'scheduledTime': scheduledTime,
      'kind': kind,
      'title': title,
    });
  }

  Future<void> _scheduleReminder({
    required String uniqueKey,
    required DateTime when,
    required String title,
    required String body,
    required String payload,
    required bool includeTakenAction,
  }) async {
    if (!when.isAfter(DateTime.now())) {
      return;
    }

    try {
      await _plugin.zonedSchedule(
        _hashId(uniqueKey),
        title,
        body,
        tz.TZDateTime.from(when, tz.local),
        NotificationDetails(
          android: _androidDetails(includeTakenAction: includeTakenAction),
          iOS: _iosDetails(includeTakenAction: includeTakenAction),
        ),
        androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
        payload: payload,
      );
    } on PlatformException catch (e) {
      if (kDebugMode) {
        debugPrint(
          '[NotificationService] zonedSchedule skipped for $uniqueKey: '
          '${e.message}',
        );
      }
    }
  }

  Future<void> schedulePlanNotifications(Plan plan) async {
    await initialize();
    if (kIsWeb || plan.hasEnded) {
      return;
    }

    await cancelPlanNotifications(plan.id);

    final now = DateTime.now();
    final parsedStartDate = DateTime.tryParse(plan.startDate);
    final normalizedStart = parsedStartDate != null
        ? DateTime(
            parsedStartDate.year,
            parsedStartDate.month,
            parsedStartDate.day,
          )
        : DateTime(now.year, now.month, now.day);
    final normalizedToday = DateTime(now.year, now.month, now.day);
    final anchorDate = normalizedStart.isBefore(normalizedToday)
        ? normalizedToday
        : normalizedStart;
    final parsedEndDate = plan.parsedEndDate;
    final normalizedEnd = parsedEndDate != null
        ? DateTime(parsedEndDate.year, parsedEndDate.month, parsedEndDate.day)
        : anchorDate.add(Duration(days: (plan.totalDays ?? 30) - 1));

    for (
      var current = anchorDate;
      !current.isAfter(normalizedEnd);
      current = current.add(const Duration(days: 1))
    ) {
      final dateKey = _dateKey(current);

      for (final slot in plan.slots) {
        final parts = slot.time.split(':');
        if (parts.length != 2) {
          continue;
        }

        final hour = int.tryParse(parts[0]);
        final minute = int.tryParse(parts[1]);
        if (hour == null || minute == null) {
          continue;
        }

        final scheduled = DateTime(
          current.year,
          current.month,
          current.day,
          hour,
          minute,
        );
        final occurrenceId = '${plan.id}:$dateKey:${slot.time}';
        final scheduledTime = scheduled.toUtc().toIso8601String();
        final payload = _payload(
          planId: plan.id,
          occurrenceId: occurrenceId,
          scheduledTime: scheduledTime,
          kind: 'dose',
          title: plan.drugName,
        );
        final body = _slotBody(slot);

        await _scheduleReminder(
          uniqueKey: '$occurrenceId:pre',
          when: scheduled.subtract(const Duration(minutes: 30)),
          title: 'Sắp đến giờ uống thuốc',
          body: body,
          payload: payload,
          includeTakenAction: false,
        );
        await _scheduleReminder(
          uniqueKey: '$occurrenceId:due',
          when: scheduled,
          title: _l10n.notificationDefaultTitle,
          body: body,
          payload: payload,
          includeTakenAction: true,
        );

        for (var index = 1; index <= 3; index += 1) {
          final minutes = 15 * index;
          await _scheduleReminder(
            uniqueKey: '$occurrenceId:followup:$minutes',
            when: scheduled.add(Duration(minutes: minutes)),
            title: index == 3
                ? 'Liều thuốc sắp bị tính là quên'
                : 'Nhắc lại uống thuốc',
            body: body,
            payload: payload,
            includeTakenAction: true,
          );
        }
      }
    }
  }

  Map<String, dynamic>? _decodePayload(String? payload) {
    if (payload == null || payload.isEmpty) {
      return null;
    }

    try {
      return jsonDecode(payload) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  Future<void> cancelOccurrenceNotifications(String occurrenceId) async {
    await initialize();
    if (kIsWeb) {
      return;
    }

    final pending = await _plugin.pendingNotificationRequests();
    for (final req in pending) {
      final payload = _decodePayload(req.payload);
      if (payload?['occurrenceId']?.toString() == occurrenceId) {
        await _plugin.cancel(req.id);
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
      final payload = _decodePayload(req.payload);
      if (payload?['planId']?.toString() == planId) {
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
    for (final plan in plans.where((plan) => plan.isCurrentPlan)) {
      await schedulePlanNotifications(plan);
    }
  }

  Future<bool> hasPermissions() async {
    if (kIsWeb) {
      return false;
    }
    await initialize();

    if (defaultTargetPlatform == TargetPlatform.android) {
      final androidPlugin = _plugin.resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin>();
      if (androidPlugin == null) {
        return false;
      }

      final notificationsEnabled =
          await androidPlugin.areNotificationsEnabled() ?? false;
      if (!notificationsEnabled) {
        return false;
      }

      final exactAlarmsEnabled =
          await androidPlugin.canScheduleExactNotifications() ?? false;
      if (!exactAlarmsEnabled) {
        return false;
      }

      return true;
    }
    return true;
  }

  Future<void> requestPermissions() async {
    if (kIsWeb) {
      return;
    }
    await initialize();

    if (defaultTargetPlatform == TargetPlatform.android) {
      final androidPlugin = _plugin.resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin>();
      if (androidPlugin == null) {
        return;
      }

      final notificationsEnabled =
          await androidPlugin.areNotificationsEnabled() ?? false;
      if (!notificationsEnabled) {
        await androidPlugin.requestNotificationsPermission();
      }

      final exactAlarmsEnabled =
          await androidPlugin.canScheduleExactNotifications() ?? false;
      if (!exactAlarmsEnabled) {
        await androidPlugin.requestExactAlarmsPermission();
      }
    } else if (defaultTargetPlatform == TargetPlatform.iOS) {
      final iosPlugin = _plugin.resolvePlatformSpecificImplementation<
          IOSFlutterLocalNotificationsPlugin>();
      await iosPlugin?.requestPermissions(
        alert: true,
        badge: true,
        sound: true,
      );
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
  return NotificationService.instance;
});
