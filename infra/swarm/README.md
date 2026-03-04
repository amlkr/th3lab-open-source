# Swarm Phase 2 (Local Runtime)

Este stack levanta:

- Postgres
- Redis
- Backend FastAPI
- Celery worker
- MCP bridge

## 1) Preparar variables

```bash
cp .env.example .env
```

## 2) Levantar stack

Desde raíz del repo:

```bash
docker compose -f infra/swarm/docker-compose.phase2.yml --env-file infra/swarm/.env up -d --build
```

## 3) Verificar

```bash
curl http://localhost:8000/health
curl http://localhost:8090/health
```

## 4) Operación creativa (sin programar)

Usa `think.sh` desde raíz:

```bash
./think.sh worlds
./think.sh ingest amniotic /ruta/a/teoria
./think.sh ask amniotic "Que estructura estilistica emerge de estos textos?"
./think.sh agent "Dame un manifiesto visual en 5 principios para este proyecto"
```

