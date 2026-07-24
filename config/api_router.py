"""Central DRF router for ViewSets shared across the project.

Register ViewSets here as new domain apps are added, e.g.::

    router.register("unidades", UnidadeViewSet)
"""

from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

app_name = "api"
urlpatterns = router.urls
