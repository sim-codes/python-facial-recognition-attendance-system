from django.contrib import admin
from .models import User

class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type')
    fieldsets = (
        ('User Type', {'fields': ('user_type', 'face_image', 'face_encoding')}),
    )
    add_fieldsets = (
        ('User Type', {'fields': ('user_type',)}),
    )

admin.site.register(User, CustomUserAdmin)
