import math
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from mrv.models import MRV
from mrv.serializers import MRVCreateSerializer, MRVSerializer
from transactions.models import Transaction

from .models import CreditInventory, MarketplaceListing, Project, ProjectFAQ, ProjectImpact , ProjectDocument


class ProjectDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDocument
        fields = ["id", "document_type", "file_url", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class CreditInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditInventory
        fields = [
            "id", "total_issued", "available", "sold",
            "reserved", "retired", "buffer",
        ]
        read_only_fields = fields


class MarketplaceListingSerializer(serializers.ModelSerializer):
    credit_inventory = CreditInventorySerializer(read_only=True)

    class Meta:
        model = MarketplaceListing
        fields = [
            "id", "price_per_credit", "visibility", "status",
            "published_at", "credit_inventory",
        ]
        read_only_fields = ["id", "published_at", "credit_inventory"]


class MarketplaceListingUpdateSerializer(serializers.ModelSerializer):
    """Panel 'Pengaturan Listing' -> harga, visibilitas, publish/unpublish."""

    class Meta:
        model = MarketplaceListing
        fields = ["price_per_credit", "visibility", "status"]

    def update(self, instance, validated_data):
        new_status = validated_data.get("status", instance.status)
        if (
            new_status == MarketplaceListing.Status.PUBLISHED
            and instance.status != new_status
        ):
            validated_data["published_at"] = timezone.now()
        return super().update(instance, validated_data)


class TransactionAuditSerializer(serializers.ModelSerializer):
    """Untuk section 'Audit Trail (Sales Log)'."""

    buyer_name = serializers.CharField(source="buyer.full_name", read_only=True)

    class Meta:
        model = Transaction
        fields = ["id", "buyer_name", "quantity", "total_price", "status", "created_at"]


class ProjectImpactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectImpact
        fields = ["id", "impact_type", "icon", "label", "order"]


class ProjectFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectFAQ
        fields = ["id", "question", "answer", "order"]


class MarketplaceCatalogueSerializer(serializers.ModelSerializer):
    """List proyek di halaman marketplace (buyer)."""

    price_per_credit = serializers.DecimalField(
        source="marketplace_listing.price_per_credit",
        max_digits=15, decimal_places=2, read_only=True,
    )
    available_tons = serializers.SerializerMethodField()
    trees_label = serializers.SerializerMethodField()
    people_label = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id", "project_name", "project_type", "location", "registry",
            "thumbnail_url", "price_per_credit", "available_tons",
            "trees_label", "people_label",
        ]

    def _get_impact(self, obj, impact_type):
        return next((i for i in obj.impacts.all() if i.impact_type == impact_type), None)

    def get_available_tons(self, obj):
        listing = getattr(obj, "marketplace_listing", None)
        inv = getattr(listing, "credit_inventory", None) if listing else None
        return inv.available if inv else None

    def get_trees_label(self, obj):
        impact = self._get_impact(obj, ProjectImpact.ImpactType.TREES)
        return impact.label if impact else None

    def get_people_label(self, obj):
        impact = self._get_impact(obj, ProjectImpact.ImpactType.PEOPLE)
        return impact.label if impact else None


class MarketplaceDetailSerializer(serializers.ModelSerializer):
    """Detail proyek di halaman buyer -> dashboard-pembeli/[project]."""

    developer_name = serializers.CharField(source="organization.full_name", read_only=True)
    price_per_credit = serializers.DecimalField(
        source="marketplace_listing.price_per_credit",
        max_digits=15, decimal_places=2, read_only=True,
    )
    platform_fee_percentage = serializers.DecimalField(
        source="marketplace_listing.platform_fee_percentage",
        max_digits=5, decimal_places=4, read_only=True,
    )
    available_tons = serializers.SerializerMethodField()
    impacts = ProjectImpactSerializer(many=True, read_only=True)
    faqs = ProjectFAQSerializer(many=True, read_only=True)
    documents = ProjectDocumentSerializer(many=True, read_only=True)
    mrv_confidence = serializers.SerializerMethodField()
    mrv_baseline_label = serializers.SerializerMethodField()
    listing_id = serializers.CharField(source="marketplace_listing.id", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "project_name", "project_type", "location", "country",
            "description", "thumbnail_url", "developer_name",
            "registry", "vintage_year", "methodology", "verified_by",
            "serial_range", "verification_status",
            "price_per_credit", "platform_fee_percentage", "available_tons",
            "area_hectares", "mrv_baseline_label", "mrv_confidence",
            "impacts", "faqs", "documents", "listing_id"
        ]
        read_only_fields = fields

    def get_available_tons(self, obj):
        listing = getattr(obj, "marketplace_listing", None)
        inv = getattr(listing, "credit_inventory", None) if listing else None
        return inv.available if inv else None

    def get_mrv_confidence(self, obj):
        latest_mrv = obj.mrv_records.order_by("-created_at").first()
        if not latest_mrv:
            return None
        mapping = {"low": "Tinggi", "medium": "Sedang", "high": "Rendah"}
        return mapping.get(latest_mrv.risk_level)

    def get_mrv_baseline_label(self, obj):
        return "Hist. Deforestasi" if obj.deforestation_rate is not None else None

