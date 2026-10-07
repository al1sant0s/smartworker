import re
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Max, Subquery
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    phone = PhoneNumberField(
        unique=True, blank=True, null=True, region="BR", verbose_name="Telefone"
    )


class Company(models.Model):
    cnpj = models.CharField(
        max_length=18,
        unique=True,
        verbose_name="CNPJ",
        help_text="Com ou sem pontuação (ex: 12.345.678/0001-95)",
    )
    name = models.CharField(max_length=64, verbose_name="Nome")
    email = models.EmailField(unique=True, blank=True, null=True)
    phone = PhoneNumberField(
        unique=True, blank=True, null=True, region="BR", verbose_name="Telefone"
    )

    class Meta:
        verbose_name = "Construtora"
        verbose_name_plural = "Construtoras"

    def clean(self):
        super().clean()
        if not self.cnpj:
            return

        # Remove pontuação (pontos, barras, traços e espaços) e converte para maiúsculo
        # Ex: "12.345.678/0001-95" vira "12345678000195"
        # Letras são mantidas por causa do CNPJ alfanumérico (a partir de julho/2026)
        self.cnpj = re.sub(r"[^A-Za-z0-9]", "", self.cnpj).upper()

        if not re.fullmatch(r"[A-Z0-9]{12}\d{2}", self.cnpj):
            raise ValidationError(
                {"cnpj": "O CNPJ deve ter 14 caracteres (12 letras/números + 2 dígitos verificadores)."}
            )
        if not self._cnpj_check_digits_ok(self.cnpj):
            raise ValidationError({"cnpj": "CNPJ inválido."})

    @staticmethod
    def _cnpj_check_digits_ok(cnpj):
        # Sequências repetidas (ex: "00000000000000") passam no cálculo, mas são inválidas
        if len(set(cnpj)) == 1:
            return False
        # Cada caractere vale seu código ASCII - 48 ("0"-"9" -> 0-9, "A"-"Z" -> 17-42)
        values = [ord(c) - 48 for c in cnpj]
        for size in (12, 13):
            weights = [(i % 8) + 2 for i in range(size)][::-1]
            remainder = sum(v * w for v, w in zip(values, weights)) % 11
            digit = 0 if remainder < 2 else 11 - remainder
            if values[size] != digit:
                return False
        return True

    @property
    def cnpj_display(self):
        """CNPJ com pontuação para exibição (ex: '12.345.678/0001-95')."""
        c = self.cnpj
        if len(c) != 14:
            return c
        return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"

    def __str__(self):
        return f"{self.name} (CNPJ: {self.cnpj_display})"


class Facility(models.Model):
    """
    Cadastra os tipos de estruturas em formato slug/snake_case.
    Exemplo no banco: 'piscina_infantil', 'salao_de_festas'
    """

    name = models.CharField(max_length=64, unique=True, verbose_name="Identificador")

    class Meta:
        verbose_name = "Estrutura / Comodidade"
        verbose_name_plural = "Estruturas / Comodidades"
        ordering = ["name"]

    def clean(self):
        super().clean()
        if not self.name:
            return
        # 1. Limpa espaços nas extremidades e converte para minúsculo
        cleaned = self.name.strip().lower()
        # 2. Converte espaços e hífens repetidos em um único underscore
        self.name = re.sub(r"[\s-]+", "_", cleaned)

    @property
    def display_name(self):
        """Retorna a string formatada para exibição (ex: 'Piscina infantil')"""
        return self.name.replace("_", " ").capitalize()

    def __str__(self):
        return self.display_name


class Estate(models.Model):
    """Modelo do Empreendimento"""

    name = models.CharField(max_length=64, verbose_name="Nome")
    company = models.ForeignKey(
        "Company", on_delete=models.CASCADE, verbose_name="Construtora"
    )
    address = models.TextField(verbose_name="Endereço")
    cartographic_id = models.CharField(
        max_length=32, verbose_name="Identificação cartográfica", blank=True, null=True
    )
    block = models.PositiveIntegerField(verbose_name="Quadra", blank=True, null=True)
    lot = models.PositiveIntegerField(verbose_name="Lote", blank=True, null=True)
    sea_distance = models.PositiveIntegerField(
        verbose_name="Distância ao mar (metros)", blank=True, null=True
    )
    sales_start = models.DateField(verbose_name="Início das vendas")
    delivery_date = models.DateField(verbose_name="Data da entrega")

    # Relacionamento M2M através da tabela intermediária
    facilities = models.ManyToManyField(
        Facility,
        through="EstateFacility",
        related_name="estates",
        verbose_name="Estruturas",
    )

    class Meta:
        verbose_name = "Empreendimento"
        verbose_name_plural = "Empreendimentos"

    def clean(self):
        super().clean()
        # Datas inválidas já geraram erro próprio em clean_fields()
        if self.sales_start and self.delivery_date and self.delivery_date <= self.sales_start:
            raise ValidationError(
                {"delivery_date": "A data da entrega deve ser posterior ao início das vendas."}
            )

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            # Todo empreendimento começa com um evento, então sempre há uma situação atual
            TrackingEvent.objects.create(
                estate=self,
                status=TrackingEvent.Status.ACTIVE,
                note="Empreendimento cadastrado",
            )

    def __str__(self):
        return self.name


