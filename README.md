# BFF - Django + Django Rest Framework SME - Autosserviço

## 🥞 Stack

- [Python 3.12](https://docs.python.org/3.12/)
- [Django 5.1](https://docs.djangoproject.com/en/5.1/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [drf-spectacular](https://drf-spectacular.readthedocs.io/) (OpenAPI schema)
- [Celery](https://docs.celeryq.dev/) + [KeyDB](https://docs.keydb.dev/) (broker de tasks e cache de estado da UI)
- [pytest](https://docs.pytest.org/) + [pytest-django](https://pytest-django.readthedocs.io/)
- [Black](https://black.readthedocs.io/) + [Ruff](https://docs.astral.sh/ruff/) + [mypy](https://mypy.readthedocs.io/) + [pre-commit](https://pre-commit.com/)
- [Sphinx](https://www.sphinx-doc.org/) (documentação técnica)
- [Docker](https://docs.docker.com/) / [Docker Compose](https://docs.docker.com/compose/)

## 🧭 Papel do BFF na arquitetura

Este serviço é o **BFF (Backend For Frontend)** do Autosserviço: fica entre o
`SME-Autosservico-Frontend` (Next.js) e as demais fontes de dados, orquestrando
e roteando as chamadas necessárias para montar as respostas consumidas pelo
frontend. Hoje ele fala com o `SME-Autosservico-Backend` (métricas de
coordenadorias); a comunicação com outras fontes está mapeada como próximos
passos (veja [Roadmap](#-roadmap)).

**Este BFF é estritamente stateless**: não possui banco de dados relacional
nem migrations locais — é focado em agregação. A arquitetura interna (nível
C3) segue três camadas:

1. **Camada de Request (síncrona)**: as views recebem a requisição HTTP do
   frontend, validam a API Key e consultam o estado já cacheado no
   `BFF_BROKER` — nunca fazem chamadas de I/O externas em tempo de
   requisição.
2. **Broker e Cache (KeyDB)**: o `BFF_BROKER` tem papel duplo — cache dos
   payloads agregados prontos para a UI, e message broker das tasks do
   Celery.
3. **Background (Celery Workers)**: consumidores assíncronos que executam
   as integrações reais (Zabbix, Jenkins, Azure DevOps, Grafana), absorvendo
   a latência de rede sem degradar a experiência síncrona do usuário.

As chamadas de saída para o ecossistema de integrações devem futuramente
passar pelo **SME Sidecar SDK** (circuit breaker/retry + tracing
OpenTelemetry) — ainda não referenciado no código, entra junto da primeira
task de integração real.

## 🛠️ Configurando o projeto

### 🔄 via HTTPS

```bash
git clone https://github.com/<organizacao>/SME-Autosservico-BFF.git
```

### 🔐 via SSH

```bash
git clone git@github.com:<organizacao>/SME-Autosservico-BFF.git
```

### 🐳 Rodando com Docker

**Ambiente de desenvolvimento** (hot-reload, `runserver`, suporte a debug remoto na porta `5678` via [debugpy](https://github.com/microsoft/debugpy)):

```bash
cp .env.example .env
docker compose -f docker-compose-dev.yml up --build
```

**Ambiente "prod-like"** (Gunicorn + `collectstatic` automático):

```bash
cp .env.example .env
docker compose up --build
```

Em ambos os casos sobem três serviços: `web` (Django, porta `8000`), `worker`
(Celery) e `keydb` (broker/cache, porta `6379`). Como o BFF não possui banco
de dados relacional, não há etapa de `migrate`.

### 🐍 Rodando com virtualenv

#### Criando e ativando uma virtual env

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

#### Instalando as dependências do projeto

```bash
pip install -r requirements/local.txt
```

#### Configurando as variáveis de ambiente

```bash
cp .env.example .env
```

Ajuste os valores em `.env` conforme necessário — em especial `CELERY_BROKER_URL`/`KEYDB_CACHE_URL` caso o KeyDB não esteja rodando localmente via Docker.

#### Instalando o pre-commit

```bash
pre-commit install
# ou: scripts/executar_precommit.sh
```

#### Executando o projeto

```bash
python manage.py runserver
```

#### Executando o worker do Celery

```bash
celery -A config worker --loglevel=info
```

## 🔐 Autenticação

Como microsserviço, a autenticação entre serviços é feita por **chave de API** enviada em um header HTTP (nome e valor configuráveis via `API_KEY_HEADER`/`API_KEY` no `.env`). O endpoint de health check é sempre público, independente de autenticação. Como este serviço não possui banco de dados/usuários, o Swagger UI (`/api/v1/docs/`) e o schema (`/api/v1/schema/`) são protegidos pela **mesma API Key**, não por login de superusuário.

## 🧪 Testes

### Executando os testes com Pytest

```bash
pytest
```

### Executando a cobertura dos testes

```bash
coverage run -m pytest
coverage report   # cobertura mínima exigida: 80%
coverage html
```

Testes unitários ficam dentro de cada app, em `apps/<dominio>/tests/`. A pasta `testes/` na raiz é reservada para testes E2E (Cypress/Postman), ainda não configurados.

## 📚 Documentação técnica (Sphinx)

```bash
cd docs
make html      # gera a documentação em docs/_build/html
make livehtml  # build com live-reload em http://localhost:9000
make apidocs   # regenera os .rst de API a partir dos apps
```

A documentação de domínio (regras de negócio, decisões arquiteturais) fica em `docs/dominios/<dominio>/`.

## 📄 API / OpenAPI

- Schema (JSON): `GET /api/v1/schema/` (requer API Key)
- Swagger UI: `GET /api/v1/docs/` (requer API Key)
- Health check: `GET /api/v1/health/` (público)

## 🩺 Health Check

O endpoint `GET /api/v1/health/` retorna `{"status": "ok"}` e não exige autenticação. É utilizado por probes de liveness/orquestradores para verificar se o processo da aplicação está no ar.

## 📡 Zabbix

Integração com o Zabbix (porte do que hoje vive no `SME-Autosservico-Frontend`, mesmo contrato de rotas/resposta):

- `GET /api/v1/zabbix/status/<preset>/` (`producao` ou `filas`) — status de disponibilidade, via `trigger.get`.
- `GET /api/v1/zabbix/database/` — status de banco de dados por sistema, via `item.get`.
- `GET /api/v1/zabbix/jenkins/job/` — resumo de build do Jenkins, também lido via `item.get` (outro sistema já coleta os dados do Jenkins e grava no Zabbix).

A camada de request nunca chama o Zabbix diretamente — só lê o cache do `BFF_BROKER` (KeyDB). Em cache frio, dispara uma Celery task em background e devolve um fallback seguro na hora; o status de banco de dados também é atualizado periodicamente por uma Celery Beat. Ver `docs/dominios/zabbix/` para detalhes.

## ☁️ Azure DevOps

Integração direta com a REST API do Azure DevOps (`dev.azure.com`), sem serviço intermediário, devolvendo o mesmo contrato de resposta já consumido pelo frontend:

- `GET /api/v1/azure/backlog/?project_name=<projeto>` — backlog de work items do projeto, separado entre `parents` e `children`, com as métricas de bugs do ciclo (`total_cycle`, `open`, `in_progress`, `resolved` e o tempo médio de atendimento já formatado em pt-br).
- `POST /api/v1/azure/backlog/` — mesmo backlog, com os filtros no corpo (listas em vez de valores separados por vírgula).
- `GET /api/v1/azure/backlog/diagnostics/?project_name=<projeto>` — contagem de work items por tipo, com amostra dos 20 primeiros. Útil para descobrir quais tipos um projeto usa antes de configurar os filtros.
- `GET /api/v1/azure/projects/` — projetos da organização, paginados por `top`/`skip`/`continuation_token`.

Filtros opcionais do backlog: `organization`, `start_date`/`end_date` (`YYYY-MM-DD`), `year`/`month`, `work_item_types`, `states`, `area_paths`, `iteration_paths`, `assigned_to` e `tags` — no `GET`, os de lista aceitam valores separados por vírgula. Filtros equivalentes por `GET` e `POST` compartilham a mesma entrada de cache.

O campo `pat` é aceito no corpo do `POST` por compatibilidade, mas **ignorado**: o token vem sempre de `AZURE_DEVOPS_PAT`, nunca da requisição.

A carga acontece em duas etapas no Azure (uma consulta WIQL para os ids, depois os detalhes em lotes de 200), então a camada de request nunca a executa: em cache frio, dispara uma Celery task e devolve na hora um backlog vazio — o mesmo payload que o Azure produz quando nada casa com os filtros. Ver `docs/dominios/azure/` para detalhes.

## 🗺️ Roadmap

Próximos cards já mapeados para a evolução deste BFF:

- Integrar o **SME Sidecar SDK** (circuit breaker/retry + tracing) nas integrações já existentes.
- Ampliar a comunicação com o **Azure DevOps** para o status de pipelines (o backlog de bugs já está implementado).
- Implementar comunicação com o **Grafana** (observabilidade/telemetria).

## 📄 Licença

Este projeto está licenciado sob a [GNU Affero General Public License v3.0](./LICENSE).
