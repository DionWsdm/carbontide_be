import uuid

from django.db import models

from projects.models import Project


class MRV(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CALCULATED = "calculated", "Calculated"
        VERIFIED = "verified", "Verified"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="mrv_records",
        db_column="project_id",
    )

    tree_count = models.IntegerField()
    average_dbh = models.DecimalField(max_digits=10, decimal_places=2)
    average_height = models.DecimalField(max_digits=10, decimal_places=2)
    root_to_shoot_ratio = models.DecimalField(max_digits=10, decimal_places=4)
    soil_organic_carbon = models.DecimalField(max_digits=15, decimal_places=2)

    above_ground_biomass = models.DecimalField(max_digits=15, decimal_places=2)
    below_ground_biomass = models.DecimalField(max_digits=15, decimal_places=2)
    total_gross_carbon_stock = models.DecimalField(max_digits=15, decimal_places=2)

    risk_level = models.CharField(max_length=10, choices=RiskLevel.choices)
    issuable_credits = models.DecimalField(max_digits=15, decimal_places=2)

    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.DRAFT
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mrv"
        verbose_name = "MRV"
        verbose_name_plural = "MRV Records"
        ordering = ["-created_at"]

    def __str__(self):
        return f"MRV for {self.project.project_name} ({self.status})"