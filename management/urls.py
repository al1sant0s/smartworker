from django.urls import path

from . import views

app_name = "management"
urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("cities/", views.CityListView.as_view(), name="city_list"),
    path("company/list/", views.CompanyListView.as_view(), name="company_list"),
    path("company/new/", views.CompanyCreateView.as_view(), name="company_create"),
    path("company/edit/<int:pk>/", views.CompanyUpdateView.as_view(), name="company_update"),
    path("facility/list/", views.FacilityListView.as_view(), name="facility_list"),
    path("facility/new/", views.FacilityCreateView.as_view(), name="facility_create"),
    path("facility/edit/<int:pk>/", views.FacilityUpdateView.as_view(), name="facility_update"),
    path("estate/list/", views.EstateListView.as_view(), name="estate_list"),
    path("estate/new/", views.EstateCreateView.as_view(), name="estate_create"),
    path("estate/edit/<int:pk>/", views.EstateUpdateView.as_view(), name="estate_update"),
    path(
        "estate/<int:estate_pk>/events/new/",
        views.TrackingEventCreateView.as_view(),
        name="estate_event_create",
    ),
    # Nomes começam com "estate_" para o menu lateral destacar "Empreendimentos"
    path(
        "estate/<int:estate_pk>/payment-terms/new/",
        views.PaymentTermsCreateView.as_view(),
        name="estate_payment_terms_create",
    ),
    path(
        "payment-terms/edit/<int:pk>/",
        views.PaymentTermsUpdateView.as_view(),
        name="estate_payment_terms_update",
    ),
    path(
        "payment-terms/delete/<int:pk>/",
        views.PaymentTermsDeleteView.as_view(),
        name="estate_payment_terms_delete",
    ),
]
