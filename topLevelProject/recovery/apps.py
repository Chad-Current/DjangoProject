from django.apps import AppConfig


class RecoveryConfig(AppConfig):
    name = 'recovery'

    def ready(self):
        import recovery.signals  # noqa: F401
