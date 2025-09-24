from django.urls import path, include

from landreg.views.pelakviews import (
    PelakListApiViews
)
from landreg.views.flagviews import (
    FlagListApiView,
)
from landreg.views.cadasterviews import (
    UploadOldCadasterApiView,
    OldCadasterDetailsApiView,
)



urlpatterns = [
    path('pelak/',PelakListApiViews.as_view(),name="plak-list"),

    path('flag/<int:cadasterid>/',FlagListApiView.as_view(),name="flag-list"),

    path('uploadoldcadaster/' , UploadOldCadasterApiView.as_view() , name="uoload-oldcadasterdata"),

    path('oldcadasterdata/<int:oldcadasterid>/' , OldCadasterDetailsApiView.as_view() , name="oldcadasterdata-details"),
    
]