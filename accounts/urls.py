
from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path(
        "login/verify-otp/",
        views.verify_login_otp,
        name="verify_login_otp",
    ),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
]