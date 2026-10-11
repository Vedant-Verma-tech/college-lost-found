
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    fieldsets = UserAdmin.fieldsets + (
        ('Campus Information', {
            'fields': (
                'role',
                'college_id',
                'department',
                'phone',
            )
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Campus Information', {
            'fields': (
                'role',
                'college_id',
                'department',
                'phone',
            )
        }),
    )

    list_display = (
        'username',
        'email',
        'role',
        'college_id',
        'is_staff',
        'is_active',
    )

    list_filter = ('role', 'is_staff', 'is_active')