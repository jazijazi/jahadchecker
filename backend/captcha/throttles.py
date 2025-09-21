from rest_framework.throttling import SimpleRateThrottle

class CaptchaRateThrottle(SimpleRateThrottle):
    scope = 'captcha'

    def get_cache_key(self, request, view):
        # Use IP for anonymous users
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)  # IP address

        return f"{self.scope}_{ident}"
