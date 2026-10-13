
from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path(
        "register/verify-otp/",
        views.verify_registration_otp,
        name="verify_registration_otp",
    ),
    path("logout/", views.logout_view, name="logout"),
]
