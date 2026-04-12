# Eisenherz

YouTube Shorts 음악 채널을 위한 콘텐츠 라이브러리 + AI 프롬프트 워크스테이션.

![Dashboard](static/screenshot-dashboard.png)

## Why

YouTube Shorts 음악 채널을 운영하면 이런 문제가 생깁니다:

- 조회수 잘 나온 영상의 **프롬프트를 까먹는다** -- Suno에 뭘 넣었는지, 어떤 스타일로 영상을 만들었는지
- 어떤 장르/서브스타일이 **성과가 좋은지 감으로만 판단**한다
- 새 영상 만들 때마다 프롬프트를 **처음부터 다시 쓴다**
- 채널 전체 콘텐츠를 **한눈에 못 본다**

Eisenherz는 이 문제를 해결합니다:

1. **프롬프트 아카이브** -- Suno 음악 프롬프트 + 영상 프롬프트를 프로젝트 단위로 저장. 조회수 잘 나온 콘텐츠의 레시피를 언제든 다시 꺼내볼 수 있습니다.
2. **YouTube 채널 싱크** -- Data API v3로 채널 전체 영상을 가져와서 조회수/좋아요/댓글 추적. Shorts와 Videos를 자동 분류합니다.
3. **성과 분석** -- 장르별, 서브스타일별 평균 조회수와 engagement rate를 비교. "이번 달은 어떤 스타일이 먹혔나"를 데이터로 봅니다.
4. **AI 프롬프트 생성** -- 장르만 넣으면 Suno 프롬프트 + 4세트 영상 프롬프트가 동시에 나옵니다. shranz 계열은 12개 서브스타일 중 최근 안 쓴 걸 자동 선택합니다.

## Core Flow

```
장르 선택 → Suno 프롬프트 + 영상 프롬프트 자동 생성
                ↓
        Suno에서 음악 생성, Kling/Higgsfield에서 영상 생성
                ↓
        YouTube 업로드 → 채널 싱크로 자동 라이브러리 등록
                ↓
        조회수/engagement 분석 → 다음 콘텐츠에 반영
```

## Features

- **Content Library** -- Shorts(9:16) 그리드 + Videos(16:9) 리스트, 무드 태그, 모티프 태그, 메모
- **Suno Prompt Generator** -- 장르별 음악 프롬프트 + 구조화 가사 ([Verse], [Chorus] 등)
- **Video Prompt Generator** -- Zoom/Pan/Subject/Atmosphere 4세트 영상 프롬프트
- **YouTube Sync** -- 채널 전체 영상 메타데이터 + 통계 자동 수집
- **Analytics** -- 장르/서브스타일별 성과 랭킹, LLM 비용 추적
- **YouTube Metadata** -- AI 생성 제목/설명/태그/고정 댓글
- **Preview** -- 카드에서 바로 YouTube 미리보기 재생
- **Substyle Diversity** -- shranz/schranz 12개 서브스타일 자동 로테이션

## Quick Start

```bash
git clone https://github.com/slimex200-wq/youtube-shorts-music.git
cd youtube-shorts-music
pip install -r requirements.txt
cp .env.example .env   # YOUTUBE_API_KEY 설정
python -m uvicorn web:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`

## Requirements

- Python 3.11+
- FFmpeg (for video composition)
- Claude CLI (free on Max) or Anthropic API key

### LLM Backends

| Backend | Config | Cost |
|---------|--------|------|
| Claude CLI (default) | Claude Max subscription | $0 per call |
| Anthropic API | `LLM_MODE=api` + `ANTHROPIC_API_KEY` | Pay per token |

## Architecture

```
web.py                  FastAPI server (19 endpoints)
models/project.py       JSON-based project storage
services/
  suno_prompt.py        Suno music prompt generation
  higgsfield_prompt.py  Video prompt generation
  metadata.py           YouTube SEO metadata
  youtube_sync.py       YouTube Data API sync
  llm.py                LLM abstraction (CLI + API)
  kb.py                 Channel knowledge base
  shranz_substyles.py   12 substyle definitions
  beat_analyzer.py      BPM + beat detection
  composer.py           FFmpeg video pipeline
static/
  index.html            Single-page dashboard
  app.js                Frontend logic (~1900 lines)
  styles.css            Industrial control panel UI
```

## License

MIT
