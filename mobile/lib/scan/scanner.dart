import 'models.dart';

abstract interface class PrescriptionScanner {
  Future<EntityRequest?> scan();

  Future<void> close();
}
