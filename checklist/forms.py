from django import forms

from .models import AvailabilitySheet, CheckList, SourceEmail, SourceHyperLink, SourcePhone


class SourceHyperLinkForm(forms.ModelForm):
    class Meta:
        model = SourceHyperLink
        fields = ["url", "description"]
        widgets = {
            "url": forms.URLInput(attrs={"placeholder": "https://construtora.com.br/empreendimento"}),
            "description": forms.TextInput(attrs={"placeholder": "Ex: página de vendas"}),
        }


class SourceEmailForm(forms.ModelForm):
    class Meta:
        model = SourceEmail
        fields = ["email", "description"]
        widgets = {
            "email": forms.EmailInput(attrs={"placeholder": "vendas@construtora.com.br"}),
            "description": forms.TextInput(attrs={"placeholder": "Ex: comercial"}),
        }


class SourcePhoneForm(forms.ModelForm):
    class Meta:
        model = SourcePhone
        fields = ["phone", "description"]
        widgets = {
            "phone": forms.TextInput(attrs={"placeholder": "(48) 3333-4444", "type": "tel"}),
            "description": forms.TextInput(attrs={"placeholder": "Ex: WhatsApp do corretor"}),
        }


class LinkExistingSourceForm(forms.Form):
    """Vincula ao empreendimento uma fonte já cadastrada da mesma construtora."""

    source = forms.ModelChoiceField(queryset=None, label="Fonte já cadastrada")

    def __init__(self, *args, queryset, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["source"].queryset = queryset


class CheckListResultForm(forms.ModelForm):
    """Resultado da verificação; "Pendente" é só o estado inicial."""

    class Meta:
        model = CheckList
        fields = ["status"]
        labels = {"status": "Resultado"}
        widgets = {"status": forms.RadioSelect(attrs={"class": "form-check-input"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [
            choice
            for choice in CheckList.StatusCheck.choices
            if choice[0] != CheckList.StatusCheck.PENDING
        ]


class AvailabilitySheetForm(forms.ModelForm):
    class Meta:
        model = AvailabilitySheet
        fields = ["file"]
