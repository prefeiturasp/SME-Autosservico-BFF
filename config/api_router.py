"""Router central do DRF para ViewSets compartilhados entre os apps.

Registre ViewSets aqui conforme novos apps de domínio forem adicionados,
por exemplo::

    router.register("unidades", UnidadeViewSet)
"""

from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

app_name = "api"
urlpatterns = router.urls
