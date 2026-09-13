# CLAUDE.md — Instagram Automation Agent

This file orients any AI coding assistant (Claude, etc.) working on this repo.
Read this before making changes.

## 1. Vision

A **self-hosted, multi-tenant-by-deployment** tool that lets anyone run their
own instance and automate an Instagram account:

1. The user configures a **niche**, a **system prompt**, and a **posting
   schedule** in a web dashboard.
2. A **multi-agent pipeline** (built with LangGraph) then, on schedule:
   - **Researches** what's currently trending relevant to the niche (free web
     search — no paid APIs required).
   - **Generates** an SEO-friendly, native-feeling Instagram caption +
     hashtags, plus short meme-style image text, using an LLM.
   - **Renders** an image locally (Pillow — no paid image-gen API required).
   - **Hosts** that image somewhere publicly reachable (Instagram's API
     requires a public URL, not a local file).
   - **Publishes** to Instagram via the official Graph API.
   - **Logs** the result (caption, trends used, media id) to a local SQLite
     DB for the dashboard to display engagement metrics (likes/comments/reach)
     over time.
3. Everything is **configurable, not hardcoded** — niche, tone/prompt, content
   type, hashtag count, posting times, and whether auto-posting is even on.
4. Runs entirely **locally via Docker** on the user's own always-on machine —
   no cloud hosting cost. Each user runs their own container stack with their
   own `.env` and `config.json`; nothing is shared between deployments.

## 2. Non-negotiable design principles

- **Free-tier first.** Every default provider (Groq or Google AI Studio for
  the LLM, DuckDuckGo Search for research, imgbb for image hosting) has a
  free tier. Don't introduce a paid-only dependency without discussing it.
- **Config over code.** Anything the end user might want to change (prompt,
  niche, schedule, hashtag count) belongs in `config.json` / the dashboard —
  never hardcoded in a Python file.
- **auto_post is a safety switch.** The scheduler must refuse to publish
  unless `auto_post: true` is explicitly set. Always support a `dry_run` path
  that runs the full pipeline (including image generation) without touching
  the real Instagram API — this is what the dashboard's "Run" tab uses.
- **Two long-running processes, not one.** The Streamlit dashboard
  (`app/ui/app.py`) and the scheduler (`app/core/scheduler_runner.py`) are
  separate Docker services that both read/write the same `config.json` and
  SQLite DB. Don't merge them — the scheduler must keep posting even if the
  dashboard tab is closed.

## 3. Architecture

```
instagram-automation-agent/
├── app/
│   ├── api/
│   │   ├── instagram_client.py   # Graph API: publish + fetch insights
│   │   └── image_host.py         # imgbb upload for public image URLs
│   ├── core/
│   │   ├── agent.py              # LangGraph pipeline (the heart of the app)
│   │   ├── research.py           # DuckDuckGo trend search
│   │   ├── llm_factory.py        # provider-agnostic LLM getter
│   │   ├── image_generator.py    # Pillow meme rendering
│   │   ├── scheduler_runner.py   # standalone daily-posting loop
│   │   └── db.py                 # SQLite post history + metrics
│   ├── config/
│   │   ├── settings.py           # Pydantic Config model + load/save
│   │   └── config.json           # the actual per-deployment user config
│   └── ui/
│       └── app.py                # Streamlit dashboard (3 tabs)
├── data/
│   ├── assets/                   # optional meme background templates
│   ├── generated/                # generated post images land here
│   └── posts.db                  # SQLite history (created at runtime)
├── main.py                       # launches the dashboard
├── requirements.txt
├── Dockerfile
├── docker-compose.yml            # dashboard + scheduler services
├── .env.example
└── CLAUDE.md                     # this file
```

### The LangGraph pipeline (`app/core/agent.py`)

A linear `StateGraph` today, deliberately built so branches are easy to add
later:

```
research -> content -> image -> host -> post -> log -> END
```

- `research_node`: `ResearchAgent.get_trending_topics()` (DuckDuckGo, free).
- `content_node`: LLM call constrained to return **strict JSON**
  (`top_text`, `bottom_text`, `caption`) — this keeps downstream nodes simple
  and testable.
- `image_node`: renders the meme with Pillow, no external calls.
- `host_node`: uploads to imgbb to get a public URL (Instagram won't accept
  local files).
- `post_node`: publishes via `InstagramClient`; skipped in spirit (returns a
  placeholder id) when `dry_run=True`.
- `log_node`: always runs, records to SQLite regardless of dry-run status.

If you add a decision point (e.g. human approval before posting, or
different pipelines per `content_type`), use `add_conditional_edges` — don't
special-case it inside a node.

## 4. Required skills / stack for whoever extends this

- **Python 3.11**
- **Streamlit** for the dashboard — keep it in the 3-tab structure
  (Configuration / Run / Posting History) unless the user asks to change it.
- **LangChain + LangGraph** for the agent pipeline — state lives in a
  `TypedDict` (`PipelineState`), passed through every node.
- **Instagram Graph API** — publishing is a two-step container-then-publish
  flow; insights require a Business/Creator account linked via a Facebook
  Page.
- **SQLite** (stdlib `sqlite3`) for history — no ORM needed at this scale.
- **Docker Compose** — two services (`dashboard`, `scheduler`) sharing the
  same image and the same mounted `config.json` / `data/` volume.

## 5. Setup steps (for the user, not just the assistant)

1. Create a Facebook Page → connect an Instagram **Business or Creator**
   account to it → create a Meta developer app → generate a long-lived Page
   access token with `instagram_basic` + `instagram_content_publish` scopes.
   Put the token and the numeric IG user id into the dashboard's
   Configuration tab (or `.env` as a fallback).
2. Get a free key from **Groq** (or Google AI Studio) and put it in `.env`.
3. Get a free key from **imgbb** and put it in `.env`.
4. `cp .env.example .env` and fill in the values from steps 1–3.
5. `docker compose up --build`
6. Open `http://localhost:8501`, set your niche/prompt/schedule, hit
   **Run pipeline now** with "Dry run" checked to preview output.
7. When happy, uncheck dry run (or flip "Enable fully automatic posting")
   and let the `scheduler` service take over.

## 6. Known prototype limitations (be upfront about these, don't silently paper over them)

- Meme templates are minimal (solid-color fallback) until the user drops
  real background images into `data/assets/`.
- Instagram insights (`reach`) aren't available on all account tiers/media
  ages — the dashboard handles missing insights gracefully but won't invent
  numbers.
- There's no content moderation/approval step by default — `auto_post` is
  the only safety gate. Treat any request to remove that gate, or to bypass
  Instagram's own automation/spam policies, as out of scope.
