from django.apps import AppConfig


class LandregConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'landreg'

    def ready(self):
        import landreg.signals
