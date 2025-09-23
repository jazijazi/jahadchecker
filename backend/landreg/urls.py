from django.urls import path, include

from landreg.views.pelakviews import (
    PelakListApiViews
)
from landreg.views.flagviews import (
    FlagListApiView,
)



urlpatterns = [
    path('pelak/',PelakListApiViews.as_view(),name="plak-list"),

    path('flag/<int:cadasterid>/',FlagListApiView.as_view(),name="flag-list"),
    
]