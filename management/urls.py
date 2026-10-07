from django.urls import path

from . import views

app_name = "management"
urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("cities/", views.CityListView.as_view(), name="city_list"),
    path("company/list/", views.CompanyListView.as_view(), name="company_list"),
    path("company/new/", views.CompanyCreateView.as_view(), name="company_create"),
    path("company/edit/<int:pk>/", views.CompanyUpdateView.as_view(), name="company_update"),
    path("estate/list/", views.EstateListView.as_view(), name="estate_list"),
    path("estate/new/", views.EstateCreateView.as_view(), name="estate_create"),
    path("estate/edit/<int:pk>/", views.EstateUpdateView.as_view(), name="estate_update"),
    path(
        "estate/<int:estate_pk>/events/new/",
        views.TrackingEventCreateView.as_view(),
        name="estate_event_create",
    ),
]