class TrackingEventQuerySet(models.QuerySet):
    def latest_per_estate(self):
        """O evento mais recente (maior pk) de cada empreendimento, ou seja, a situação atual.

        Como eventos não podem ser retroativos, o maior pk é também o de data mais recente.
        """
        latest_ids = (
            TrackingEvent.objects.values("estate")
            .annotate(last_id=Max("pk"))
            .values("last_id")
        )
        return self.filter(pk__in=Subquery(latest_ids))

    def tracked(self):
        """Situação atual dos empreendimentos ativos (que recebem checklists mensais)."""
        return self.latest_per_estate().filter(status=TrackingEvent.Status.ACTIVE)


class TrackingEvent(models.Model):
    """Mudança na situação de acompanhamento de um empreendimento (ex: esgotado, distrato)."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Ativo"
        SOLD_OUT = "SOLD_OUT", "Esgotado"
        CANCELLED = "CANCELLED", "Cancelado"
        PAUSED = "PAUSED", "Pausado"

    estate = models.ForeignKey(
        Estate,
        on_delete=models.CASCADE,
        related_name="tracking_events",
        verbose_name="Empreendimento",
    )
    status = models.CharField(
        max_length=16, choices=Status, verbose_name="Nova situação"
    )
    date = models.DateField(default=timezone.localdate, verbose_name="Data")
    note = models.TextField(blank=True, default="", verbose_name="Observação")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="Registrado por",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Registrado em")

    objects = TrackingEventQuerySet.as_manager()

    class Meta:
        verbose_name = "Evento de acompanhamento"
        verbose_name_plural = "Eventos de acompanhamento"
        # Ordem de registro; o primeiro da lista é sempre a situação atual
        ordering = ["-pk"]

    def clean(self):
        super().clean()
        if not self.estate_id or not self.status or not self.date:
            return

        # Eventos vizinhos na ordem de registro (ao editar, ignora o próprio evento)
        events = self.estate.tracking_events.all()
        previous = (events.filter(pk__lt=self.pk) if self.pk else events).first()
        following = events.filter(pk__gt=self.pk).last() if self.pk else None

        errors = {}
        if previous:
            if previous.status == self.status:
                errors["status"] = (
                    f"O empreendimento já está com a situação “{self.get_status_display()}”."
                )
            if self.date < previous.date:
                errors["date"] = (
                    "A data não pode ser anterior ao último evento "
                    f"({previous.date:%d/%m/%Y})."
                )
        if following:
            if following.status == self.status:
                errors["status"] = (
                    f"O evento seguinte já tem a situação “{self.get_status_display()}”."
                )
            if self.date > following.date:
                errors["date"] = (
                    f"A data não pode ser posterior ao evento seguinte ({following.date:%d/%m/%Y})."
                )
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.estate}: {self.get_status_display()} em {self.date:%d/%m/%Y}"


class EstateFacility(models.Model):
    """Tabela intermediária com metadados adicionais de cada estrutura por empreendimento"""

    estate = models.ForeignKey(
        Estate, on_delete=models.CASCADE, verbose_name="Empreendimento"
    )
    facility = models.ForeignKey(
        Facility, on_delete=models.CASCADE, verbose_name="Estrutura"
    )

    # Detalhes específicos dessa estrutura neste empreendimento
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantidade")
    area = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True, verbose_name="Área (m²)"
    )
    floor = models.CharField(
        max_length=32, blank=True, null=True, verbose_name="Pavimento / Andar"
    )

    class Meta:
        verbose_name = "Estrutura do Empreendimento"
        verbose_name_plural = "Estruturas do Empreendimento"
        unique_together = ("estate", "facility")

    def __str__(self):
        return f"{self.facility.display_name} em {self.estate.name}"


class PaymentTerms(models.Model):
    estate = models.ForeignKey(
        Estate, on_delete=models.CASCADE, verbose_name="Empreendimento"
    )
    down_payment = models.DecimalField(
        verbose_name="Sinal (%)",
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    key_payment = models.DecimalField(
        verbose_name="Chaves ou habite-se (%)",
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    monthly_payment = models.DecimalField(
        verbose_name="Mensais (%)",
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    monthly_installments = models.PositiveIntegerField(
        default=0, verbose_name="Mensais (parcelas)"
    )
    balloon_payment = models.DecimalField(
        verbose_name="Intercaladas (%)",
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    balloon_installments = models.PositiveIntegerField(
        default=0, verbose_name="Intercaladas (parcelas)"
    )

    class Meta:
        verbose_name = "Condição de pagamento"
        verbose_name_plural = "Condições de pagamento"

    def clean(self):
        super().clean()
        percentages = [
            self.down_payment,
            self.key_payment,
            self.monthly_payment,
            self.balloon_payment,
        ]
        # Algum campo inválido já gerou erro próprio em clean_fields()
        if None in percentages:
            return

        errors = {}
        total = sum(percentages)
        if total != Decimal("100.00"):
            errors["__all__"] = f"A soma dos percentuais deve ser 100% (atual: {total}%)."

        # Percentual e número de parcelas precisam ser coerentes
        for pct, qty, label in [
            ("monthly_payment", "monthly_installments", "mensais"),
            ("balloon_payment", "balloon_installments", "intercaladas"),
        ]:
            has_pct = getattr(self, pct) > 0
            has_qty = (getattr(self, qty) or 0) > 0
            if has_pct and not has_qty:
                errors[qty] = f"Informe o número de parcelas {label}."
            elif has_qty and not has_pct:
                errors[pct] = f"Informe o percentual das parcelas {label}."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"{self.estate}: sinal {self.down_payment}% · "
            f"chaves {self.key_payment}% · "
            f"{self.monthly_installments}x mensais ({self.monthly_payment}%) · "
            f"{self.balloon_installments}x intercaladas ({self.balloon_payment}%)"
        )
