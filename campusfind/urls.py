
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from reports import views

urlpatterns = [
    # Django built-in admin
    path('admin/', admin.site.urls),

    # Home and item listings
    path('', views.home, name='home'),
    path('lost/', views.lost_items, name='lost'),
    path('found/', views.found_items, name='found'),

    # Report items
    path('report/lost/', views.report_lost, name='report_lost'),
    path('report/found/', views.report_found, name='report_found'),
    path('my-reports/', views.my_reports, name='my_reports'),

    # Teacher dashboard and report review
    path(
        'teacher/dashboard/',
        views.teacher_dashboard,
        name='teacher_dashboard'
    ),
    path(
        'teacher/review/<int:report_id>/',
        views.review_report,
        name='review_report'
    ),

    # CampusFind custom admin dashboard
    path(
        'campus-admin/',
        views.admin_dashboard,
        name='admin_dashboard'
    ),
    path(
        'campus-admin/users/',
        views.admin_users,
        name='admin_users'
    ),
    path(
        'campus-admin/users/<int:user_id>/role/',
        views.admin_update_user_role,
        name='admin_update_user_role'
    ),
    path(
        'campus-admin/users/<int:user_id>/toggle-active/',
        views.admin_toggle_user_active,
        name='admin_toggle_user_active'
    ),
    path(
        'campus-admin/reports/',
        views.admin_reports,
        name='admin_reports'
    ),
    path(
        'campus-admin/reports/<int:report_id>/status/',
        views.admin_update_report_status,
        name='admin_update_report_status'
    ),

    # Claim system
    path(
        'claims/review/',
        views.claims_dashboard,
        name='claims_dashboard'
    ),

    # App URLs
    path('', include('reports.urls')),
    path('', include('accounts.urls')),
]

# Uploaded media files during development
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
