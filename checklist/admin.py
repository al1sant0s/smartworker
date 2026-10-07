from django.contrib import admin
from django.utils import timezone

from .models import AvailabilitySheet, CheckList, SourceEmail, SourceHyperLink, SourcePhone


class SourceAdmin(admin.ModelAdmin):
    list_filter = ["company"]
    autocomplete_fields = ["company", "estates"]
    list_select_related = ["company"]

    @admin.display(description="Empreendimentos")
    def estate_list(self, obj):
        return ", ".join(estate.name for estate in obj.estates.all())

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("estates")


@admin.register(SourceHyperLink)
class SourceHyperLinkAdmin(SourceAdmin):
    list_display = ["url", "company", "description", "estate_list"]
    search_fields = ["url", "description", "company__name", "estates__name"]


@admin.register(SourceEmail)
class SourceEmailAdmin(SourceAdmin):
    list_display = ["email", "company", "description", "estate_list"]
    search_fields = ["email", "description", "company__name", "estates__name"]


@admin.register(SourcePhone)
class SourcePhoneAdmin(SourceAdmin):
    list_display = ["phone", "company", "description", "estate_list"]
    search_fields = ["phone", "description", "company__name", "estates__name"]


class AvailabilitySheetInline(admin.TabularInline):
    model = AvailabilitySheet
    extra = 0
    readonly_fields = ["uploaded_at"]


@admin.register(CheckList)
class CheckListAdmin(admin.ModelAdmin):
    list_display = ["estate", "reference_month", "status", "checked_by", "checked_at"]
    list_filter = ["status", "reference_month"]
    date_hierarchy = "reference_month"
    search_fields = ["estate__name", "estate__company__name"]
    autocomplete_fields = ["estate"]
    readonly_fields = ["checked_by", "checked_at"]
    list_select_related = ["estate", "checked_by"]
    inlines = [AvailabilitySheetInline]

    def save_model(self, request, obj, form, change):
        # Mesmo comportamento da tela de checklist: registra quem verificou
        if "status" in form.changed_data and obj.status != CheckList.StatusCheck.PENDING:
            obj.checked_by = request.user
            obj.checked_at = timezone.now()
        super().save_model(request, obj, form, change)
