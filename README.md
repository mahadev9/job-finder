# Job Finder

An AI-powered job discovery and matching agent. It scrapes job postings from company career pages and job boards, then scores each listing against your CV and profile using an LLM — surfacing the best matches in a Reflex web UI.

---

## Quick Start (Docker Compose)

### 1. Configure environment

Copy the example and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` — at minimum set `LLM_MODEL` and the matching API key (see [Environment Variables](#environment-variables)).

### 2. Edit your templates

Before running, personalise the three template files in `templates/`:

- `templates/cv.md` — your CV/resume in Markdown
- `templates/profile.md` — your target roles, comp targets, location policy
- `templates/portals.yml` — which companies and job boards to scan

See [Template Files](#template-files) below for details.

### 3. Build and run

```bash
docker compose up --build
```

The web UI is available at `http://localhost:8000` once the container starts.

> **Note:** The first start takes a minute — Reflex compiles the Next.js frontend on launch.

### 4. Stop

```bash
docker compose down
```

Data (SQLite database) is persisted in `./data/` on the host and survives restarts.

---

## Environment Variables

Create a `.env` file in the project root. All variables are optional except `LLM_MODEL` and its matching key.

```dotenv
# ── LLM provider ──────────────────────────────────────────────────────────────
# Uncomment ONE model and supply its key below.

# LM Studio (local — no key needed, but LM_STUDIO_BASE_URL must be reachable)
LLM_MODEL=lmstudio:qwen/qwen3.6-27b

# OpenAI
# LLM_MODEL=openai:gpt-4o
# OPENAI_API_KEY=sk-...

# Google Gemini
# LLM_MODEL=google_genai:gemini-2.0-flash
# GEMINI_API_KEY=...

# Anthropic
# LLM_MODEL=anthropic:claude-sonnet-4-6
# ANTHROPIC_API_KEY=sk-ant-...

# ── LM Studio (only needed when using lmstudio: model) ────────────────────────
LM_STUDIO_API_KEY=
LM_STUDIO_BASE_URL=http://localhost:1234/v1

# ── Storage ───────────────────────────────────────────────────────────────────
# Path inside the container where data/ is mounted (default: /mnt)
MOUNT_FOLDER=/mnt/
```

> **Docker + LM Studio:** If LM Studio runs on the host machine, set  
> `LM_STUDIO_BASE_URL=http://host.docker.internal:1234/v1` so the container can reach it.

---

## Template Files

All three files live in `templates/` and are mounted read-only into the container.  
Edit them on the host; restart the container to pick up changes.

### `templates/cv.md`

Paste your CV here in plain Markdown. The matcher reads this file and compares each job description against it. Structure doesn't matter — plain paragraphs, bullet points, or a formatted resume all work. The more detail you include (skills, tools, project outcomes), the better the match quality.

### `templates/profile.md`

Describes **who you are** and **what you want**. The LLM uses this as scoring context. Key sections to personalise:

| Section | What to edit |
|---------|-------------|
| `## Target Roles` | Table of archetypes and what employers buy — add/remove rows to match your search |
| `## Comp Targets` | Target and minimum salary, location preference, visa status |
| `## Location Policy` | How to score remote / local / international roles |
| `## Exit Narrative` | 2–3 sentences the LLM uses to frame cover letter openings |

You don't need to follow the exact format — plain prose works. The important thing is stating your target role types, location constraints, and compensation floor.

### `templates/portals.yml`

Controls **where** the fetch pipeline looks for jobs.

```yaml
# Optional: filter jobs by location keyword before storing
location_filter:
  allow:
    - "Remote"
    - "United States"
  block:
    - "India"
    - "United Kingdom"

# Role title keywords — only jobs matching a positive keyword are stored
title_filter:
  positive:
    - "AI Engineer"
    - "ML Engineer"
    - "Machine Learning"
  negative:
    - "Manager"
    - "Director"

# Generic job board search queries (uses web search)
search_queries:
  - query: "AI Engineer jobs site:greenhouse.io"
  - query: "ML Engineer remote jobs site:lever.co"

# Specific companies to track (scraped directly from their careers page)
tracked_companies:
  - name: "Anthropic"
    careers_url: "https://www.anthropic.com/careers"
    enabled: true
    scan_query: "AI Engineer"       # optional: narrows the careers page search

  - name: "OpenAI"
    careers_url: "https://openai.com/careers"
    enabled: true
```

**Tips:**
- `careers_url` should be the **branded** careers page (e.g. `careers.company.com`), not a raw ATS URL — raw ATS URLs can return 410 errors.
- Set `enabled: false` to pause a company without deleting it.
- `scan_query` is optional; omit it to scan all roles on the page.
- `location_filter` and `title_filter` are applied before the job is stored — they keep the database clean.

---

## Using the UI

1. **Fetch New Jobs** — scrapes all sources in `portals.yml` and stores new listings. Results appear in the **Fetched Jobs** tab.
2. **Run Match Pipeline** — scores stored jobs against your CV and profile. Results appear in the **Matched Jobs** tab.
3. **Matched Jobs** — filter by status (Pending / Applied / Rejected / Low Match), date range. Click a role to open the original posting.
4. **Status updates** — use the status dropdown on any matched job row to mark it Applied or Rejected.

---

## Local Development (without Docker)

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit environment
cp .env.example .env

# Run in dev mode (hot-reload)
reflex run

# Or prod mode
reflex run --env prod
```

The dev server runs on `http://localhost:3000`.

---

## Project Structure

```
job-finder/
├── templates/
│   ├── cv.md              # Your CV — edit this
│   ├── profile.md         # Your target roles and preferences — edit this
│   └── portals.yml        # Companies and search queries — edit this
├── job_finder/            # Reflex app (UI + state)
├── services/              # Fetch and match pipeline logic
├── database/              # SQLAlchemy models and migrations
├── core/                  # Logging and settings
├── mcp_server.py          # Optional MCP server
├── data/                  # SQLite database (created on first run)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Credits

Inspired by [career-ops](https://github.com/santifer/career-ops) by [@santifer](https://github.com/santifer).