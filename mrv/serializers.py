# mrv/serializers.py
from rest_framework import serializers

from .models import MRV


class MRVSerializer(serializers.ModelSerializer):
    class Meta:
        model = MRV
        fields = [
            "id", "project", "tree_count", "average_dbh", "average_height",
            "root_to_shoot_ratio", "soil_organic_carbon",
            "above_ground_biomass", "below_ground_biomass",
            "total_gross_carbon_stock", "risk_level", "issuable_credits",
            "status", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MRVCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MRV
        fields = [
            "tree_count", "average_dbh", "average_height",
            "root_to_shoot_ratio", "soil_organic_carbon",
            "above_ground_biomass", "below_ground_biomass",
            "total_gross_carbon_stock", "risk_level", "issuable_credits",
        ]