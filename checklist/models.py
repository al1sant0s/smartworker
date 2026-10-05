from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from management.models import Company, Estate


class SourceHyperLink(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, verbose_name="Construtora"
    )
    url = models.URLField(max_length=500, unique=True, verbose_name="URL")
    description = models.TextField(blank=True, default="", verbose_name="Descrição")

    class Meta:
        verbose_name = "Link"
        verbose_name_plural = "Links"


class SourceEmail(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, verbose_name="Construtora"
    )
    email = models.EmailField(unique=True, verbose_name="Email")
    description = models.TextField(blank=True, default="", verbose_name="Descrição")

    class Meta:
        verbose_name = "Email para contato"
        verbose_name_plural = "Emails para contato"


class SourcePhone(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, verbose_name="Construtora"
    )
    phone = PhoneNumberField(unique=True, region="BR", verbose_name="Telefone")
    description = models.TextField(blank=True, default="", verbose_name="Descrição")

    class Meta:
        verbose_name = "Telefone para contato"
        verbose_name_plural = "Telefones para contato"


class CheckList(models.Model):
    class StatusCheck(models.TextChoices):
        PENDING = "PENDING", _("Pendente")
        UP_TO_DATE = "UP_TO_DATE", _("Atualizado")
        OUTDATED = "OUTDATED", _("Desatualizado")
        UNAVAILABLE = "UNAVAILABLE", _("Indisponível")

    estate = models.ForeignKey(
        Estate, on_delete=models.CASCADE, verbose_name="Empreendimento"
    )
    source_hyperlink = models.ManyToManyField(
        SourceHyperLink, verbose_name="Links de origem"
    )
    source_email = models.ManyToManyField(
        SourceEmail, verbose_name="Emails para contato"
    )
    source_phone = models.ManyToManyField(
        SourcePhone, verbose_name="Telefones para contato"
    )
    date = models.DateField(auto_now=True, verbose_name="Data")
    status = models.CharField(
        max_length=32,
        choices=StatusCheck,
        default=StatusCheck.PENDING,
        verbose_name="Situação",
    )
