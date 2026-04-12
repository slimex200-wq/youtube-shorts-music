# Eisenherz

AI-powered YouTube Shorts music video production toolkit.

Genre prompt generation, beat-synced video composition, YouTube SEO metadata — all from one dashboard.

![Dashboard](static/screenshot-dashboard.png)

## Features

- **Suno Prompt Generator** -- Genre-aware music prompts with structured lyrics, substyle diversity (12 shranz/schranz variants)
- **Video Prompt Generator** -- 4-set video prompts (zoom, pan, subject, atmosphere) for Higgsfield/Kling
- **YouTube Metadata** -- AI-generated titles, descriptions, tags, pinned comments
- **Beat Analysis** -- Librosa-based BPM detection, beat-aligned scene splitting
- **Video Composer** -- FFmpeg pipeline: Ken Burns, title cards, fade-out, bounce loops
- **YouTube Sync** -- Pull channel stats (views, likes, comments) via Data API v3
- **Analytics** -- Genre/substyle performance ranking, LLM cost tracking
- **Library** -- Mood tags, motif tags, visual refs, notes per project

## Quick Start

```bash
# Clone
git clone https://github.com/slimex200-wq/youtube-shorts-music.git
cd youtube-shorts-music

# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your keys

# Run
python -m uvicorn web:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`

## Requirements

- Python 3.11+
- FFmpeg (for video composition)
- Claude CLI or Anthropic API key (for AI generation)

### LLM Backends

| Backend | Config | Cost |
|---------|--------|------|
| Claude CLI (default) | Claude Max subscription | $0 per call |
| Anthropic API | `LLM_MODE=api` + `ANTHROPIC_API_KEY` | Pay per token |

## Architecture

```
web.py              FastAPI server (19 endpoints)
cli.py              CLI interface
models/project.py   JSON-based project storage
services/
  llm.py            LLM abstraction (CLI + API backends)
  suno_prompt.py    Suno music prompt generation
  higgsfield_prompt.py  Video prompt generation
  metadata.py       YouTube SEO metadata
  beat_analyzer.py  BPM + beat detection
  composer.py       FFmpeg video pipeline
  youtube_sync.py   YouTube Data API sync
  kb.py             Channel knowledge base
  shranz_substyles.py  12 substyle definitions
static/
  index.html        Single-page dashboard
  app.js            Frontend logic
  styles.css        Industrial control panel UI
```

## License

MIT
