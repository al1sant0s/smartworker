from django import forms
from django.urls import reverse

from .models import City, Company, Estate, State, TrackingEvent


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
