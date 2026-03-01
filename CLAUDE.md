# AMLKR Dashboard — Project Intelligence

## Who I am
This is the central dashboard for amlkr, a 37-year-old Argentine multimedia artist and filmmaker based in Australia, working at the intersection of documentary cinematography and generative AI systems.

## The Vision
Building an AI-powered visual analysis platform to validate and sell VISUAL CULT — an online course teaching AI cinematography to artists. The dashboard IS the product being sold. Every feature built here becomes course content.

## Two Modules

### th3lab
AI-powered film analysis tool. Analyzes video files for shot detection, camera movement, shot scale classification (ECS/CS/MS/FS/LS), brightness, saturation.

### VISUAL CULT
Online course: AI Cinematography for Artists. Three modules:
- Módulo 1: Mapa Visual Interno — student uploads reference images, system builds their internal visual map
- Módulo 2: Gramática de lo Visible — cinematographic grammar analysis
- Módulo 3: Serie Final + Modo Espejo — student uploads final series, system compares it to their visual map using CLIP mirror score 0-100

## Tech Stack — 100% Open Source, Zero API costs

### AI Models (all local via Ollama)
- Qwen2.5-VL:7b — multimodal, sees images directly, semantic visual analysis
- Qwen2.5:14b — text generation, narrative cinematographic reports in Spanish
- CLIP ViT-L/14 via open_clip — vector embeddings, cosine similarity, coherence scoring

### Backend
- Python 3.11 + FastAPI
- Celery + Redis for async job queue
- PostgreSQL (SQLAlchemy async)
- PySceneDetect + OpenCV for shot detection
- timm (EfficientNet) for shot scale classification
- Ollama Python client for Qwen

### Frontend
- React 18 + Vite + Tailwind
- Dark monochrome UI, violet accent (#8b5cf6)
- Fonts: Syne + DM Mono
- Two main views: /lab (th3lab), /studio (VISUAL CULT)

### Infrastructure
- Localhost: Docker (Postgres + Redis) + Ollama native on M4 Metal GPU
- Production: Vercel (frontend) + Hetzner CX33 €5.49/mo (backend)
- Storage: Cloudflare R2
- Hardware: Apple M4 Mac Mini 16GB RAM

## Key API Endpoints
- POST /api/analysis/video — shot detection + classification
- POST /api/analysis/images — CLIP + Qwen2.5-VL series analysis
- POST /api/analysis/visual-map — builds internal visual map from reference images
- POST /api/analysis/mirror — compares visual map vs final series (mirror score 0-100)
- POST /api/semantic/report — Qwen2.5:14b narrative cinematographic report

## CLIP Engine Logic
- Embeds images as 768-dim vectors (ViT-L/14)
- collection_coherence() — score 0-100 + outlier detection
- mirror_score() — compares map centroid vs series embeddings
- Runs on MPS (Apple Silicon Metal) automatically

## Semantic Engine Logic
- Qwen2.5-VL:7b analyzes each image → structured JSON (shot_scale, atmosphere, light_quality, composition_notes, dominant_colors, symbolic_elements)
- Qwen2.5:14b receives all technical data → generates narrative report using Belting/Arnheim/Berger framework
- Three report types: series report, visual map report, mirror report
- All prompts in Spanish, cinematographic vocabulary

## Theoretical Framework
- Hans Belting: imagen/medio/cuerpo
- Rudolf Arnheim: visual forces, tension, balance
- John Berger: gaze, power, context
- Vilém Flusser: technical images, apparatus

## UI Design Language
- Inspired by SolaFlux Behance dashboard style
- Dark monochrome base: #0a0a0c, #0e0e11, #131317
- Violet accent: #8b5cf6 (base), #a78bfa (hi), #c4b5fd (soft), #3d2a7a (dim)
- Key screens designed: Overview, Mapa Visual, Modo Espejo

## File Structure
amlkr-dashboard/
├── CLAUDE.md
├── docker-compose.yml
├── docker/init.sql
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── core/
│   │   ├── celery_app.py
│   │   └── database.py
│   ├── services/
│   │   ├── clip_engine.py
│   │   ├── semantic_engine.py
│   │   └── shot_analyzer.py
│   └── api/routes/
│       ├── analysis.py
│       ├── jobs.py
│       └── projects.py
└── frontend/
    └── src/

## Current Status
- Architecture fully designed and documented
- Backend services coded: clip_engine, semantic_engine, shot_analyzer
- UI designs completed: Overview, Mapa Visual, Modo Espejo
- NOT YET: Ollama models downloaded, Docker running, frontend built
- NEXT: Install Ollama + models, wire backend, test with amlkr real images

## Working Style
- Always open source, local-first
- Zero external API costs — Qwen runs local on M4
- Use MPS acceleration for Apple Silicon
- All Qwen prompts in Spanish
- The tool serves the artistic vision, not the other way around

## Target Users

### Instructor (amlkr)
- Uses desktop Mac for full dashboard
- Creates modules, worlds, libraries
- Manages student projects
- Runs analysis on own work

### Students
- Designers, photographers, visual artists
- Primary device: iPad Pro or desktop browser
- Has images in Apple Photos, PDFs in Files app
- Needs touch-first, visual-first interface
- No technical knowledge required

## Student-Facing Interface (iPad + Desktop)
- PWA installable from Safari on iPad
- Touch-first design: large cards, swipe navigation, bottom tab bar on mobile
- Upload images directly from iPad Camera Roll
- Upload PDFs and EPUBs from iPad Files app
- Chat interface with the agent (OpenClaw) in natural language
- See analysis results as visual cards, not data tables
- Personal library per student
- Progress through modules as a journey, not a dashboard

## Two Interface Modes
- /admin — full dashboard for instructor (amlkr), desktop optimized
- /app — student experience, iPad + desktop responsive, touch optimized

## Production Infrastructure (students connect here)
- Backend on Hetzner — Qwen + CLIP running in cloud for student analysis
- M4 Mac Mini — local development and instructor personal use only
- Vercel — frontend CDN, global fast loading on any device
