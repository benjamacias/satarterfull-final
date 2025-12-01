from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from billing.views import FacturacionViewSet, TarifaProductoViewSet

router = DefaultRouter()
router.register("api/productos", TarifaProductoViewSet, basename="productos")
router.register("api", FacturacionViewSet, basename="api")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(router.urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
