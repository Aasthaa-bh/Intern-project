from django.urls import path
from .views import login_view, change_password, logout_view
from .settings_views import user_settings_view

urlpatterns = [
    path("", login_view, name="login"),
    path("change-password/", change_password, name="change_password"),
    path("logout/", logout_view, name="logout"),
    path("settings/", user_settings_view, name="user_settings"),
]
