from django.urls import path

from . import views

app_name = "checklist"
urlpatterns = [
    path("", views.CheckListListView.as_view(), name="checklist_list"),
    path("generate/", views.CheckListGenerateView.as_view(), name="checklist_generate"),
    path("<int:pk>/", views.CheckListDetailView.as_view(), name="checklist_detail"),
    path(
        "sheets/<int:pk>/delete/",
        views.AvailabilitySheetDeleteView.as_view(),
        name="sheet_delete",
    ),
    path(
        "estate/<int:estate_pk>/sources/",
        views.EstateSourcesView.as_view(),
        name="estate_sources",
    ),
]
