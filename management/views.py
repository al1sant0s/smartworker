from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import OuterRef, Subquery
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from .forms import CompanyForm, EstateForm, TrackingEventForm
from .models import City, Company, Estate, State, TrackingEvent


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


class CompanyListView(ListView):
    model = Company
    ordering = ["name"]
    paginate_by = 25


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


# Empreendimentos ---------------------------------------------------------------


class EstateListView(ListView):
    model = Estate
    paginate_by = 25

    def get_queryset(self):
        # Situação atual = status do evento mais recente de cada empreendimento
        latest_status = TrackingEvent.objects.filter(estate=OuterRef("pk")).values("status")[:1]
        return (
            Estate.objects.select_related("company", "city")
            .annotate(status=Subquery(latest_status))
            .order_by("name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for estate in context["estate_list"]:
            estate.status_label = TrackingEvent.Status(estate.status).label
        return context


class EstateCreateView(SuccessMessageMixin, CreateView):
    model = Estate
    form_class = EstateForm
    success_url = reverse_lazy("management:estate_list")
    success_message = "Empreendimento %(name)s cadastrado."

    def form_valid(self, form):
        response = super().form_valid(form)
        # O evento inicial é criado no save() do modelo, que não conhece o usuário
        self.object.tracking_events.update(created_by=self.request.user)
        return response


class EstateUpdateView(SuccessMessageMixin, UpdateView):
    model = Estate
    form_class = EstateForm
    success_url = reverse_lazy("management:estate_list")
    success_message = "Empreendimento %(name)s atualizado."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tracking_events"] = self.object.tracking_events.select_related("created_by")
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
