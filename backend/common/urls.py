from django.urls import path, include

from common.views import (
    ProvinceListApiView,
    CountyListApiView,

    CompanyListApiView,
    CompanyDetailsApiView,

    HealthCheck,
)


urlpatterns = [
    path('province/' , ProvinceListApiView.as_view() , name="province-list"),
    path('county/' , CountyListApiView.as_view() , name="county-list"),

    path('company/' , CompanyListApiView.as_view() , name="company-list"),
    path('company/<int:companyid>/' , CompanyDetailsApiView.as_view() , name="company-details"),

    path('healthcheck/' , HealthCheck.as_view() , name="healthcheck"),
    
]
