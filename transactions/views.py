from decimal import Decimal

from django.db.models import Sum
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Transaction
from .serializers import (
    PortfolioSummarySerializer,
    PurchaseSerializer,
    TransactionListSerializer,
    TransactionSerializer,
)

# Asumsi konversi dampak — sesuaikan dengan metodologi resmi jika ada.
TREES_PER_TON = Decimal("5")
CARS_PER_TON = Decimal("0.22")


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET  /api/transactions/           -> daftar transaksi milik buyer (Portfolio)
    GET  /api/transactions/{id}/      -> detail transaksi
    GET  /api/transactions/summary/   -> kartu ringkasan Portfolio
    POST /api/transactions/purchase/  -> beli & pensiunkan kredit (satu langkah)
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(buyer=self.request.user).select_related(
            "listing__project"
        )

    def get_serializer_class(self):
        if self.action == "list":
            return TransactionListSerializer
        return TransactionSerializer

    @action(detail=False, methods=["post"], url_path="purchase")
    def purchase(self, request):
        serializer = PurchaseSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        transaction = serializer.save()
        return Response(
            TransactionSerializer(transaction).data, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        completed = self.get_queryset().filter(status=Transaction.Status.COMPLETED)

        total_offset_tons = completed.aggregate(total=Sum("quantity"))["total"] or Decimal("0")
        total_contribution = completed.aggregate(total=Sum("total_price"))["total"] or Decimal("0")

        data = {
            "total_offset_tons": total_offset_tons,
            "equivalent_trees": int(total_offset_tons * TREES_PER_TON),
            "equivalent_cars": int(total_offset_tons * CARS_PER_TON),
            "total_contribution": total_contribution,
        }
        return Response(PortfolioSummarySerializer(data).data)