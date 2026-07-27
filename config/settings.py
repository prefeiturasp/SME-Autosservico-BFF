"""Configurações do projeto SME Autosservico BFF.

Arquivo único, lendo todos os valores variáveis do ambiente, conforme o
padrão SME para aplicações Python + Django. Este serviço é um BFF
estritamente *stateless*, focado em orquestração e agregação: não mapeia
tabelas SQL nem possui migrations locais (ver arquitetura C3).
"""

import sys
from pathlib import Path
from typing import Any

import environ

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
APPS_DIR = BASE_DIR / "apps"

env = environ.Env()

# Lê o arquivo .env automaticamente quando ele existir (silenciosamente
# ignorado se ausente — por exemplo, em produção, onde as variáveis vêm
# diretamente do ambiente do container).
env.read_env(str(BASE_DIR / ".env"))

DEBUG = env.bool("DJANGO_DEBUG", default=False)

# Detecta execução da suíte de testes para habilitar defaults seguros
# (SECRET_KEY, hosts) independente de DEBUG/.env.
RUNNING_TESTS = "pytest" in sys.modules or "test" in sys.argv

SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-change-me" if DEBUG or RUNNING_TESTS else None,
)
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=(
        ["localhost", "127.0.0.1", "0.0.0.0"]  # noqa: S104
        if DEBUG or RUNNING_TESTS
        else []
    ),
)

TIME_ZONE = "America/Sao_Paulo"
LANGUAGE_CODE = "pt-br"
USE_I18N = True
USE_TZ = True

# Sem banco de dados relacional: o BFF não define DATABASES (Django usa o
# default global {}) — não há models, migrations nem ORM neste serviço.

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DJANGO_APPS = [
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
]
LOCAL_APPS = [
    "apps.core",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

if DEBUG:
    INSTALLED_APPS = ["whitenoise.runserver_nostatic", *INSTALLED_APPS]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        # APP_DIRS=True é necessário para o template HTML embutido do
        # SpectacularSwaggerView (drf-spectacular).
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
            ],
        },
    },
]

STATIC_ROOT = str(BASE_DIR / "staticfiles")
STATIC_URL = "/static/"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Autenticação por API Key (padrão SME para microsserviços) — ver
# apps/core/authentication.py.
API_KEY = env("API_KEY", default="")
API_KEY_HEADER = env("API_KEY_HEADER", default="X-Api-Key")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.core.authentication.ApiKeyAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Sem django.contrib.auth (sem banco de dados): quando nenhuma
    # autenticação é resolvida, o DRF deixaria request.user como uma
    # instância de AnonymousUser por padrão, o que importaria
    # django.contrib.contenttypes (não instalado). None evita isso.
    "UNAUTHENTICATED_USER": None,
}

CORS_URLS_REGEX = r"^/api/.*$"
CORS_ALLOWED_ORIGINS = env.list(
    "DJANGO_CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"]
)

SPECTACULAR_SETTINGS: dict[str, Any] = {
    "TITLE": "SME Autosservico BFF API",
    "DESCRIPTION": (
        "Documentação dos endpoints da API do SME Autosservico BFF: "
        "camada de orquestração e roteamento entre o frontend e as "
        "demais fontes de dados do autosserviço (backend, Azure DevOps, "
        "Zabbix, Grafana)."
    ),
    "VERSION": "1.0.0",
    # drf-spectacular não herda o DEFAULT_PERMISSION_CLASSES global do
    # DRF (SERVE_PERMISSIONS tem seu próprio default, AllowAny) — por
    # isso é preciso declarar explicitamente aqui para exigir a mesma
    # API Key das demais rotas (não há login de admin, já que este
    # serviço não possui banco de dados/usuários). A authentication
    # class já é herdada corretamente do DEFAULT_AUTHENTICATION_CLASSES.
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAuthenticated"],
    "SCHEMA_PATH_PREFIX": "/api/v1/",
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": API_KEY_HEADER,
            },
        },
    },
    "SECURITY": [{"ApiKeyAuth": []}],
}

# KeyDB (BFF_BROKER): broker do Celery e cache de estado da UI.
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://keydb:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_TIME_LIMIT = 30

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("KEYDB_CACHE_URL", default="redis://keydb:6379/1"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    },
}

if not DEBUG and not RUNNING_TESTS:
    CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
    SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=518400)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
        "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
    )
    SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
    SECURE_CONTENT_TYPE_NOSNIFF = True
