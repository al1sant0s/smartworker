from django import forms

from .models import Company, Estate


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
    class Meta:
        model = Estate
        # As estruturas (facilities) têm dados próprios na tabela intermediária
        # e serão cadastradas à parte
        fields = [
            "name",
            "company",
            "address",
            "cartographic_id",
            "block",
            "lot",
            "sea_distance",
            "sales_start",
            "delivery_date",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
            # O seletor de data do navegador exige o formato ISO
            "sales_start": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "delivery_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company"].queryset = Company.objects.order_by("name")
