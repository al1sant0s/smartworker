from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from PIL import Image

from management.models import Company, Estate, TrackingEvent


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
        ordering = ["url"]

    def __str__(self):
        return f"{self.url} ({self.description})" if self.description else self.url


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
        ordering = ["email"]

    def __str__(self):
        return f"{self.email} ({self.description})" if self.description else self.email


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
        ordering = ["phone"]

    def __str__(self):
        phone = self.phone.as_national
        return f"{phone} ({self.description})" if self.description else phone


class CheckListQuerySet(models.QuerySet):
    def create_for_month(self, reference_month):
        """Cria um checklist pendente para cada empreendimento ativo que ainda não tem um no mês.

        Usado pelo comando create_monthly_checklists e pela lista de checklists.
        Retorna os checklists criados.
        """
        reference_month = reference_month.replace(day=1)
        existing = CheckList.objects.filter(reference_month=reference_month).values("estate_id")
        events = TrackingEvent.objects.tracked().exclude(estate_id__in=existing)
        return CheckList.objects.bulk_create(
            [
                CheckList(estate_id=event.estate_id, reference_month=reference_month)
                for event in events
            ],
            ignore_conflicts=True,
        )


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
        AVAILABLE = "AVAILABLE", _("Disponível")

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

    objects = CheckListQuerySet.as_manager()

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
        if self.file and self.is_image:
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

    @property
    def is_image(self):
        return self.extension in IMAGE_EXTENSIONS

    def __str__(self):
        return Path(self.file.name).name
