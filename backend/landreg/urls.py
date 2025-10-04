from django.urls import path, include

from landreg.views.pelakviews import (
    PelakListApiViews
)
from landreg.views.flagviews import (
    FlagListApiView,
)
from landreg.views.cadasterviews import (
    UploadOldCadasterFromGdbApiView,
    UploadOldCadasterFromShapefileApiView,

    CadasterDetailsApiView,

    OldCadasterListApiView,
    OldCadasterDetailsApiView,

    GetListLayersFromGeodbFile,
    ChangeCadsterStatusApiView,
    TableColumnNamesAPIView,
    CadasterColumnMappingValidateAPIView,
    CadasterImportAPIView,
)
from landreg.views.reportviews import (
    CadaterStatusByProvince,
    FlagStatusByProvince,
    DiffCadasterAndFlagStatusByProvince
)


urlpatterns = [
    path('pelak/',PelakListApiViews.as_view(),name="plak-list"),

    path('flag/<int:cadasterid>/',FlagListApiView.as_view(),name="flag-list"),

    path('cadaster/<int:cadasterid>/' , CadasterDetailsApiView.as_view() , name="cadaster-details"),

    path('uploadoldcadasterfromshapefile/' , UploadOldCadasterFromShapefileApiView.as_view() , name="upload-oldcadasterdata-shp"),
    path('uploadoldcadasterfromgeodatabase/' , UploadOldCadasterFromGdbApiView.as_view() , name="upload-oldcadasterdata-gdb"),

    path('listlayersgdb/',GetListLayersFromGeodbFile.as_view(),name='list-layers-from-gdb'),

    path('oldcadasterdata/' , OldCadasterListApiView.as_view() , name="oldcadasterdata-list"),
    path('oldcadasterdata/<int:oldcadasterid>/' , OldCadasterDetailsApiView.as_view() , name="oldcadasterdata-details"),
    path('updatecadasterstatus/<int:cadasterid>/' , ChangeCadsterStatusApiView.as_view() , name="oldcadasterdata-details"),
    
    path('tablecolumnnames/' , TableColumnNamesAPIView.as_view() , name="oldcadasterdata-tablename"),
    path('colmapvalidate/', CadasterColumnMappingValidateAPIView.as_view(), name='cadaster-column-mapping-validate'),
    path('cadasterimport/', CadasterImportAPIView.as_view(), name='cadaster-import'),

    path('cadaterstatusbyprovince/<int:provinceid>/', CadaterStatusByProvince.as_view(), name='report-cadastersatus-by-province'),    
    path('flagstatusbyprovince/<int:provinceid>/', FlagStatusByProvince.as_view(), name='report-flagsatus-by-province'),    
    path('diffcadasterflagstatusbyprovince/<int:provinceid>/', DiffCadasterAndFlagStatusByProvince.as_view(), name='report-cadasterflag-diff-satus-by-province'),    
    
]