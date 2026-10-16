"""Fábrica da aplicação Celery para o SME Autosservico BFF.

O broker/backend (KeyDB) e demais opções do Celery são lidos de
``config.settings`` (variáveis prefixadas com ``CELERY_``), conforme o
papel de "BFF_BROKER" descrito na arquitetura C3 deste serviço.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("sme_autosservico_bff")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
