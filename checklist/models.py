from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from PIL import Image

from management.models import Company, Estate


class SourceHyperLink(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, verbose_name="Construtora"
    )
    # Empreendimentos que usam esta fonte (acessível via estate.source_hyperlinks)
    estates = models.ManyToManyField(
        Estate,
        blank=True,
        related_name="source_hyperlinks",
        verbose_name="Empreendimentos",
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
    # Empreendimentos que usam esta fonte (acessível via estate.source_emails)
    estates = models.ManyToManyField(
        Estate, blank=True, related_name="source_emails", verbose_name="Empreendimentos"
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
    # Empreendimentos que usam esta fonte (acessível via estate.source_phones)
    estates = models.ManyToManyField(
        Estate, blank=True, related_name="source_phones", verbose_name="Empreendimentos"
    )
    phone = PhoneNumberField(unique=True, region="BR", verbose_name="Telefone")
    description = models.TextField(blank=True, default="", verbose_name="Descrição")

    class Meta:
        verbose_name = "Telefone para contato"
        verbose_name_plural = "Telefones para contato"


class CheckList(models.Model):
    """Verificação mensal de um empreendimento.

    As fontes ficam no empreendimento (estate.source_hyperlinks, etc.),
    então cada novo checklist mensal usa automaticamente as fontes atuais.
    """

    class StatusCheck(models.TextChoices):
        PENDING = "PENDING", _("Pendente")
        UP_TO_DATE = "UP_TO_DATE", _("Atualizado")
        OUTDATED = "OUTDATED", _("Desatualizado")
        UNAVAILABLE = "UNAVAILABLE", _("Indisponível")

    estate = models.ForeignKey(
        Estate, on_delete=models.CASCADE, verbose_name="Empreendimento"
    )
    # Sempre o 1º dia do mês de referência (normalizado em clean())
    reference_month = models.DateField(verbose_name="Mês de referência")
    status = models.CharField(
        max_length=32,
        choices=StatusCheck,
        default=StatusCheck.PENDING,
        verbose_name="Situação",
    )
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="Verificado por",
    )
    checked_at = models.DateTimeField(
        blank=True, null=True, verbose_name="Verificado em"
    )

    class Meta:
        verbose_name = "Checklist"
        verbose_name_plural = "Checklists"
        ordering = ["-reference_month", "estate__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["estate", "reference_month"],
                name="unique_checklist_per_estate_month",
                violation_error_message="Já existe um checklist para este empreendimento neste mês.",
            )
        ]

    def clean(self):
        super().clean()
        if self.reference_month:
            self.reference_month = self.reference_month.replace(day=1)

    def __str__(self):
        return f"{self.estate} - {self.reference_month:%m/%Y}"


# Apenas formatos abertos, para facilitar o uso dos arquivos por outros programas.
# Formatos proprietários (doc, xlsx...) devem ser convertidos (pdf, csv...) antes do envio.
DOCUMENT_EXTENSIONS = ["pdf", "txt", "csv", "odt", "ods"]
IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "webp", "gif"]


def availability_sheet_path(instance, filename):
    # Ex: checklists/12/2026-10/tabela-precos.pdf
    checklist = instance.checklist
    return f"checklists/{checklist.estate_id}/{checklist.reference_month:%Y-%m}/{filename}"


class AvailabilitySheet(models.Model):
    """Arquivo (tabela de preços/disponibilidade) enviado para um checklist."""

    checklist = models.ForeignKey(
        "CheckList",
        on_delete=models.CASCADE,
        related_name="sheets",
        verbose_name="Checklist",
    )
    file = models.FileField(
        "Arquivo",
        upload_to=availability_sheet_path,
        validators=[
            FileExtensionValidator(DOCUMENT_EXTENSIONS + IMAGE_EXTENSIONS)
        ],
        help_text="Formatos aceitos: " + ", ".join(DOCUMENT_EXTENSIONS + IMAGE_EXTENSIONS),
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Enviado em")

    class Meta:
        verbose_name = "Tabela de preços"
        verbose_name_plural = "Tabelas de preços"
        ordering = ["-uploaded_at"]

    def clean(self):
        super().clean()
        # A extensão sozinha não garante o conteúdo: confere se imagens abrem de fato
        if self.file and self.extension in IMAGE_EXTENSIONS:
            try:
                self.file.seek(0)
                Image.open(self.file).verify()
            except Exception:
                raise ValidationError({"file": "O arquivo não é uma imagem válida."})
            finally:
                self.file.seek(0)

    @property
    def extension(self):
        return Path(self.file.name).suffix.lower().lstrip(".")

    def __str__(self):
        return Path(self.file.name).name
