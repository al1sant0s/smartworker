import re
from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core import validators
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
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

    def __str__(self):
        return f"{self.name} (CNPJ: {self.cnpj})"


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

    def save(self, *args, **kwargs):
        # 1. Limpa espaços nas extremidades e converte para minúsculo
        cleaned = self.name.strip().lower()
        # 2. Converte espaços e hífens repetidos em um único underscore
        self.name = re.sub(r"[\s-]+", "_", cleaned)
        super().save(*args, **kwargs)

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

    def __str__(self):
        return self.name


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
        verbose_name="Sinal",
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    key_payment = models.DecimalField(
        verbose_name="Chaves ou habite-se",
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
        verbose_name="Mensais (parcelas)"
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
        verbose_name="Intercaladas (parcelas)"
    )

    class Meta:
        verbose_name = "Condição de pagamento"
        verbose_name_plural = "Condições de pagamento"
