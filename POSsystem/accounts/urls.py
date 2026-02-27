from django.urls import path
from .views import login_view, change_password, logout_view

urlpatterns = [
    path("login/", login_view, name="login"),
    path("change-password/", change_password, name="change_password"),
    path("logout/", logout_view, name="logout"),
]
