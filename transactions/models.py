import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone

from accounts.models import User
from projects.models import MarketplaceListing


class Transaction(models.Model):
    class Status(models.TextChoices):
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class PaymentMethod(models.TextChoices):
        CARD = "card", "Kartu Kredit / Debit"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer / Invoice ESG"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        MarketplaceListing,
        on_delete=models.CASCADE,
        related_name="transactions",
        db_column="listing_id",
    )
    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="purchases",
        db_column="buyer_id",
    )
    invoice_number = models.CharField(max_length=30, unique=True, blank=True)

    quantity = models.DecimalField(max_digits=15, decimal_places=2)
    price_per_credit = models.DecimalField(
        max_digits=15, decimal_places=2,
        help_text="Snapshot harga per kredit saat transaksi dibuat.",
    )
    platform_fee = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=15, decimal_places=2)

    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices,
        default=PaymentMethod.CARD,
    )
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.COMPLETED
    )

    certificate_number = models.CharField(max_length=50, blank=True, null=True)
    certificate_url = models.TextField(blank=True, null=True)
    retired_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transactions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.invoice_number} - {self.buyer} - {self.quantity} credits ({self.status})"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            count = Transaction.objects.count() + 1
            self.invoice_number = f"INV-{count:04d}"
        super().save(*args, **kwargs)