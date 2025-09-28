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

    GetListLayersFromGeodbFile,
    ChangeCadsterStatusApiView,
    TableColumnNamesAPIView,
    CadasterColumnMappingValidateAPIView,
)



urlpatterns = [
    path('pelak/',PelakListApiViews.as_view(),name="plak-list"),

    path('flag/<int:cadasterid>/',FlagListApiView.as_view(),name="flag-list"),

    path('uploadoldcadaster/' , UploadOldCadasterApiView.as_view() , name="uoload-oldcadasterdata"),

    path('listlayersgdb/',GetListLayersFromGeodbFile.as_view(),name='list-layers-from-gdb'),


    path('oldcadasterdata/<int:oldcadasterid>/' , OldCadasterDetailsApiView.as_view() , name="oldcadasterdata-details"),
    path('updatecadasterstatus/<int:cadasterid>/' , ChangeCadsterStatusApiView.as_view() , name="oldcadasterdata-details"),
    
    path('tablecolumnnames/' , TableColumnNamesAPIView.as_view() , name="oldcadasterdata-tablename"),
    path('colmapvalidate/', CadasterColumnMappingValidateAPIView.as_view(), name='cadaster-column-mapping-validate'),
    
]