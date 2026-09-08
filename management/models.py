from pathlib import Path
from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="Telefone"
    )


class Company(models.Model):
    name = models.CharField(max_length=64, verbose_name="Nome")
    contact = models.CharField(max_length=16, default="", verbose_name="Contato")

    class Meta:
        verbose_name = "Construtora"
        verbose_name_plural = "Construtoras"

    def __str__(self):
        return self.name


class Estate(models.Model):
    name = models.CharField(max_length=64, verbose_name="Nome")
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, verbose_name="Construtora"
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
    elevators = models.PositiveIntegerField(default=0, verbose_name="Elevadores")
    swimming_pools = models.PositiveIntegerField(default=0, verbose_name="Piscinas")
    restaurants_bars = models.PositiveIntegerField(
        default=0, verbose_name="Bares e restaurantes"
    )
    academies = models.PositiveIntegerField(default=0, verbose_name="Academias")
    playgrounds = models.PositiveIntegerField(
        default=0, verbose_name="Ambientes para Pets / Playgrounds"
    )
    party_rooms = models.PositiveIntegerField(
        default=0, verbose_name="Salões de festas"
    )
    saunas = models.PositiveIntegerField(default=0, verbose_name="Saunas")
    mini_markets = models.PositiveIntegerField(default=0, verbose_name="Mini-mercados")

    class Meta:
        verbose_name = "Residencial"
        verbose_name_plural = "Residenciais"

    def __str__(self):
        return self.name


class PaymentTerms(models.Model):
    estate = models.ForeignKey(
        Estate, on_delete=models.CASCADE, verbose_name="Residencial"
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
