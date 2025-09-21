from django.urls import path, include

from captcha.views import (
    CaptchaGenerateView,
    CaptchaRefreshView,
)
urlpatterns = [
    path('generate/' , CaptchaGenerateView.as_view() ,name="captcha-generate"),
    path('refresh/' , CaptchaRefreshView.as_view() ,name="captcha-refresh"),
]