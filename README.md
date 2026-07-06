# MinusPod Fork

> **Fork of [ttlequals0/MinusPod](https://github.com/ttlequals0/MinusPod)** — the self-hosted podcast ad remover.  
> This fork adds **original-audio fallback** and **RSS status labeling** so you can use a single podcast feed that plays instantly, with episodes getting cleaned in the background.

<p align="center">
  <img src="frontend/public/logo.png" alt="MinusPod" width="400" />
</p>

## Why This Fork?

The upstream MinusPod is excellent at detecting and removing ads — but the listening experience has a friction problem: **if an episode hasn't been processed yet, you can't listen to it**. The server returns HTTP 503 and you have to wait 10-15 minutes for processing to complete before you can play it.

This fork fixes that with three changes:

### 1. Original Audio Fallback ⭐

**Upstream behavior:** Unprocessed episode → HTTP 503 "try again in 30s"  
**Fork behavior:** Unprocessed episode → stream the original audio immediately, trigger processing in the background, swap to the cleaned version when ready

You press play, you get audio. No waiting, no 503 errors. The episode gets cleaned while you listen and the next time you play it, you get the ad-free version.

### 2. RSS Status Labeling ⭐

Each episode in the RSS feed gets a status tag in its title so you can tell at a glance in your podcast app what's been cleaned:

| Title in Podcast App | Meaning |
|---|---|
| `The British Grand Prix Review [Ad-Free]` | Processed — ads removed |
| `The Next Episode [Cleaning...]` | Currently being processed |
| `Another Episode` | Not yet processed — original audio |

### 3. HEAD Request Caching ⭐

Upstream MinusPod re-fetches the entire upstream RSS feed (up to 7 MB for some podcasts) on every single HEAD request from a podcast app. Refreshing a feed with 12 episodes fires 12 upstream fetches, blocking all workers. This fork caches RSS lookups so HEAD requests are served from cache — no more server lockups when you refresh your feeds.

---

## Architecture

![Architecture](docs/architecture.html)

<details>
<summary>Open the architecture diagram</summary>

Open [`docs/architecture.html`](docs/architecture.html) in any browser for an interactive SVG diagram.
</details>

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                 │
│  AntennaPod          MinusPod Web UI         Hermes Agent API        │
│  (Android)           (React Settings)       (Trigger/Monitor)       │
└──────┬──────────────────────┬────────────────────┬──────────────────┘
       │         HTTPS         │   via CF Tunnel    │
       ▼                      ▼                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│              Cloudflare Tunnel (pod.ogsapps.cc)                       │
└──────────────────────────────┬───────────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│              MINUSPOD CONTAINER (Podman Quadlet)                     │
│              Port 8000 • 4 Gunicorn Workers • 32 Threads             │
│                                                                       │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐   │
│  │  Flask App       │  │  Processing Pipe │  │   SQLite DB        │   │
│  │                  │  │                  │  │   podcast.db       │   │
│  │  • RSS Serving   │──│  1. Groq Whisper │  │   • Episodes      │   │
│  │  • Episode Serve │  │  2. NVIDIA LLM   │  │   • Settings      │   │
│  │  • REST API      │  │  3. FFmpeg Cut   │  │   • Patterns      │   │
│  │  • Auth (session)│  │  4. Pattern Learn│  │                    │   │
│  │                  │  │                  │  │  ┌──────────────┐  │   │
│  │ ★ Original       │  │  ~12 min total   │  │  │ Audio Storage│  │   │
│  │   Audio Fallback │  │  $0.00 / episode │  │  │ Processed MP3│  │   │
│  │                  │  │                  │  │  │ Transcripts  │  │   │
│  │ ★ RSS Status     │  │                  │  │  │ Chapters     │  │   │
│  │   Labeling       │  │                  │  │  └──────────────┘  │   │
│  │                  │  │                  │  │   5-day retention  │   │
│  │ ★ HEAD Caching   │  │                  │  │                    │   │
│  └─────────────────┘  └────────┬─────────┘  └────────────────────┘   │
│                                │                                      │
└────────────────────────────────┼──────────────────────────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL APIs (Free Tier)                          │
│  Groq (whisper-large-v3-turbo)   NVIDIA NIM (Llama/Qwen/Gemma)       │
│  Upstream Podcast RSS Feeds (Simplecast, Megaphone, CBC, etc)        │
└──────────────────────────────────────────────────────────────────────┘
```

## Files Modified (Fork Diff)

| File | Change | Description |
|------|--------|-------------|
| `src/main_app/routes.py` | `serve_episode()` | Serve original audio for unprocessed episodes instead of 503; trigger background processing non-blocking |
| `src/main_app/routes.py` | `_head_upstream()` | Cache upstream RSS lookups; serve HEAD from cache instead of re-fetching every time |
| `src/rss_parser.py` | `modify_feed()` | Append `[Ad-Free]` or `[Cleaning...]` to episode titles based on processing status |

All changes are backwards-compatible. If you don't want the fork features, the behavior is identical to upstream.

## Current Deployment

Running on bare metal:

- **Container:** `docker.io/ttlequals0/minuspod:cpu` via Podman Quadlet
- **LLM:** NVIDIA NIM free tier — Llama 3.3 70B (first pass), Qwen 3 Next 80B (verification), Gemma 4 31B (chapters)
- **Whisper:** Groq free tier — `whisper-large-v3-turbo`
- **Tunnel:** Cloudflare → `pod.ogsapps.cc`
- **Auth:** Session-based password auth (UI + API share same password)
- **Retention:** 5 days (auto-cleanup of processed files)
- **11 podcasts** configured, 7000+ episodes discovered

### Processing Performance

| Metric | Value |
|--------|-------|
| Transcription (57 min episode) | ~49 seconds (Groq) |
| Full processing (57 min episode) | ~12 minutes |
| Ads removed (typical) | 5-14 per episode |
| Cost per episode | $0.00 |

---

## Upstream Documentation

All original MinusPod documentation is preserved:

| Topic | |
|---|---|
| [How It Works & Detection Pipeline](docs/how-it-works.md) | Verification pass, sliding windows, queue, validation, pattern learning, audio analysis |
| [Installation & Upgrading](docs/installation.md) | Requirements, quick start, CPU image, upgrading to 2.0.0+ |
| [Web Interface](docs/web-interface.md) | Management UI, ad editor workflow, screenshots |
| [Configuration & Experiments](docs/configuration.md) | Settings, per-stage LLM tuning, VAD gap detector, ad reviewer, reprocessing, community patterns |
| [Environment Variables](docs/environment-variables.md) | Every env var, grouped by how often you touch it |
| [LLM Providers](docs/llm-providers.md) | Claude Code wrapper, Ollama, OpenRouter, recommended models, pricing |
| [Whisper / Transcription](docs/transcription.md) | GPU compute types, whisper.cpp, Groq, OpenAI Whisper, timeouts |

## Disclaimer

This tool is for personal use only. Only use it with podcasts you have permission to modify or where such modification is permitted under applicable laws. Respect content creators and their terms of service.

## License

MIT — same as upstream.

## Credits

Based on [ttlequals0/MinusPod](https://github.com/ttlequals0/MinusPod) by Dominick Krachtus.
