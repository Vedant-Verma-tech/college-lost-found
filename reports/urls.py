
from django.urls import path
from . import views

urlpatterns = [
    
    path('', views.home, name='home'),
    path('lost/', views.lost_items, name='lost_items'),
    path('found/', views.found_items, name='found_items'),

    
    path('report/lost/', views.report_lost, name='report_lost'),
    path('report/found/', views.report_found, name='report_found'),
    path('my-reports/', views.my_reports, name='my_reports'),

    
    path(
        'teacher/dashboard/',
        views.teacher_dashboard,
        name='teacher_dashboard'
    ),
    path(
        'teacher/reports/<int:report_id>/review/',
        views.review_report,
        name='review_report'
    ),


    path(
         "notifications/",
         views.notifications_list,
         name="notifications"
    ),
    path(
         "notifications/<int:notification_id>/read/",
         views.mark_notification_read,
         name="mark_notification_read"
    ),


    path(
        'items/<int:report_id>/claim/',
        views.submit_claim,
        name='submit_claim'
    ),
    path('my-claims/', views.my_claims, name='my_claims'),
    path(
        'teacher/claims/',
        views.claims_dashboard,
        name='claims_dashboard'
    ),
    path(
        'teacher/claims/<int:claim_id>/review/',
        views.review_claim,
        name='review_claim'
    ),
    path(
        'teacher/claims/<int:claim_id>/return/',
        views.confirm_item_return,
        name='confirm_item_return'
    ),
]