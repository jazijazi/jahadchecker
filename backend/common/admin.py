from django.contrib import admin
from leaflet.admin import LeafletGeoAdmin

from common.models import (
    Province,
    Company,
    County,
)

class ProvinceAdmin(admin.ModelAdmin):
    list_display = ['name_fa' , 'cnter_name_fa' , 'code']
    search_fields = ['name_fa' , 'cnter_name_fa' , 'code']

class CountyAdmin(admin.ModelAdmin):
    list_display = ['name_fa'  , 'code' , 'province']
    search_fields = ['name_fa' , 'code']
    list_per_page = 400
    
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name' , 'is_nazer' , 'is_supernazer' , 'is_moshaver']
    search_fields = ['name',]

admin.site.register(Province,ProvinceAdmin)
admin.site.register(County,CountyAdmin)
admin.site.register(Company,CompanyAdmin)
