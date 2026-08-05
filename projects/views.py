from django.db.models import Sum
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from transactions.models import Transaction

from .models import MarketplaceListing, Project
from .serializers import (
    DashboardSummarySerializer,
    MarketplaceListingUpdateSerializer,
    ProjectCreateSerializer,
    ProjectDetailSerializer,
    ProjectListSerializer,
    ProjectWithMRVCreateSerializer,
)

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from .models import Project, MarketplaceListing
from .serializers import MarketplaceCatalogueSerializer, MarketplaceDetailSerializer

from .services.gfw import GFWServiceError, get_tree_cover_loss


class ProjectViewSet(viewsets.ModelViewSet):
    """
    GET    /api/projects/                 -> list (dashboard-penjual)
    GET    /api/projects/{id}/             -> detail proyek
    POST   /api/projects/                 -> buat proyek (tanpa MRV)
    PATCH  /api/projects/{id}/            -> update proyek
    DELETE /api/projects/{id}/
    GET    /api/projects/dashboard-summary/
    PATCH  /api/projects/{id}/listing/
    POST   /api/projects/{id}/listing/publish/
    POST   /api/projects/{id}/listing/unpublish/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(organization=self.request.user).order_by(
            "-created_at"
        )

    def get_serializer_class(self):
        if self.action == "list":
            return ProjectListSerializer
        if self.action == "retrieve":
            return ProjectDetailSerializer
        return ProjectCreateSerializer

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user, status=Project.Status.DRAFT)

    @action(detail=False, methods=["get"], url_path="dashboard-summary")
    def dashboard_summary(self, request):
        projects = self.get_queryset()
        total_projects = projects.count()

        completed_tx = Transaction.objects.filter(
            listing__project__in=projects,
            status=Transaction.Status.COMPLETED,
        )
        total_revenue = completed_tx.aggregate(total=Sum("total_price"))["total"] or 0
        total_credits_sold = (
            completed_tx.aggregate(total=Sum("quantity"))["total"] or 0
        )

        data = {
            "total_revenue": total_revenue,
            "total_credits_sold": total_credits_sold,
            "total_projects": total_projects,
        }
        return Response(DashboardSummarySerializer(data).data)

    def _get_or_create_listing(self, project, default_price=0):
        try:
            return project.marketplace_listing
        except MarketplaceListing.DoesNotExist:
            return MarketplaceListing.objects.create(
                project=project, price_per_credit=default_price
            )

    @action(detail=True, methods=["patch"], url_path="listing")
    def update_listing(self, request, pk=None):
        project = self.get_object()
        listing = self._get_or_create_listing(
            project, default_price=request.data.get("price_per_credit", 0)
        )

        serializer = MarketplaceListingUpdateSerializer(
            listing, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MarketplaceListingUpdateSerializer(listing).data)

    @action(detail=True, methods=["post"], url_path="listing/publish")
    def publish_listing(self, request, pk=None):
        project = self.get_object()
        try:
            listing = project.marketplace_listing
        except MarketplaceListing.DoesNotExist:
            return Response(
                {"error": "Listing belum dibuat untuk proyek ini."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        listing.status = MarketplaceListing.Status.PUBLISHED
        listing.visibility = MarketplaceListing.Visibility.PUBLIC
        listing.published_at = timezone.now()
        listing.save()
        return Response(MarketplaceListingUpdateSerializer(listing).data)

    @action(detail=True, methods=["post"], url_path="listing/unpublish")
    def unpublish_listing(self, request, pk=None):
        project = self.get_object()
        try:
            listing = project.marketplace_listing
        except MarketplaceListing.DoesNotExist:
            return Response(
                {"error": "Listing belum dibuat untuk proyek ini."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        listing.status = MarketplaceListing.Status.UNPUBLISHED
        listing.save()
        return Response(MarketplaceListingUpdateSerializer(listing).data)

    @action(detail=True, methods=["post"], url_path="listing/unpublish")
    def unpublish_listing(self, request, pk=None):
        project = self.get_object()
        try:
            listing = project.marketplace_listing
        except MarketplaceListing.DoesNotExist:
            return Response(
                {"error": "Listing belum dibuat untuk proyek ini."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        listing.status = MarketplaceListing.Status.UNPUBLISHED
        listing.save()
        return Response(MarketplaceListingUpdateSerializer(listing).data)

    @action(detail=True, methods=["post"], url_path="check-deforestation")   # ⬅️ BARU
    def check_deforestation(self, request, pk=None):
        """
        POST /api/projects/{id}/check-deforestation/
        Body opsional: {"year": 2024}

        Ambil data tutupan hutan hilang dari Global Forest Watch API
        untuk area proyek ini, lalu simpan ke field deforestation_rate.
        """
        project = self.get_object()

        if not project.area_geojson:
            return Response(
                {"error": "Proyek ini belum punya data lokasi (area_geojson)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        year = request.data.get("year", 2024)

        try:
            loss_ha = get_tree_cover_loss(project.area_geojson, year=year)
        except GFWServiceError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if project.area_hectares and project.area_hectares > 0:
            rate_percentage = (loss_ha / float(project.area_hectares)) * 100
        else:
            rate_percentage = 0

        project.deforestation_rate = round(rate_percentage, 2)
        project.deforestation_checked_at = timezone.now()
        project.save(update_fields=["deforestation_rate", "deforestation_checked_at"])

        return Response(
            {
                "deforestation_rate": project.deforestation_rate,
                "tree_cover_loss_ha": loss_ha,
                "checked_at": project.deforestation_checked_at,
            }
        )



class MarketplaceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/marketplace/                 -> katalog proyek untuk buyer
        ?project_type=blue_carbon&registry=verra&search=kelabat
    GET /api/marketplace/{id}/            -> detail proyek untuk buyer
    """

    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["project_type", "registry"]
    search_fields = ["project_name", "location", "country"]

    def get_queryset(self):
        return Project.objects.filter(
            marketplace_listing__status=MarketplaceListing.Status.PUBLISHED,
            marketplace_listing__visibility=MarketplaceListing.Visibility.PUBLIC,
        ).select_related("marketplace_listing__credit_inventory", "organization")

    def get_serializer_class(self):
        if self.action == "list":
            return MarketplaceCatalogueSerializer
        return MarketplaceDetailSerializer


class ProjectFullCreateView(generics.CreateAPIView):
    """
    Endpoint gabungan untuk wizard create-project (Setup + Data + Risk),
    dipanggil sekali saat submit terakhir di halaman Report.
    """

    serializer_class = ProjectWithMRVCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx