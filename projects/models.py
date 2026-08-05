import uuid

from django.core.exceptions import ValidationError
from django.db import models
from decimal import Decimal


class Project(models.Model):
    class ProjectType(models.TextChoices):
        FORESTRY = "forestry", "Forestry & Land Use"
        RENEWABLE_ENERGY = "renewable_energy", "Renewable Energy"
        AGRICULTURE = "agriculture", "Agriculture"
        WASTE_MANAGEMENT = "waste_management", "Waste Management"
        BLUE_CARBON = "blue_carbon", "Blue Carbon"
        ENERGY_EFFICIENCY = "energy_efficiency", "Energy Efficiency"
        OTHER = "other", "Other"

    class Registry(models.TextChoices):
        VERRA = "verra", "Verra (VCS)"
        GOLD_STANDARD = "gold_standard", "Gold Standard"
        ACR = "acr", "American Carbon Registry (ACR)"
        CAR = "car", "Climate Action Reserve (CAR)"
        PLAN_VIVO = "plan_vivo", "Plan Vivo"
        OTHER = "other", "Other"

    class VerificationStatus(models.TextChoices):
        UNVERIFIED = "unverified", "Unverified"
        UNDER_REVIEW = "under_review", "Under Review"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="projects",
    )
    project_name = models.CharField(max_length=255)
    project_type = models.CharField(max_length=50, choices=ProjectType.choices)
    description = models.TextField(blank=True)
    country = models.CharField(max_length=100)
    location = models.CharField(max_length=255)
    methodology = models.CharField(max_length=255)
    registry = models.CharField(
        max_length=50, choices=Registry.choices, blank=True
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED,
    )

    # --- Data setup proyek (step "Setup" di wizard create-project) ---
    area_hectares = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Luas area proyek (hektar).",
    )

    area_geojson = models.JSONField(
        null=True, blank=True,
        help_text="Polygon/MultiPolygon lokasi proyek dalam format GeoJSON, dipakai untuk query GFW API.",
    )

    deforestation_rate = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Tingkat deforestasi historis baseline (%).",
    )

    deforestation_checked_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Kapan terakhir kali data deforestasi diambil dari GFW API.",
    )

    expected_credits = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    thumbnail_url = models.TextField(blank=True, null=True)

    # --- Carbon Credit Identity & Traceability (ditampilkan di detail proyek) ---
    vintage_year = models.PositiveIntegerField(null=True, blank=True)
    verified_by = models.CharField(max_length=255, blank=True, null=True)
    serial_range = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "projects"
        ordering = ["-created_at"]

    def __str__(self):
        return self.project_name

class ProjectImpact(models.Model):
    """Co-benefits / dampak nyata proyek (section 'Dampak Nyata')."""

    class ImpactType(models.TextChoices):
        TREES = "trees", "Pohon Ditanam"
        SPECIES = "species", "Spesies Dilindungi"
        PEOPLE = "people", "Masyarakat Terbantu"
        OTHER = "other", "Lainnya"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="impacts",
        db_column="project_id",
    )
    impact_type = models.CharField(max_length=20, choices=ImpactType.choices)
    icon = models.CharField(max_length=10, blank=True, help_text="Emoji, misal 🌲")
    label = models.CharField(
        max_length=100, help_text="Teks tampil, misal '250.000+ Ditanam'"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "project_impacts"
        ordering = ["order"]

    def __str__(self):
        return f"{self.project.project_name} - {self.label}"


class ProjectFAQ(models.Model):
    """FAQ & Risk Disclosure di halaman detail proyek."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="faqs",
        db_column="project_id",
    )
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "project_faqs"
        ordering = ["order"]

    def __str__(self):
        return self.question

class ProjectDocument(models.Model):
    class DocumentType(models.TextChoices):
        PDD = "pdd", "Project Design Document (PDD)"
        VALIDATION_REPORT = "validation_report", "Validation Report"
        MONITORING_REPORT = "monitoring_report", "Monitoring Report"
        VERIFICATION_REPORT = "verification_report", "Verification Report"
        LEGAL_DOCUMENT = "legal_document", "Legal Document"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="documents",
        db_column="project_id",
    )
    document_type = models.CharField(max_length=50, choices=DocumentType.choices)
    file_url = models.TextField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "project_documents"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.project.project_name} - {self.get_document_type_display()}"


class MarketplaceListing(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"

    class Status(models.TextChoices):
        PUBLISHED = "published", "Published"
        UNPUBLISHED = "unpublished", "Unpublished"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="marketplace_listing",
        db_column="project_id",
    )
    price_per_credit = models.DecimalField(max_digits=15, decimal_places=2)
    platform_fee_percentage = models.DecimalField(
        max_digits=5, decimal_places=4, default=Decimal("0.05"),
        help_text="Contoh: 0.05 = 5%",
    )
    visibility = models.CharField(
        max_length=10, choices=Visibility.choices, default=Visibility.PRIVATE
    )
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.UNPUBLISHED
    )
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "marketplace_listings"
        ordering = ["-published_at"]

    def __str__(self):
        return f"Listing for {self.project.project_name}"


class CreditInventory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.OneToOneField(
        MarketplaceListing,
        on_delete=models.CASCADE,
        related_name="credit_inventory",
        db_column="listing_id",
    )
    total_issued = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    available = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    sold = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    reserved = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    retired = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    buffer = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        db_table = "credit_inventory"
        verbose_name_plural = "Credit Inventories"

    def clean(self):
        total_allocated = (
            self.available + self.sold + self.reserved + self.retired + self.buffer
        )
        if total_allocated != self.total_issued:
            raise ValidationError(
                "Jumlah available + sold + reserved + retired + buffer "
                "harus sama dengan total_issued."
            )

    def __str__(self):
        return f"Inventory for {self.listing}"