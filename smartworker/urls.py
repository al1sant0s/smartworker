"""
URL configuration for smartworker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
from django.views.generic import RedirectView
from two_factor.urls import urlpatterns as tf_urls
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path
from django.views.generic import RedirectView
from two_factor.urls import urlpatterns as tf_urls

urlpatterns = [
    # Sem login, o LoginRequiredMiddleware manda para a tela de login
    path("", RedirectView.as_view(pattern_name="management:index"), name="home"),
    # account/login/, account/two_factor/setup/ etc.
    path("", include(tf_urls)),
    path("account/logout/", LogoutView.as_view(), name="logout"),
    path("management/", include("management.urls")),
    path("admin/", admin.site.urls),
]
