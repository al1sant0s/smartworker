from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import OuterRef, Subquery
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from .forms import CompanyForm, EstateForm
from .models import Company, Estate, TrackingEvent


class IndexView(TemplateView):
    template_name = "management/index.html"


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
            Estate.objects.select_related("company")
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
