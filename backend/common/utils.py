from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

from rest_framework.exceptions import (
    NotAuthenticated,
    Throttled
)

def custom_exception_handler(exc, context):
    if isinstance(exc, NotAuthenticated):
        return Response({'detail': 'توکن ارائه نشده است یا کاربر وارد نشده است'}, status=status.HTTP_401_UNAUTHORIZED)

    
    if isinstance(exc, Throttled):
        wait = exc.wait
        minutes = round(wait / 60) if wait else 1
        custom_response_data = {
            "detail": f"تعداد درخواست‌های شما بیش از حد مجاز است. لطفاً حدود {minutes} دقیقه دیگر تلاش کنید."
        }
        return Response(custom_response_data, status=status.HTTP_429_TOO_MANY_REQUESTS)

    # fallback to default handler
    return exception_handler(exc, context)
