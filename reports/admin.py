from django.contrib import admin

from .models import ItemReport


@admin.register(ItemReport)
class ItemReportAdmin(admin.ModelAdmin):

    list_display = (

        'title',

        'report_type',

        'category',

        'location',

        'status',

        'owner',

        'created_at',

    )

    list_filter = (

        'report_type',

        'category',

        'status',

    )

    search_fields = (

        'title',

        'description',

        'location',

        'owner__username',

        'owner__college_id',

    )

    ordering = (
        '-created_at',
    )
    
