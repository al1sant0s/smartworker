from django.urls import path
from django.contrib.auth.views import LoginView, login_required

from . import views

app_name = "management"
urlpatterns = [
    path("login/", LoginView.as_view(template_name="management/login.html"), name="login"),
    path("", views.index, name="index"),
]
