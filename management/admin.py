from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    City,
    Company,
    CustomUser,
    Estate,
    EstateFacility,
    Facility,
    PaymentTerms,
    TrackingEvent,
)

admin.site.site_header = "Smartworker"
admin.site.site_title = "Smartworker"
admin.site.index_title = "Administração"


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Contato", {"fields": ["phone"]}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Contato", {"fields": ["email", "phone"]}),)
    list_display = ["username", "email", "first_name", "last_name", "is_staff"]


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["name", "cnpj_display", "email", "phone"]
    search_fields = ["name", "cnpj", "email"]
    ordering = ["name"]

    @admin.display(description="CNPJ", ordering="cnpj")
    def cnpj_display(self, obj):
        return obj.cnpj_display


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ["display_name", "name"]
    search_fields = ["name"]


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    """Municípios vêm do IBGE (migração 0005): só consulta."""

    list_display = ["name", "state", "ibge_code"]
    list_filter = ["state"]
    search_fields = ["name", "ibge_code"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class EstateFacilityInline(admin.TabularInline):
    model = EstateFacility
    extra = 0
    autocomplete_fields = ["facility"]


class PaymentTermsInline(admin.TabularInline):
    model = PaymentTerms
    extra = 0


class TrackingEventInline(admin.TabularInline):
    """Histórico: eventos salvos não mudam; uma correção é um novo evento."""

    model = TrackingEvent
    extra = 0
    fields = ["status", "date", "note", "created_by", "created_at"]
    readonly_fields = ["created_by", "created_at"]
    can_delete = False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Estate)
class EstateAdmin(admin.ModelAdmin):
    list_display = ["name", "company", "city", "sales_start", "delivery_date"]
    list_filter = ["city__state", "company"]
    search_fields = ["name", "company__name", "street", "district", "city__name", "cep"]
    autocomplete_fields = ["company", "city"]
    list_select_related = ["company", "city"]
    inlines = [EstateFacilityInline, PaymentTermsInline, TrackingEventInline]

    def get_inlines(self, request, obj):
        # Ao cadastrar, o save() do modelo já cria o evento inicial
        if obj is None:
            return [EstateFacilityInline, PaymentTermsInline]
        return super().get_inlines(request, obj)

    def save_formset(self, request, form, formset, change):
        if formset.model is TrackingEvent:
            for event in formset.save(commit=False):
                event.created_by = request.user
                event.save()
            return
        super().save_formset(request, form, formset, change)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            obj.tracking_events.update(created_by=request.user)


@admin.register(TrackingEvent)
class TrackingEventAdmin(admin.ModelAdmin):
    list_display = ["estate", "status", "date", "created_by", "created_at"]
    list_filter = ["status", "date"]
    search_fields = ["estate__name", "note"]
    autocomplete_fields = ["estate"]
    readonly_fields = ["created_by", "created_at"]
    list_select_related = ["estate", "created_by"]

    def has_change_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        super().save_model(request, obj, form, change)
