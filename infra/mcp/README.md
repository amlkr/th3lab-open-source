# th3lab MCP Bridge

Bridge operativo para biblioteca teórica y consultas estilísticas.

## Endpoints

- `GET /health`
- `POST /mcp/world/ingest`
  - body: `{ "world_id": "...", "path": "...", "project_id": "_admin" }`
- `POST /mcp/world/query`
  - body: `{ "world_id": "...", "question": "...", "n_results": 5 }`
- `POST /mcp/world/ask`
  - body: `{ "world_id": "...", "message": "...", "project_id": "..." }`

## Ejemplo

```bash
curl -X POST http://localhost:8090/mcp/world/ingest \
  -H "Content-Type: application/json" \
  -d '{"world_id":"amniotic","path":"text"}'
```

