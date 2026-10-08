import re
import unicodedata
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Max, Subquery
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField


class CustomUserManager(UserManager):
    """Usuários identificados pelo e-mail, sem username."""

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("O e-mail é obrigatório.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Superusuário precisa de is_staff e is_superuser.")
        return self._create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    # O login é feito pelo e-mail
    username = None
    email = models.EmailField(unique=True, verbose_name="E-mail")
    phone = PhoneNumberField(
        unique=True, blank=True, null=True, region="BR", verbose_name="Telefone"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        # Usado nos registros (verificado por, registrado por): o nome é
        # definido só pelo admin e o e-mail identifica a pessoa sem ambiguidade
        name = self.get_full_name()
        return f"{name} ({self.email})" if name else self.email


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
    """Tipo de estrutura, com nome padronizado e identificador ASCII único.

    Ex: "sAlA de  MUSCULAçÃo" vira label "Sala de musculação" e slug "sala_de_musculacao".
    O slug (sem acentos) é o que garante a unicidade: "Natação" e "natacao" são a mesma.
    """

    label = models.CharField(max_length=64, verbose_name="Nome")
    slug = models.CharField(
        max_length=64, unique=True, editable=False, verbose_name="Identificador"
    )

    class Meta:
        verbose_name = "Estrutura / Comodidade"
        verbose_name_plural = "Estruturas / Comodidades"
        ordering = ["label"]

    @staticmethod
    def standardize_label(text):
        """Espaços extras removidos e só a primeira letra maiúscula."""
        return " ".join(text.split()).capitalize()

    @staticmethod
    def make_slug(label):
        """snake_case ASCII: sem acentos ("ç" vira "c") e só letras, números e "_"."""
        ascii_text = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode()
        return re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")

    def standardize(self):
        self.label = self.standardize_label(self.label or "")
        self.slug = self.make_slug(self.label)

    def clean(self):
        super().clean()
        if not self.label:
            return
        self.standardize()
        if not self.slug:
            raise ValidationError({"label": "O nome precisa ter letras ou números."})
        # O slug não está no formulário, então o validate_unique do ModelForm não o
        # confere; a checagem fica aqui para o erro aparecer no campo "Nome"
        duplicate = Facility.objects.filter(slug=self.slug).exclude(pk=self.pk).first()
        if duplicate:
            raise ValidationError({"label": f"Já existe a estrutura “{duplicate.label}”."})

    def save(self, *args, **kwargs):
        # Também padroniza fora dos formulários (shell, scripts)
        self.standardize()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.label


class State(models.TextChoices):
    """Unidades federativas (UF)."""

    AC = "AC", "Acre"
    AL = "AL", "Alagoas"
    AP = "AP", "Amapá"
    AM = "AM", "Amazonas"
    BA = "BA", "Bahia"
    CE = "CE", "Ceará"
    DF = "DF", "Distrito Federal"
    ES = "ES", "Espírito Santo"
    GO = "GO", "Goiás"
    MA = "MA", "Maranhão"
    MT = "MT", "Mato Grosso"
    MS = "MS", "Mato Grosso do Sul"
    MG = "MG", "Minas Gerais"
    PA = "PA", "Pará"
    PB = "PB", "Paraíba"
    PR = "PR", "Paraná"
    PE = "PE", "Pernambuco"
    PI = "PI", "Piauí"
    RJ = "RJ", "Rio de Janeiro"
    RN = "RN", "Rio Grande do Norte"
    RS = "RS", "Rio Grande do Sul"
    RO = "RO", "Rondônia"
    RR = "RR", "Roraima"
    SC = "SC", "Santa Catarina"
    SP = "SP", "São Paulo"
    SE = "SE", "Sergipe"
    TO = "TO", "Tocantins"


class City(models.Model):
    """Município, identificado pelo código do IBGE (carregado de data/municipios.json)."""

    ibge_code = models.PositiveIntegerField(primary_key=True, verbose_name="Código IBGE")
    name = models.CharField(max_length=64, verbose_name="Nome")
    state = models.CharField(max_length=2, choices=State, verbose_name="UF")

    class Meta:
        verbose_name = "Município"
        verbose_name_plural = "Municípios"
        ordering = ["name"]
        indexes = [models.Index(fields=["state", "name"])]

    def __str__(self):
        return f"{self.name}/{self.state}"


class Estate(models.Model):
    """Modelo do Empreendimento"""

    name = models.CharField(max_length=64, verbose_name="Nome")
    company = models.ForeignKey(
        "Company", on_delete=models.CASCADE, verbose_name="Construtora"
    )

    # Endereço (a UF vem do município)
    cep = models.CharField(
        max_length=9, verbose_name="CEP", help_text="Com ou sem traço (ex: 88015-200)"
    )
    street = models.CharField(max_length=128, verbose_name="Logradouro")
    number = models.CharField(
        max_length=16, verbose_name="Número", help_text="Use “s/n” se não houver"
    )
    complement = models.CharField(
        max_length=64, blank=True, default="", verbose_name="Complemento"
    )
    district = models.CharField(max_length=64, verbose_name="Bairro")
    city = models.ForeignKey(
        City, on_delete=models.PROTECT, related_name="estates", verbose_name="Município"
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal("-90")), MaxValueValidator(Decimal("90"))],
        verbose_name="Latitude",
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal("-180")), MaxValueValidator(Decimal("180"))],
        verbose_name="Longitude",
    )

    cartographic_id = models.CharField(
        max_length=32, verbose_name="Identificação cartográfica", blank=True, null=True
    )
    block = models.PositiveIntegerField(verbose_name="Quadra", blank=True, null=True)
    lot = models.PositiveIntegerField(verbose_name="Lote", blank=True, null=True)
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
        errors = {}

        if self.cep:
            # Guarda só os dígitos, como no CNPJ (ex: "88015-200" vira "88015200")
            self.cep = re.sub(r"\D", "", self.cep)
            if len(self.cep) != 8:
                errors["cep"] = "O CEP deve ter 8 dígitos."

        if (self.latitude is None) != (self.longitude is None):
            errors["longitude" if self.longitude is None else "latitude"] = (
                "Informe latitude e longitude juntas."
            )

        # Datas inválidas já geraram erro próprio em clean_fields()
        if self.sales_start and self.delivery_date and self.delivery_date <= self.sales_start:
            errors["delivery_date"] = "A data da entrega deve ser posterior ao início das vendas."

        if errors:
            raise ValidationError(errors)

    @property
    def cep_display(self):
        """CEP com traço para exibição (ex: '88015-200')."""
        return f"{self.cep[:5]}-{self.cep[5:]}" if len(self.cep) == 8 else self.cep

    @property
    def address_display(self):
        """Endereço em uma linha (ex: 'Rua X, 100, Torre B - Centro, Florianópolis/SC')."""
        parts = [self.street, self.number, self.complement]
        line = ", ".join(p for p in parts if p)
        return f"{line} - {self.district}, {self.city}"

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
    quantity = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)], verbose_name="Quantidade"
    )
    total_area = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Área total (m²)",
    )

    class Meta:
        verbose_name = "Estrutura do Empreendimento"
        verbose_name_plural = "Estruturas do Empreendimento"
        unique_together = ("estate", "facility")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name="estatefacility_quantity_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(total_area__isnull=True) | models.Q(total_area__gte=0),
                name="estatefacility_total_area_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.facility.label} em {self.estate.name}"


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
