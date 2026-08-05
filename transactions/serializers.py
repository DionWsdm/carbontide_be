from decimal import Decimal

from rest_framework import serializers

from projects.models import MarketplaceListing

from .models import Transaction

from django.utils import timezone

class PurchaseSerializer(serializers.Serializer):
    """
    POST /api/transactions/purchase/
    Satu langkah: validasi, potong kredit, buat transaksi COMPLETED,
    terbitkan sertifikat pensiun — semua sekaligus.
    """

    listing_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal("0.01"))
    payment_method = serializers.ChoiceField(choices=Transaction.PaymentMethod.choices)

    def validate(self, attrs):
        try:
            listing = MarketplaceListing.objects.select_related(
                "credit_inventory", "project"
            ).get(
                id=attrs["listing_id"],
                status=MarketplaceListing.Status.PUBLISHED,
            )
        except MarketplaceListing.DoesNotExist:
            raise serializers.ValidationError("Listing tidak ditemukan atau belum dipublikasikan.")

        inventory = getattr(listing, "credit_inventory", None)
        if inventory is None or inventory.available < attrs["quantity"]:
            raise serializers.ValidationError(
                "Kredit yang tersedia tidak mencukupi untuk jumlah yang diminta."
            )

        attrs["listing"] = listing
        attrs["inventory"] = inventory
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        listing = validated_data["listing"]
        inventory = validated_data["inventory"]
        quantity = validated_data["quantity"]

        price_per_credit = listing.price_per_credit
        subtotal = quantity * price_per_credit
        platform_fee = subtotal * listing.platform_fee_percentage
        total_price = subtotal + platform_fee

        transaction = Transaction.objects.create(
            listing=listing,
            buyer=request.user,
            quantity=quantity,
            price_per_credit=price_per_credit,
            platform_fee=platform_fee,
            total_price=total_price,
            payment_method=validated_data["payment_method"],
            status=Transaction.Status.COMPLETED,
        )

        # Langsung pindah dari available -> retired (dipensiunkan)
        inventory.available -= quantity
        inventory.retired += quantity
        inventory.save()

        transaction.retired_at = timezone_now()
        transaction.certificate_number = f"CERT-{transaction.id.hex[:8].upper()}"
        transaction.certificate_url = f"/certificates/{transaction.id}.pdf"
        transaction.save()

        return transaction


def timezone_now():
    from django.utils import timezone
    return timezone.now()


class TransactionSerializer(serializers.ModelSerializer):
    """Detail transaksi -> 'Ringkasan Pesanan' & halaman sukses pembayaran."""

    project_name = serializers.CharField(source="listing.project.project_name", read_only=True)
    project_location = serializers.CharField(source="listing.project.location", read_only=True)
    project_thumbnail = serializers.CharField(source="listing.project.thumbnail_url", read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            "id", "invoice_number", "project_name", "project_location",
            "project_thumbnail", "quantity", "price_per_credit", "subtotal",
            "platform_fee", "total_price", "payment_method", "status",
            "certificate_number", "certificate_url", "retired_at", "created_at",
        ]
        read_only_fields = fields

    def get_subtotal(self, obj):
        return obj.quantity * obj.price_per_credit


class TransactionListSerializer(serializers.ModelSerializer):
    """Untuk tabel 'Daftar Sertifikat & Kredit Anda' di Portfolio."""

    project_name = serializers.CharField(source="listing.project.project_name", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id", "invoice_number", "project_name", "quantity",
            "status", "certificate_url", "created_at",
        ]
        read_only_fields = fields


class PortfolioSummarySerializer(serializers.Serializer):
    total_offset_tons = serializers.DecimalField(max_digits=18, decimal_places=2)
    equivalent_trees = serializers.IntegerField()
    equivalent_cars = serializers.IntegerField()
    total_contribution = serializers.DecimalField(max_digits=18, decimal_places=2)