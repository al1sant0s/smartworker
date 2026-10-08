from datetime import date, timedelta

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DeleteView, ListView, TemplateView, UpdateView

from management.mixins import SearchMixin
from management.models import Estate

from .forms import (
    AvailabilitySheetForm,
    CheckListResultForm,
    LinkExistingSourceForm,
    SourceEmailForm,
    SourceHyperLinkForm,
    SourcePhoneForm,
)
from .models import AvailabilitySheet, CheckList, SourceEmail, SourceHyperLink, SourcePhone

# Tipos de fonte: modelo, formulário e o related_name no empreendimento
SOURCE_KINDS = {
    "link": {
        "model": SourceHyperLink,
        "form": SourceHyperLinkForm,
        "related": "source_hyperlinks",
        "title": "Links",
        "icon": "bi-link-45deg",
    },
    "email": {
        "model": SourceEmail,
        "form": SourceEmailForm,
        "related": "source_emails",
        "title": "Emails",
        "icon": "bi-envelope",
    },
    "phone": {
        "model": SourcePhone,
        "form": SourcePhoneForm,
        "related": "source_phones",
        "title": "Telefones",
        "icon": "bi-telephone",
    },
}


def parse_month(value):
    """Converte "AAAA-MM" no 1º dia do mês; vazio ou inválido vira o mês atual."""
    try:
        year, month = map(int, value.split("-"))
        return date(year, month, 1)
    except (AttributeError, ValueError):
        return timezone.localdate().replace(day=1)


# Fontes do empreendimento ------------------------------------------------------


