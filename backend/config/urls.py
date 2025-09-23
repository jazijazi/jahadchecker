from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

#spectacular
from drf_spectacular.views import (
    SpectacularAPIView, 
    SpectacularRedocView, 
    SpectacularSwaggerView
)

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/common/', include('common.urls')),
    path('api/auth/', include('accounts.urls', namespace='accounts')),
    
    path('api/landreg/', include('landreg.urls')),

    #spectacular
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
