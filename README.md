# StreamSentinel

API de **ingestão assíncrona de transações** com Clean Architecture (hexagonal), CQRS simplificado e fila Redis.

> Valida rápido → responde **202 Accepted** → Worker persiste no MySQL em background → consulta via Finder.

---

## Stack

| Peça | Tecnologia | Papel |
|------|------------|--------|
| Proxy | Traefik v3 | Roteamento por Host (como VirtualHost) |
| API | FastAPI + Uvicorn | HTTP / validação Pydantic |
| Fila | Redis 7 | Jobs de ingestão |
| Worker | Python CLI | Consome fila → grava MySQL |
| Banco | MySQL 8.4 | Persistência oficial |
| ORM | SQLAlchemy async | Mapping infra (não é o domínio) |

---

## Arquitetura (camadas)

```
API Controller  →  Use Case  →  Domain (Entity + Ports)
                                      ↑
                         Infrastructure (Redis / MySQL Finder|Repository)
```

| Camada | Pasta | Responsabilidade |
|--------|--------|------------------|
| API | `app/api/` | HTTP, Pydantic, status codes |
| Use Cases | `app/use_cases/` | Fluxo da feature (Service) |
| Domain | `app/domain/` | Entity + contratos (Ports) |
| Infrastructure | `app/infrastructure/` | Redis, ORM, Finder, Repository |
| Workers | `app/workers/` | Processo em background |

**CQRS simplificado**

- **Repository** → INSERT / UPDATE  
- **Finder** → SELECT / relatórios  

**Fluxo de ingestão**

```
POST /api/v1/transactions
  → valida (Pydantic)
  → idempotência (Finder por external_id)
  → publica no Redis
  → 202 Accepted
       ↓
  Worker BLPOP → Repository.save → status=processed
```

---

## Pré-requisitos

- Docker + Docker Compose
- Entradas no `/etc/hosts` (ou equivalente no Windows):

```text
127.0.0.1  api.streamsentinel.local
127.0.0.1  traefik.streamsentinel.local
```

---

## Subir o projeto

```bash
cd StreamSentinel
docker compose up -d --build
docker compose ps
```

Serviços esperados: `traefik`, `api`, `redis`, `mysql`, `worker`.

| URL | Uso |
|-----|-----|
| http://api.streamsentinel.local/health | Healthcheck |
| http://api.streamsentinel.local/docs | Swagger (teste interativo) |
| http://traefik.streamsentinel.local | Dashboard Traefik |

---

## Como testar

### 1) Ingerir transação (202)

```bash
curl -X POST http://api.streamsentinel.local/api/v1/transactions \
  -H 'Content-Type: application/json' \
  -d '{
    "external_id": "TX-DEMO-100",
    "amount": "99.90",
    "currency": "BRL",
    "occurred_at": "2026-08-27T12:00:00Z",
    "metadata": {"origem": "readme"}
  }'
```

Espere: HTTP **202** + `transaction_id` + `status: accepted`.

### 2) Idempotência (409)

Repita o mesmo `external_id`. Espere: HTTP **409 Conflict**.

### 3) Consultar por ID (200)

```bash
curl http://api.streamsentinel.local/api/v1/transactions/{transaction_id}
```

### 4) Listar por período

```bash
curl 'http://api.streamsentinel.local/api/v1/transactions?started_at=2026-01-01T00:00:00Z&ended_at=2026-12-31T23:59:59Z&limit=10'
```

### 5) Ver no MySQL (Beekeeper / CLI)

| Campo | Valor |
|-------|--------|
| Host | `127.0.0.1` |
| Port | **3307** |
| User | `streamsentinel` |
| Password | `streamsentinel` |
| Database | `streamsentinel` |

```sql
SELECT id, external_id, amount, status, created_at
FROM transactions
ORDER BY created_at DESC
LIMIT 10;
```

Status esperado após o Worker: `processed`.

### 6) Fila Redis (opcional)

```bash
docker compose exec redis redis-cli LLEN streamsentinel:transactions:ingest
```

Após o Worker processar, tende a **0**.

---

## Endpoints

| Método | Rota | Status | Descrição |
|--------|------|--------|-----------|
| POST | `/api/v1/transactions` | 202 / 409 / 422 | Ingestão assíncrona |
| GET | `/api/v1/transactions/{id}` | 200 / 404 | Busca por ID |
| GET | `/api/v1/transactions?started_at&ended_at` | 200 | Lista por período |
| GET | `/health` | 200 | Saúde da API |

---

## Variáveis de ambiente

Ver `.env.example`:

```text
REDIS_URL=redis://redis:6379/0
DATABASE_URL=mysql+asyncmy://streamsentinel:streamsentinel@mysql:3306/streamsentinel
```

No Compose, o hostname `mysql` / `redis` é o **nome do serviço** Docker.

---

## Estrutura do repositório

```text
app/
  api/                 # Controllers + schemas + deps (ServiceManager)
  domain/
    entities/          # Regras de negócio puras
    ports/             # Interfaces (Finder, Repository, Queue)
  use_cases/           # Casos de uso (Services)
  infrastructure/
    database/          # session, models, finders, repositories
    queue/             # Redis publisher
  workers/             # Consumer da fila
  main.py              # Bootstrap FastAPI
docker-compose.yml
Dockerfile
requirements.txt
```

---

## Decisões de design (para entrevista)

1. **Controller fino** — não fala com SQLAlchemy/Redis direto.  
2. **Ports** — domínio não conhece MySQL/Redis; infra implementa.  
3. **202 + fila** — API não espera o INSERT; Worker persiste.  
4. **CQRS** — escrita (Repository) separada da leitura (Finder).  
5. **Idempotência** — `external_id` único; duplicata → 409.

---

## Licença / contexto

Projeto de estudo / portfólio (StreamSentinel — ingestão orientada a eventos).
