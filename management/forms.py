from django import forms
from django.urls import reverse

from .models import (
    City,
    Company,
    Estate,
    EstateFacility,
    Facility,
    PaymentTerms,
    State,
    TrackingEvent,
)


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ["name", "cnpj", "email", "phone"]
        widgets = {
            "cnpj": forms.TextInput(attrs={"placeholder": "12.345.678/0001-95"}),
            "email": forms.EmailInput(attrs={"placeholder": "contato@construtora.com.br"}),
            "phone": forms.TextInput(attrs={"placeholder": "(11) 91234-5678", "type": "tel"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ao editar, mostra os valores formatados em vez do formato salvo no banco
        if self.instance.pk:
            self.initial["cnpj"] = self.instance.cnpj_display
            if self.instance.phone:
                self.initial["phone"] = self.instance.phone.as_national


class EstateForm(forms.ModelForm):
    # A UF não é campo do modelo (vem do município); serve para filtrar os municípios
    state = forms.ChoiceField(
        choices=[("", "---------"), *State.choices],
        label="UF",
        # Ligado ao script de endereço (busca de CEP e lista de municípios)
        widget=forms.Select(attrs={"data-address": "state"}),
    )

    class Meta:
        model = Estate
        # As estruturas (facilities) têm dados próprios na tabela intermediária
        # e serão cadastradas à parte
        fields = [
            "name",
            "company",
            "cep",
            "street",
            "number",
            "complement",
            "district",
            "state",
            "city",
            "latitude",
            "longitude",
            "cartographic_id",
            "block",
            "lot",
            "sales_start",
            "delivery_date",
        ]
        widgets = {
            "cep": forms.TextInput(
                attrs={"placeholder": "88015-200", "inputmode": "numeric", "data-address": "cep"}
            ),
            "street": forms.TextInput(attrs={"data-address": "street"}),
            "number": forms.TextInput(attrs={"data-address": "number"}),
            "district": forms.TextInput(attrs={"data-address": "district"}),
            "city": forms.Select(attrs={"data-address": "city"}),
            "latitude": forms.NumberInput(attrs={"step": "0.000001", "placeholder": "-27.595378"}),
            "longitude": forms.NumberInput(attrs={"step": "0.000001", "placeholder": "-48.548050"}),
            # O seletor de data do navegador exige o formato ISO
            "sales_start": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "delivery_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company"].queryset = Company.objects.order_by("name")

        # UF escolhida: a enviada no formulário ou a do município já salvo
        if self.is_bound:
            state = self.data.get(self.add_prefix("state"), "")
        elif self.instance.pk:
            state = self.instance.city.state
            self.initial["state"] = state
            self.initial["cep"] = self.instance.cep_display
        else:
            state = ""

        # Só os municípios da UF; assim um município de outra UF não é aceito
        self.fields["city"].queryset = City.objects.filter(state=state)

        url = reverse("management:city_list")
        self.fields["state"].widget.attrs["data-cities-url"] = url


class TrackingEventForm(forms.ModelForm):
    """Registra uma mudança de situação. A instância já chega com o empreendimento."""

    class Meta:
        model = TrackingEvent
        fields = ["status", "date", "note"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "note": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Ex: unidades voltaram à venda após distrato"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A situação atual não é uma mudança; o clean() do modelo também bloqueia
        current = self.instance.estate.tracking_events.first()
        if current:
            self.fields["status"].choices = [
                choice for choice in self.fields["status"].choices if choice[0] != current.status
            ]


class FacilityForm(forms.ModelForm):
    class Meta:
        model = Facility
        fields = ["label"]
        help_texts = {
            "label": "Ex: Sala de musculação. É padronizado e identificado como sala_de_musculacao."
        }


class EstateFacilityForm(forms.ModelForm):
    class Meta:
        model = EstateFacility
        fields = ["facility", "quantity", "area", "floor"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"min": 1}),
            "area": forms.NumberInput(attrs={"step": "0.01", "min": 0}),
            "floor": forms.NumberInput(attrs={"step": 1, "placeholder": "0 = térreo"}),
        }


class BaseEstateFacilityFormSet(forms.BaseInlineFormSet):
    def get_unique_error_message(self, unique_check):
        return "Cada estrutura só pode aparecer uma vez no empreendimento."


# Estruturas do empreendimento, editadas junto com o formulário do empreendimento
EstateFacilityFormSet = forms.inlineformset_factory(
    Estate,
    EstateFacility,
    form=EstateFacilityForm,
    formset=BaseEstateFacilityFormSet,
    extra=0,
    can_delete=True,
)


class PaymentTermsForm(forms.ModelForm):
    class Meta:
        model = PaymentTerms
        fields = [
            "down_payment",
            "key_payment",
            "monthly_payment",
            "monthly_installments",
            "balloon_payment",
            "balloon_installments",
        ]
        widgets = {
            field: forms.NumberInput(attrs={"step": "0.01", "min": 0, "max": 100})
            for field in ["down_payment", "key_payment", "monthly_payment", "balloon_payment"]
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Parcelas em branco valem 0; o clean() do modelo cobra quando há percentual
        for field in ["monthly_installments", "balloon_installments"]:
            self.fields[field].required = False

    def clean_monthly_installments(self):
        return self.cleaned_data["monthly_installments"] or 0

    def clean_balloon_installments(self):
        return self.cleaned_data["balloon_installments"] or 0
