from django.conf import settings


def feature_flags(request):
    return {
        'RECOVERY_ENABLED': getattr(settings, 'RECOVERY_ENABLED', False),
    }
