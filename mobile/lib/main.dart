import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/date_symbol_data_local.dart';

import 'app.dart';
import 'core/notifications/notification_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: '.env');
  await initializeDateFormatting('vi_VN');
  await NotificationService.instance.initialize();

  const sendDebugNotifications = bool.fromEnvironment(
    'SEND_DEBUG_NOTIFS',
    defaultValue: false,
  );
  if (sendDebugNotifications) {
    unawaited(NotificationService.instance.sendDebugNotificationsBurst());
  }

  runApp(const ProviderScope(child: MedicineApp()));
}
