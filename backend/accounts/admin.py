from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from accounts.models import (
    User,
    Apis,
    Tools,
    Roles,
    Notification,
    UserPelakPermission
)

class APISADMIN(admin.ModelAdmin):
    list_display = ['id' , 'method' , 'url']
    search_fields = ['method' , 'url']

class TOOLSADMIN(admin.ModelAdmin):
    list_display = ['id' , 'title']
    search_fields = ['title']

class ROLESADMIN(admin.ModelAdmin):
    list_display = ['id' , 'title']
    search_fields = ['title']

class UserPelakPermissionInline(admin.TabularInline):
    model = UserPelakPermission
    extra = 1
class USERSINADMIN(admin.ModelAdmin):
    list_display = ['id','username','first_name_fa','last_name_fa','is_active','is_superuser']
    search_fields = ['username','first_name_fa','last_name_fa','first_name','last_name']

    inlines = [UserPelakPermissionInline]
    
admin.site.register(User, USERSINADMIN)
admin.site.register(Apis , APISADMIN)
admin.site.register(Tools , TOOLSADMIN)
admin.site.register(Roles , ROLESADMIN)
admin.site.register(Notification)