class EstateSourcesView(TemplateView):
    """Fontes (links, emails, telefones) de um empreendimento.

    Na mesma página: cadastrar uma fonte nova, vincular uma já cadastrada da
    construtora e desvincular. Cada formulário envia "kind" e "action".
    """

    template_name = "checklist/estate_sources.html"

    def dispatch(self, request, *args, **kwargs):
        self.estate = get_object_or_404(
            Estate.objects.select_related("company"), pk=kwargs["estate_pk"]
        )
        # Formulários com erro, para reexibir na página: {(kind, action): form}
        self.bound_forms = {}
        return super().dispatch(request, *args, **kwargs)

    def linkable_sources(self, kind):
        """Fontes da construtora ainda não vinculadas a este empreendimento."""
        model = SOURCE_KINDS[kind]["model"]
        return model.objects.filter(company=self.estate.company).exclude(estates=self.estate)

    def new_form(self, kind, data=None):
        config = SOURCE_KINDS[kind]
        # A construtora da fonte é a do empreendimento
        instance = config["model"](company=self.estate.company)
        return config["form"](data, instance=instance, prefix=f"{kind}-new")

    def link_form(self, kind, data=None):
        return LinkExistingSourceForm(
            data, queryset=self.linkable_sources(kind), prefix=f"{kind}-link"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["estate"] = self.estate
        context["sections"] = [
            {
                "kind": kind,
                "title": config["title"],
                "icon": config["icon"],
                # estate_count: em quantos empreendimentos a fonte é usada (aviso ao excluir)
                # (contar direto em estate.<related> só veria este empreendimento, por causa do filtro)
                "sources": config["model"]
                .objects.filter(pk__in=getattr(self.estate, config["related"]).values("pk"))
                .annotate(estate_count=Count("estates")),
                "new_form": self.bound_forms.get((kind, "new")) or self.new_form(kind),
                "link_form": self.bound_forms.get((kind, "link")) or self.link_form(kind),
            }
            for kind, config in SOURCE_KINDS.items()
        ]
        return context

    def post(self, request, *args, **kwargs):
        kind = request.POST.get("kind")
        action = request.POST.get("action")
        if kind not in SOURCE_KINDS:
            raise Http404
        related = getattr(self.estate, SOURCE_KINDS[kind]["related"])

        if action == "new":
            form = self.new_form(kind, request.POST)
            if form.is_valid():
                source = form.save()
                source.estates.add(self.estate)
                messages.success(request, f"{source} cadastrado e vinculado.")
                return redirect(self.success_url(kind))
            self.bound_forms[(kind, "new")] = form

        elif action == "link":
            form = self.link_form(kind, request.POST)
            if form.is_valid():
                source = form.cleaned_data["source"]
                source.estates.add(self.estate)
                messages.success(request, f"{source} vinculado.")
                return redirect(self.success_url(kind))
            self.bound_forms[(kind, "link")] = form

        elif action == "unlink":
            source = get_object_or_404(related, pk=request.POST.get("source"))
            related.remove(source)
            messages.success(request, f"{source} desvinculado deste empreendimento.")
            return redirect(self.success_url(kind))

        elif action == "delete":
            # Excluir remove a fonte de todos os empreendimentos que a usam
            source = get_object_or_404(related, pk=request.POST.get("source"))
            source.delete()
            messages.success(request, f"{source} excluído.")
            return redirect(self.success_url(kind))

        else:
            raise Http404

        return self.render_to_response(self.get_context_data())

    def success_url(self, kind):
        url = reverse("checklist:estate_sources", args=[self.estate.pk])
        return f"{url}#{kind}"


# Checklists --------------------------------------------------------------------


class CheckListListView(SearchMixin, ListView):
    """Checklists de um mês (?month=AAAA-MM), com filtro por situação (?status=) e busca (?q=)."""

    model = CheckList
    paginate_by = 50
    search_fields = [
        "estate__name",
        "estate__company__name",
        "estate__city__name",
        "checked_by__email",
    ]

    def get(self, request, *args, **kwargs):
        self.month = parse_month(request.GET.get("month"))
        self.status = request.GET.get("status", "")
        if self.status not in CheckList.StatusCheck.values:
            self.status = ""
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .filter(reference_month=self.month)
            .select_related("estate", "estate__company", "estate__city", "checked_by")
            .order_by("estate__name")
        )
        if self.status:
            queryset = queryset.filter(status=self.status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Contagem do mês inteiro, independente do filtro de situação
        counts = CheckList.objects.filter(reference_month=self.month).aggregate(
            total=Count("pk"),
            **{
                value.lower(): Count("pk", filter=Q(status=value))
                for value in CheckList.StatusCheck.values
            },
        )
        previous_month = (self.month - timedelta(days=1)).replace(day=1)
        next_month = (self.month.replace(day=28) + timedelta(days=4)).replace(day=1)
        context.update(
            month=self.month,
            previous_month=previous_month,
            next_month=next_month,
            status=self.status,
            # Abas de filtro: (valor, rótulo, quantidade no mês)
            status_tabs=[
                (value, label, counts[value.lower()])
                for value, label in CheckList.StatusCheck.choices
            ],
            counts=counts,
            checked=counts["total"] - counts["pending"],
        )
        return context


class CheckListGenerateView(View):
    """Cria os checklists do mês (mesma lógica do comando create_monthly_checklists)."""

    http_method_names = ["post"]

    def post(self, request):
        month = parse_month(request.POST.get("month"))
        created = CheckList.objects.create_for_month(month)
        if created:
            messages.success(request, f"{len(created)} checklist(s) criado(s) para {month:%m/%Y}.")
        else:
            messages.info(request, f"Todos os empreendimentos ativos já têm checklist em {month:%m/%Y}.")
        return redirect(f"{reverse('checklist:checklist_list')}?month={month:%Y-%m}")


class CheckListDetailView(SuccessMessageMixin, UpdateView):
    """Tela de verificação: fontes, envio de tabelas e resultado do checklist."""

    model = CheckList
    form_class = CheckListResultForm
    template_name = "checklist/checklist_detail.html"
    success_message = "Checklist de %(estate)s salvo."

    def get_queryset(self):
        return CheckList.objects.select_related("estate", "estate__company", "estate__city")

    def month_pending(self):
        """Outros checklists pendentes do mesmo mês, em ordem de empreendimento."""
        return (
            CheckList.objects.filter(
                reference_month=self.object.reference_month,
                status=CheckList.StatusCheck.PENDING,
            )
            .exclude(pk=self.object.pk)
            .select_related("estate")
            .order_by("estate__name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estate = self.object.estate
        name = estate.name
        pending = self.month_pending()
        context.update(
            estate=estate,
            links=estate.source_hyperlinks.all(),
            emails=estate.source_emails.all(),
            phones=estate.source_phones.all(),
            sheets=self.object.sheets.all(),
            previous_pending=pending.filter(estate__name__lt=name).last(),
            next_pending=pending.filter(estate__name__gt=name).first(),
        )
        context.setdefault("sheet_form", AvailabilitySheetForm())
        return context

    def post(self, request, *args, **kwargs):
        if "upload" not in request.POST:
            return super().post(request, *args, **kwargs)

        self.object = self.get_object()
        form = AvailabilitySheetForm(
            request.POST, request.FILES, instance=AvailabilitySheet(checklist=self.object)
        )
        if form.is_valid():
            sheet = form.save()
            messages.success(request, f"Arquivo {sheet} enviado.")
            return redirect(self.object_url(self.object))
        return self.render_to_response(
            self.get_context_data(form=self.get_form_class()(instance=self.object), sheet_form=form)
        )

    def form_valid(self, form):
        form.instance.checked_by = self.request.user
        form.instance.checked_at = timezone.now()
        return super().form_valid(form)

    def get_success_message(self, cleaned_data):
        return self.success_message % {"estate": self.object.estate}

    def get_success_url(self):
        # "Salvar e ir para o próximo" segue para o próximo pendente do mês
        if "save_next" in self.request.POST:
            next_pending = self.month_pending().first()
            if next_pending:
                return self.object_url(next_pending)
            return f"{reverse('checklist:checklist_list')}?month={self.object.reference_month:%Y-%m}"
        return self.object_url(self.object)

    @staticmethod
    def object_url(checklist):
        return reverse("checklist:checklist_detail", args=[checklist.pk])


class CheckListDeleteView(DeleteView):
    """Exclui um checklist e seus arquivos (o django-cleanup apaga os arquivos do disco)."""

    model = CheckList
    http_method_names = ["post"]

    def form_valid(self, form):
        messages.success(self.request, f"Checklist de {self.object} excluído.")
        return super().form_valid(form)

    def get_success_url(self):
        return f"{reverse('checklist:checklist_list')}?month={self.object.reference_month:%Y-%m}"


class AvailabilitySheetDeleteView(DeleteView):
    """Remove um arquivo enviado (o django-cleanup apaga o arquivo do disco)."""

    model = AvailabilitySheet
    http_method_names = ["post"]

    def form_valid(self, form):
        messages.success(self.request, f"Arquivo {self.object} removido.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("checklist:checklist_detail", args=[self.object.checklist_id])
