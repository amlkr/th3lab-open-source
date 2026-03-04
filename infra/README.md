# th3lab Phase 2 Infra

Objetivo: mover la operación de agentes y biblioteca teórica a una base de despliegue
estable, manteniendo intacto el diseño actual de th3lab en frontend.

## Qué incluye esta fase

- `swarm/`: stack local de servicios para operación continua.
- `mcp/`: servidor MCP-bridge para ingestar teoría y consultar mundos/proyectos.
- `argocd/`: manifiestos base para GitOps en Kubernetes (siguiente etapa de deploy).

## Principio de diseño

- Frontend de th3lab se mantiene como base visual (no se altera UI).
- Backend + Celery + Redis + Postgres + MCP quedan desacoplados del frontend.
- OpenClaw sigue siendo el plano de agentes; MCP expone acciones operativas.

## Arranque rápido local (fase 2)

```bash
cp infra/swarm/.env.example infra/swarm/.env
docker compose -f infra/swarm/docker-compose.phase2.yml up -d --build
```

Health checks clave:

```bash
curl http://localhost:8000/health
curl http://localhost:8090/health
openclaw gateway status
```

