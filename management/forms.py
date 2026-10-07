from django import forms

from .models import Company


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ["name", "cnpj", "email", "phone"]
        widgets = {
            "cnpj": forms.TextInput(attrs={"placeholder": "12.345.678/0001-95"}),
            "email": forms.EmailInput(attrs={"placeholder": "contato@construtora.com.br"}),
            "phone": forms.TextInput(attrs={"placeholder": "(11) 91234-5678", "type": "tel"}),
        }
