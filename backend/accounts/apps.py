from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # This will register the extension
        from .spectacular_extensions import JWTAuthenticationExtension
        import accounts.signals
