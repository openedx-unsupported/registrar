"""
Config for the enrollments app.
"""
from django.apps import AppConfig


class EnrollmentsConfig(AppConfig):
    name = 'registrar.apps.enrollments'

    def ready(self):
        import registrar.apps.enrollments.signals
