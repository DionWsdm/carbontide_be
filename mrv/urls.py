from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MRVViewSet

app_name = "mrv"

router = DefaultRouter()
router.register("mrv", MRVViewSet, basename="mrv")

urlpatterns = [
    path("", include(router.urls)),
]