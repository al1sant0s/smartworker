from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView

from .forms import CompanyForm
from .models import Company


class IndexView(TemplateView):
    template_name = "management/index.html"


class CompanyCreateView(SuccessMessageMixin, CreateView):
    model = Company
    form_class = CompanyForm
    # Trocar pela página da construtora quando existir a view de detalhe
    success_url = reverse_lazy("management:index")
    success_message = "Construtora %(name)s cadastrada."