class ProjectListSerializer(serializers.ModelSerializer):
    """Untuk daftar proyek di dashboard-penjual."""

    listing_status = serializers.SerializerMethodField()
    price_per_credit = serializers.SerializerMethodField()
    available_credits = serializers.SerializerMethodField()
    total_issued_credits = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id", "project_name", "project_type", "methodology",
            "thumbnail_url", "status", "listing_status",
            "price_per_credit", "available_credits", "total_issued_credits",
        ]

    def _get_listing(self, obj):
        return getattr(obj, "marketplace_listing", None)

    def get_listing_status(self, obj):
        listing = self._get_listing(obj)
        return listing.status if listing else None

    def get_price_per_credit(self, obj):
        listing = self._get_listing(obj)
        return listing.price_per_credit if listing else None

    def get_available_credits(self, obj):
        listing = self._get_listing(obj)
        inv = getattr(listing, "credit_inventory", None) if listing else None
        return inv.available if inv else None

    def get_total_issued_credits(self, obj):
        listing = self._get_listing(obj)
        inv = getattr(listing, "credit_inventory", None) if listing else None
        return inv.total_issued if inv else None


class ProjectDetailSerializer(serializers.ModelSerializer):
    """Untuk halaman dashboard-penjual/[project]."""

    documents = ProjectDocumentSerializer(many=True, read_only=True)
    listing = serializers.SerializerMethodField()
    audit_trail = serializers.SerializerMethodField()
    mrv_records = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id", "project_name", "project_type", "description",
            "country", "location", "methodology", "registry",
            "verification_status", "area_hectares", "deforestation_rate",
            "area_geojson", "deforestation_checked_at",
            "expected_credits", "status", "thumbnail_url",
            "vintage_year", "verified_by", "serial_range",
            "created_at", "updated_at",
            "documents", "listing", "audit_trail", "mrv_records",
        ]
        read_only_fields = fields

    def get_listing(self, obj):
        listing = getattr(obj, "marketplace_listing", None)
        return MarketplaceListingSerializer(listing).data if listing else None

    def get_audit_trail(self, obj):
        listing = getattr(obj, "marketplace_listing", None)
        if not listing:
            return []
        qs = listing.transactions.order_by("-created_at")
        return TransactionAuditSerializer(qs, many=True).data

    def get_mrv_records(self, obj):
        qs = obj.mrv_records.order_by("-created_at")
        return MRVSerializer(qs, many=True).data


class ProjectCreateSerializer(serializers.ModelSerializer):
    """Step 'Setup Proyek' di wizard create-project."""

    class Meta:
        model = Project
        fields = [
            "id", "project_name", "project_type", "description",
            "country", "location", "methodology", "registry",
            "area_hectares", "deforestation_rate", "area_geojson",
            "expected_credits", "thumbnail_url",
        ]
        read_only_fields = ["id"]


class ProjectWithMRVCreateSerializer(serializers.Serializer):
    """
    Submit gabungan seluruh wizard (Setup + Data + Risk) sekaligus,
    dipanggil sekali di step terakhir (Report -> Submit).
    """

    project = ProjectCreateSerializer()
    mrv = MRVCreateSerializer()

    def create(self, validated_data):
        request = self.context["request"]
        project_data = validated_data["project"]
        mrv_data = validated_data["mrv"]

        with transaction.atomic():
            project = Project.objects.create(
                organization=request.user,
                status=Project.Status.PENDING,
                **project_data,
            )
            mrv = MRV.objects.create(project=project, **mrv_data)

            listing = MarketplaceListing.objects.create(
                project=project,
                price_per_credit=0,   
            )

            available = self.calcIssuableCredits(mrv)

            CreditInventory.objects.create(
                listing=listing,
                total_issued=available,
                available=available,
                sold=0,
                reserved=0,
                retired=0,
                buffer=0,
            )

        return {"project": project, "mrv": mrv}

    def to_representation(self, instance):
        return {
            "project": ProjectDetailSerializer(instance["project"]).data,
        }

    def calcBiomass(self, jumlahPohon: int, avgDbh, avgTinggi):
        avgDbh = float(avgDbh)
        avgTinggi = float(avgTinggi)

        return jumlahPohon * 0.0673 * math.pow((0.8 * math.pow(avgDbh, 2) * avgTinggi), 0.976)

    def calcGrossCarbon(self, biomass, rtsRatio, carbon):
        return float(biomass) + float(rtsRatio) + float(carbon)

    def calcIssuableCredits(self, mrv: MRV):
        biomass = self.calcBiomass(mrv.tree_count, mrv.average_dbh, mrv.average_height)
        grossCarbon = self.calcGrossCarbon(biomass, mrv.root_to_shoot_ratio, mrv.soil_organic_carbon)
        if (mrv.risk_level == "low"):
            risk = 0.1
        elif (mrv.risk_level == "medium"):
            risk = 0.15
        else:
            risk = 0.2
        return (1-risk/100) * grossCarbon


class DashboardSummarySerializer(serializers.Serializer):
    """3 kartu ringkasan di atas dashboard-penjual."""

    total_revenue = serializers.DecimalField(max_digits=18, decimal_places=2)
    total_credits_sold = serializers.DecimalField(max_digits=18, decimal_places=2)
    total_projects = serializers.IntegerField()



