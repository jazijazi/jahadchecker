
from django.contrib import admin, messages
from leaflet.admin import LeafletGeoAdmin

from .models import Pelak
from .models.cadaster import (
    IrrigationTypDomain ,
    LandUseDomain ,
    Cadaster ,
    OldCadasterData
)
from .models.flag import Flag
from landreg.services.gis import drop_table_if_exists


class PelakAdmin(LeafletGeoAdmin):
    # Fields to show in the list view
    list_display = (
        'number',
        'title',
        'is_verified',
        'created_by',
        'verifyby',
        'verifydata',
    )

    # Fields that are clickable to go to the detail page
    list_display_links = ('number', 'title')

    # Add filters on sidebar
    list_filter = ('verify',)

    # Add search box
    search_fields = ('number', 'title', 'created_by__username', 'verifyby__username')

    # Ordering
    ordering = ('-verifydata', 'number')

    # Fields to show in the detail/edit view
    fieldsets = (
        (None, {
            'fields': ('number', 'title', 'border')
        }),
        ('Verification', {
            'fields': ('verify', 'verifydata', 'verifyby')
        }),
        ('Provinace', {
            'fields': ('provinces',)
        }),
        ('Meta', {
            'fields': ('created_by',)
        }),
    )

    readonly_fields = ('verifydata', 'verifyby')

    # Optional: display boolean nicely
    def is_verified(self, obj):
        return obj.is_verified
    is_verified.boolean = True
    is_verified.short_description = "Verified"

class LandUseDomainAdmin(admin.ModelAdmin):
    list_display = ['id', 'title']
    search_fields = ['title']

class IrrigationTypDomainAdmin(admin.ModelAdmin):
    list_display = ['id', 'title']
    search_fields = ['title']

class CadasterAdmin(LeafletGeoAdmin):
    list_display = [
        'uniquecode', 'plak_name', 'plak_asli', 'plak_farei',
        'owner_name', 'owner_lastname', 'project_name', 'status'
    ]
    search_fields = [
        'uniquecode', 'plak_name', 'plak_asli', 'plak_farei',
        'owner_name', 'owner_lastname', 'national_code'
    ]
    list_filter = [
        'project_name', 'status', 'land_use', 'irrigation_type'
    ]
    autocomplete_fields = ['pelak', 'land_use', 'irrigation_type']

    fieldsets = (
        ("اطلاعات کاداستر", {
            "fields": (
                "uniquecode","jaam_code","plak_name","plak_asli",
                "plak_farei","bakhsh_sabti","nahiye_sabti","consulate_name",
                "area"
            )
        }),
        ("مالک", {
            "fields": (
                "owner_name", "owner_lastname", "fathername",
                "national_code", "mobile", "ownership_kinde"
            )
        }),
        ("کاربری و آبیاری", {
            "fields": ("land_use", "irrigation_type")
        }),
        ("نظارت",{
            "fields":("nezarat_type","nezart_verify_date","project_name")
        }),
        ("موقعیت و مرز", {
            "fields": ("pelak","status","border")
        }),
    )


class FlagAdmin(LeafletGeoAdmin):
    list_display = [
        'id', 'cadaster', 'status', 'createdby', 'created_at'
    ]
    list_filter = ['status', 'createdby', 'cadaster']
    search_fields = ['id', 'description', 'cadaster__uniquecode', 'createdby__username']
    autocomplete_fields = ['cadaster', 'createdby']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ("اطلاعات اصلی", {
            "fields": ("cadaster", "status", "description")
        }),
        ("مکان", {
            "fields": ("border",)
        }),
        ("ثبت اطلاعات", {
            "fields": ("createdby", "created_at", "updated_at")
        }),
    )

class OldCadasterDataAdmin(admin.ModelAdmin):
    list_display = [
        "id", "table_name", "province", "status",
        "created_by", "matched_by",
    ]
    list_filter = ["status",]
    search_fields = ["table_name", "province__name", "created_by__username", "matched_by__username"]
    autocomplete_fields = ["province", "created_by", "matched_by"]

    fieldsets = (
        ("اطلاعات اصلی", {
            "fields": ("table_name", "province", "status")
        }),
        ("ایجاد", {
            "fields": ("created_by",)
        }),
        ("مچ شدن", {
            "fields": ("matched_by", "matched_at")
        }),
    )

    actions = ["drop_selected_tables"]

    def drop_selected_tables(self, request, queryset):
        """
        Custom admin action: drop DB tables for selected cadaster records
        """
        success_tables = []
        failed_tables = []

        for obj in queryset:
            if drop_table_if_exists(obj.table_name):
                success_tables.append(obj.table_name)
            else:
                failed_tables.append(obj.table_name)

        if success_tables:
            self.message_user(
                request,
                f"Tables dropped successfully: {', '.join(success_tables)}",
                level=messages.SUCCESS
            )

        if failed_tables:
            self.message_user(
                request,
                f"Failed to drop tables: {', '.join(failed_tables)}",
                level=messages.ERROR
            )
    drop_selected_tables.short_description = "Drop database tables for selected records"

admin.site.register(LandUseDomain , LandUseDomainAdmin)
admin.site.register(IrrigationTypDomain , IrrigationTypDomainAdmin)

admin.site.register(Pelak , PelakAdmin)
admin.site.register(Cadaster , CadasterAdmin)
admin.site.register(Flag , FlagAdmin)
admin.site.register(OldCadasterData , OldCadasterDataAdmin)



