from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MarketplaceViewSet, ProjectFullCreateView, ProjectViewSet

app_name = "projects"

router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="project")
router.register("marketplace", MarketplaceViewSet, basename="marketplace")

urlpatterns = [
    path("projects/create-full/", ProjectFullCreateView.as_view(), name="project-create-full"),
    path("", include(router.urls)),
]