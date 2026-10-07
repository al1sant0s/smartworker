from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Count, OuterRef, Subquery
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from .forms import (
    CompanyForm,
    EstateFacilityFormSet,
    EstateForm,
    FacilityForm,
    PaymentTermsForm,
    TrackingEventForm,
)
from .mixins import SearchMixin, StaffRequiredMixin
from .models import City, Company, Estate, Facility, PaymentTerms, State, TrackingEvent


class IndexView(TemplateView):
    template_name = "management/index.html"


class CityListView(View):
    """Municípios de uma UF em JSON, para o select do formulário de endereço."""

    def get(self, request):
        state = request.GET.get("state", "")
        if state not in State.values:
            return JsonResponse({"error": "UF inválida."}, status=400)
        cities = City.objects.filter(state=state).order_by("name").values("ibge_code", "name")
        return JsonResponse({"cities": list(cities)})


# Construtoras ------------------------------------------------------------------


class CompanyListView(SearchMixin, ListView):
    model = Company
    ordering = ["name"]
    paginate_by = 25
    search_fields = ["name", "email"]
    digit_search_fields = ["cnpj", "phone"]


class CompanyCreateView(SuccessMessageMixin, CreateView):
    model = Company
    form_class = CompanyForm
    success_url = reverse_lazy("management:company_list")
    success_message = "Construtora %(name)s cadastrada."


class CompanyUpdateView(SuccessMessageMixin, UpdateView):
    model = Company
    form_class = CompanyForm
    success_url = reverse_lazy("management:company_list")
    success_message = "Construtora %(name)s atualizada."


# Estruturas --------------------------------------------------------------------
# Só a equipe mantém o catálogo; usuários comuns apenas escolhem estruturas no empreendimento


class FacilityListView(StaffRequiredMixin, SearchMixin, ListView):
    model = Facility
    paginate_by = 50
    # O slug permite buscar sem acento: "natacao" encontra "Natação"
    search_fields = ["label", "slug"]

    def get_queryset(self):
        # Com a agregação o Meta.ordering não vale, então a ordem é explícita
        return super().get_queryset().annotate(estate_count=Count("estates")).order_by("label")


class FacilityCreateView(StaffRequiredMixin, SuccessMessageMixin, CreateView):
    model = Facility
    form_class = FacilityForm
    success_url = reverse_lazy("management:facility_list")

    def get_success_message(self, cleaned_data):
        return f"Estrutura {self.object} cadastrada."


class FacilityUpdateView(StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Facility
    form_class = FacilityForm
    success_url = reverse_lazy("management:facility_list")

    def get_success_message(self, cleaned_data):
        return f"Estrutura {self.object} atualizada."


# Empreendimentos ---------------------------------------------------------------


class EstateListView(SearchMixin, ListView):
    model = Estate
    paginate_by = 25
    search_fields = ["name", "company__name", "street", "district", "city__name", "city__state"]
    digit_search_fields = ["cep"]

    def get_queryset(self):
        # Situação atual = status do evento mais recente de cada empreendimento
        latest_status = TrackingEvent.objects.filter(estate=OuterRef("pk")).values("status")[:1]
        return (
            super()
            .get_queryset()
            .select_related("company", "city")
            .annotate(status=Subquery(latest_status))
            .order_by("name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for estate in context["estate_list"]:
            estate.status_label = TrackingEvent.Status(estate.status).label
        return context


class EstateFacilitiesMixin:
    """Edita as estruturas (EstateFacility) junto com o formulário do empreendimento.

    O formulário e o formset são validados juntos e salvos na mesma transação.
    """

    def get_facility_formset(self):
        data = self.request.POST if self.request.method == "POST" else None
        # Ao cadastrar, o empreendimento ainda não existe: o formset usa uma instância vazia
        return EstateFacilityFormSet(
            data, instance=self.object or Estate(), prefix="facilities"
        )

    def post(self, request, *args, **kwargs):
        self.object = self.get_object() if "pk" in kwargs else None
        form = self.get_form()
        self.facility_formset = self.get_facility_formset()
        if form.is_valid() and self.facility_formset.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            self.facility_formset.instance = self.object
            self.facility_formset.save()
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["facility_formset"] = getattr(self, "facility_formset", None) or (
            self.get_facility_formset()
        )
        return context


class EstateCreateView(EstateFacilitiesMixin, SuccessMessageMixin, CreateView):
    model = Estate
    form_class = EstateForm
    success_url = reverse_lazy("management:estate_list")
    success_message = "Empreendimento %(name)s cadastrado."

    def form_valid(self, form):
        response = super().form_valid(form)
        # O evento inicial é criado no save() do modelo, que não conhece o usuário
        self.object.tracking_events.update(created_by=self.request.user)
        return response


class EstateUpdateView(EstateFacilitiesMixin, SuccessMessageMixin, UpdateView):
    model = Estate
    form_class = EstateForm
    success_url = reverse_lazy("management:estate_list")
    success_message = "Empreendimento %(name)s atualizado."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tracking_events"] = self.object.tracking_events.select_related("created_by")
        context["payment_terms"] = self.object.paymentterms_set.all()
        return context


# Eventos de acompanhamento -----------------------------------------------------


class TrackingEventCreateView(SuccessMessageMixin, CreateView):
    model = TrackingEvent
    form_class = TrackingEventForm

    def dispatch(self, request, *args, **kwargs):
        self.estate = get_object_or_404(Estate, pk=kwargs["estate_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # O clean() do modelo compara com os eventos do empreendimento, então a
        # instância precisa conhecê-lo antes da validação
        kwargs["instance"] = TrackingEvent(estate=self.estate, created_by=self.request.user)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["estate"] = self.estate
        context["current_event"] = self.estate.tracking_events.first()
        return context

    def get_success_url(self):
        return reverse("management:estate_update", args=[self.estate.pk])

    def get_success_message(self, cleaned_data):
        return f"Situação de {self.estate.name} alterada para {self.object.get_status_display()}."


# Condições de pagamento --------------------------------------------------------


class PaymentTermsMixin(SuccessMessageMixin):
    """Condições de pagamento ficam dentro do empreendimento e voltam para a página dele."""

    model = PaymentTerms
    form_class = PaymentTermsForm

    def get_success_url(self):
        return reverse("management:estate_update", args=[self.object.estate_id])


class PaymentTermsCreateView(PaymentTermsMixin, CreateView):
    success_message = "Condição de pagamento cadastrada."

    def dispatch(self, request, *args, **kwargs):
        self.estate = get_object_or_404(Estate, pk=kwargs["estate_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = PaymentTerms(estate=self.estate)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["estate"] = self.estate
        return context


class PaymentTermsUpdateView(PaymentTermsMixin, UpdateView):
    success_message = "Condição de pagamento atualizada."

    def get_queryset(self):
        return PaymentTerms.objects.select_related("estate")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["estate"] = self.object.estate
        return context


class PaymentTermsDeleteView(DeleteView):
    model = PaymentTerms
    http_method_names = ["post"]

    def form_valid(self, form):
        messages.success(self.request, "Condição de pagamento excluída.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("management:estate_update", args=[self.object.estate_id])
