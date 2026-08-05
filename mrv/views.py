# mrv/views.py
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from .models import MRV
from .serializers import MRVSerializer


class MRVViewSet(viewsets.ModelViewSet):
    serializer_class = MRVSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = MRV.objects.filter(project__organization=self.request.user)
        project_id = self.request.query_params.get("project")
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        project = serializer.validated_data["project"]
        if project.organization_id != self.request.user.id:
            raise PermissionDenied("Kamu tidak punya akses ke proyek ini.")
        serializer.save()