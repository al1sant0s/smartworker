from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import AbstractUser

from pathlib import Path
from decimal import Decimal


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)


class Company(models.Model):
    name = models.CharField(max_length=64)
    contact = models.CharField(max_length=16)


class Estate(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    address = models.TextField()
    cartographic_id = models.CharField(max_length=32)
    block = models.PositiveIntegerField()
    lot = models.PositiveIntegerField()
    sea_distance = models.PositiveIntegerField("Distance in meters")
    sales_start = models.DateField(default=0)
    delivery_date = models.DateField(default=0)
    elevators = models.PositiveIntegerField(default=0)
    swimming_pools = models.PositiveIntegerField(default=0)
    restaurants_bars = models.PositiveIntegerField(default=0)
    academies = models.PositiveIntegerField(default=0)
    playgrounds = models.PositiveIntegerField("For children and for pets", default=0)
    party_rooms = models.PositiveIntegerField(default=0)
    saunas = models.PositiveIntegerField(default=0)
    mini_marktes = models.PositiveIntegerField(default=0)


class PaymentTerms(models.Model):
    estate = models.ForeignKey(Estate, on_delete=models.CASCADE)
    down_payment = models.DecimalField(
        "Sinal",
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    key_payment = models.DecimalField(
        "Chaves ou habite-se",
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    monthly_payment = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    monthly_installments = models.PositiveIntegerField()
    balloon_payment = models.DecimalField(
        "Parcelas intercaladas",
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    balloon_installments = models.PositiveIntegerField()
