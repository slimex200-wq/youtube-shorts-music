"""YouTube Shorts Music -- Web API"""
import logging
import shutil
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import PROJECTS_DIR
from models.project import Project
from services.llm import LLMError

logger = logging.getLogger(__name__)


def _safe_filename(name: str) -> str:
    """Strip directory components and reject path traversal attempts."""
    clean = Path(name).name
    if not clean or ".." in clean or clean.startswith("."):
        raise HTTPException(400, "Invalid filename")
    return clean

app = FastAPI(title="YouTube Shorts Music")


class CreateRequest(BaseModel):
    genre: str
    style: str | None = None
    instrumental: bool = False
    lyrics: str | None = None
    bpm: int | None = None
    mood: str | None = None
    substyle: str | None = None
    aspect_ratio: str = "9:16"
    model: str = "sonnet"


def _serialize(p: Project) -> dict:
    return {
        "id": p.id,
        "genre": p.genre,
        "aspect_ratio": p.aspect_ratio,
        "style": p.style,
        "status": p.status,
        "steps_completed": p.steps_completed,
        "instrumental": p.instrumental,
        "lyrics": p.lyrics,
        "suno_prompt": p.suno_prompt,
        "suno_prompt_history": p.suno_prompt_history,
        "video_prompts": p.video_prompts,
        "music_file": p.music_file,
        "bpm": p.bpm,
        "duration_sec": p.duration_sec,
        "scenes": p.scenes,
        "metadata": p.metadata,
        "mood_tags": p.mood_tags,
        "motif_tags": p.motif_tags,
        "visual_refs": p.visual_refs,
        "notes": p.notes,
        "title_lock": p.title_lock,
        "created_at": p.created_at,
        "last_edited_at": p.last_edited_at,
        "youtube_video_id": p.youtube_video_id,
        "youtube_stats": p.youtube_stats,
        "thumbnail_url": p.thumbnail_url,
        "last_error": p.last_error,
    }


def _load(pid: str) -> Project:
    if ".." in pid or "/" in pid or "\\" in pid:
        raise HTTPException(400, "Invalid project ID")
    try:
        return Project.load(pid)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")


# --- API ---


@app.post("/api/projects")
async def create_project(req: CreateRequest):
    project = Project.create(
        genre=req.genre, instrumental=req.instrumental, lyrics=req.lyrics,
        style=req.style, aspect_ratio=req.aspect_ratio,
    )
    project.update_status("created", step_name="create")

    from services.suno_prompt import SunoPromptGenerator

    gen = SunoPromptGenerator(projects_dir=str(PROJECTS_DIR), model=req.model)
    try:
        project.suno_prompt = gen.generate(
            genre=req.genre,
            bpm=req.bpm,
            mood=req.mood,
            lyrics=req.lyrics,
            instrumental=req.instrumental,
            substyle=req.substyle,
        )
    except Exception as e:
        logger.warning("Suno prompt generation failed: %s", e)

    # Video prompts (alongside Suno)
    from services.higgsfield_prompt import VideoPromptGenerator

    vgen = VideoPromptGenerator(model=req.model)
    try:
        project.video_prompts = vgen.generate(
            genre=req.genre,
            style=req.style or "",
            mood_tags=[req.mood] if req.mood else None,
        )
    except Exception as e:
        logger.warning("Video prompt generation failed: %s", e)

    project.save()
    return _serialize(project)


@app.post("/api/projects/{pid}/regenerate-suno")
async def regenerate_suno(pid: str):
    """현재 suno_prompt를 히스토리에 저장하고 변주 재생성"""
    project = _load(pid)

    # Save current to history
    if project.suno_prompt:
        project.suno_prompt_history.append(project.suno_prompt)

    from services.suno_prompt import SunoPromptGenerator

    gen = SunoPromptGenerator(projects_dir=str(PROJECTS_DIR))
    substyle = (project.suno_prompt or {}).get("substyle")
    try:
        project.suno_prompt = gen.generate(
            genre=project.genre,
            instrumental=project.instrumental,
            lyrics=project.lyrics,
            substyle=substyle,
        )
    except LLMError as e:
        raise HTTPException(503, f"LLM backend unavailable: {e}")
    except Exception as e:
        raise HTTPException(500, f"Suno regeneration failed: {e}")

    project.save()
    return _serialize(project)


@app.post("/api/projects/{pid}/restore-suno/{index}")
async def restore_suno(pid: str, index: int):
    """히스토리에서 이전 suno_prompt를 복원"""
    project = _load(pid)
    if index < 0 or index >= len(project.suno_prompt_history):
        raise HTTPException(400, "Invalid history index")

    # Swap current and selected
    if project.suno_prompt:
        project.suno_prompt_history.append(project.suno_prompt)
    project.suno_prompt = project.suno_prompt_history.pop(index)
    project.save()
    return _serialize(project)


@app.post("/api/projects/{pid}/clone")
async def clone_project(pid: str):
    """기존 프로젝트 설정을 복사하여 새 프로젝트 생성 + suno_prompt 재생성"""
    source = _load(pid)

    project = Project.create(
        genre=source.genre,
        instrumental=source.instrumental,
        style=source.style,
        aspect_ratio=source.aspect_ratio,
    )
    project.mood_tags = list(source.mood_tags)
    project.motif_tags = list(source.motif_tags)
    project.update_status("created", step_name="create")

    # Regenerate suno prompt with same genre/substyle preference
    from services.suno_prompt import SunoPromptGenerator

    gen = SunoPromptGenerator(projects_dir=str(PROJECTS_DIR))
    source_substyle = (source.suno_prompt or {}).get("substyle")
    try:
        project.suno_prompt = gen.generate(
            genre=source.genre,
            instrumental=source.instrumental,
            substyle=source_substyle,
        )
    except Exception as e:
        logger.warning("Clone suno prompt generation failed: %s", e)

    # Regenerate video prompts
    from services.higgsfield_prompt import VideoPromptGenerator

    vgen = VideoPromptGenerator()
    try:
        project.video_prompts = vgen.generate(
            genre=source.genre,
            style=source.style or "",
            mood_tags=source.mood_tags or None,
        )
    except Exception as e:
        logger.warning("Clone video prompt generation failed: %s", e)

    project.save()
    return _serialize(project)


@app.get("/api/projects")
async def list_projects():
    return [_serialize(p) for p in Project.list_all()]


@app.get("/api/projects/{pid}")
async def get_project(pid: str):
    return _serialize(_load(pid))


class UpdateRequest(BaseModel):
    style: str | None = None
    mood_tags: list[str] | None = None
    motif_tags: list[str] | None = None
    notes: str | None = None
    title_lock: str | None = None


@app.patch("/api/projects/{pid}")
async def update_project(pid: str, req: UpdateRequest):
    from services.tags import clean_motifs, validate_moods

    p = _load(pid)
    if req.style is not None:
        p.style = req.style
    if req.mood_tags is not None:
        p.mood_tags = validate_moods(req.mood_tags)
    if req.motif_tags is not None:
        p.motif_tags = clean_motifs(req.motif_tags)
    if req.notes is not None:
        p.notes = req.notes
    if req.title_lock is not None:
        p.title_lock = req.title_lock or None
    p.save()
    return _serialize(p)


REF_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


@app.post("/api/projects/{pid}/refs")
async def upload_refs(pid: str, files: list[UploadFile] = File(...)):
    project = _load(pid)
    refs_dir = project.project_dir / "refs"
    refs_dir.mkdir(exist_ok=True)

    saved = []
    for f in files:
        suffix = Path(f.filename).suffix.lower()
        if suffix not in REF_EXTS:
            continue
        safe_name = _safe_filename(f.filename)
        dst = refs_dir / safe_name
        # Avoid name collision
        n = 1
        while dst.exists():
            dst = refs_dir / f"{Path(safe_name).stem}_{n}{suffix}"
            n += 1
        with open(dst, "wb") as out:
            shutil.copyfileobj(f.file, out)
        saved.append(dst.name)

    project.visual_refs = list(project.visual_refs or [])
    project.visual_refs.extend(saved)
    project.save()
    return _serialize(project)


@app.get("/api/projects/{pid}/refs/{filename}")
async def get_ref(pid: str, filename: str):
    project = _load(pid)
    path = project.project_dir / "refs" / filename
    if not path.exists() or ".." in filename:
        raise HTTPException(404, "Ref not found")
    return FileResponse(path)


@app.delete("/api/projects/{pid}/refs/{filename}")
async def delete_ref(pid: str, filename: str):
    project = _load(pid)
    if ".." in filename:
        raise HTTPException(400, "Invalid filename")
    path = project.project_dir / "refs" / filename
    if path.exists():
        path.unlink()
    project.visual_refs = [r for r in (project.visual_refs or []) if r != filename]
    project.save()
    return _serialize(project)


@app.delete("/api/projects/{pid}")
async def delete_project(pid: str):
    p = _load(pid)
    try:
        shutil.rmtree(p.project_dir)
    except PermissionError:
        # Windows: 열린 파일이 있으면 재시도
        import asyncio
        import gc
        gc.collect()
        await asyncio.sleep(0.5)
        shutil.rmtree(p.project_dir, ignore_errors=True)
    return {"ok": True}


@app.post("/api/projects/{pid}/music")
async def upload_music(pid: str, file: UploadFile = File(...)):
    from services.beat_analyzer import BeatAnalyzer

    project = _load(pid)

    music_dir = project.project_dir / "music"
    music_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(file.filename)
    dst = music_dir / safe_name
    with open(dst, "wb") as f:
        shutil.copyfileobj(file.file, f)

    project.music_file = safe_name

    analyzer = BeatAnalyzer()
    try:
        analysis = analyzer.analyze(dst)
    except Exception as e:
        raise HTTPException(500, f"Beat analysis failed: {e}")

    project.bpm = analysis["bpm"]
    project.duration_sec = analysis["duration_sec"]
    project.beat_times = analysis["beat_times"]

    # Shorts 60초 제한: 초과 시 트리밍 + fade out 2초
    trim = analyzer.trim_for_shorts(project.beat_times, project.duration_sec)
    if trim["trimmed"]:
        project.beat_times = trim["beat_times"]
        project.duration_sec = trim["duration_sec"]
    project.config["fade_out_sec"] = trim["fade_out_sec"]

    bps = analyzer.suggest_beats_per_scene(project.bpm, project.duration_sec)
    scenes = analyzer.split_scenes(
        project.beat_times, project.duration_sec, beats_per_scene=bps
    )
    project.scenes = scenes

    project.update_status("music_registered", step_name="music")
    project.save()
    return _serialize(project)


@app.post("/api/projects/{pid}/metadata")
async def generate_metadata(pid: str):
    from services.metadata import MetadataGenerator

    project = _load(pid)

    meta_gen = MetadataGenerator()
    title_hint = (
        project.title_lock
        or (project.suno_prompt.get("title_suggestion", "") if project.suno_prompt else "")
        or (project.metadata.get("title", "") if project.metadata else "")
    )
    try:
        project.metadata = meta_gen.generate(
            genre=project.genre,
            title_suggestion=title_hint,
            lyrics=project.lyrics,
            instrumental=project.instrumental,
            substyle=project.suno_prompt.get("substyle") if project.suno_prompt else None,
        )
    except LLMError as e:
        raise HTTPException(503, f"LLM backend unavailable: {e}")
    except Exception as e:
        raise HTTPException(500, f"Metadata generation failed: {e}")

    project.save()
    return _serialize(project)


@app.post("/api/projects/{pid}/prompts")
async def generate_prompts(pid: str):
    from services.prompt_generator import PromptGenerator

    project = _load(pid)
    if not project.scenes:
        raise HTTPException(400, "No scenes. Upload music first.")

    gen = PromptGenerator()
    try:
        project.scenes = gen.generate(
            genre=project.genre,
            scenes=project.scenes,
            lyrics=project.lyrics,
            instrumental=project.instrumental,
            suno_prompt=project.suno_prompt,
            style=project.style,
        )
    except LLMError as e:
        raise HTTPException(503, f"LLM backend unavailable: {e}")
    except Exception as e:
        raise HTTPException(500, f"Prompt generation failed: {e}")

    project.update_status("prompts_done", step_name="prompts")
    project.save()
    return _serialize(project)


@app.post("/api/projects/{pid}/assets")
async def upload_assets(pid: str, files: list[UploadFile] = File(...)):
    project = _load(pid)
    assets_dir = project.project_dir / "assets"
    exts = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov"}

    # Find scenes without assets
    empty_scene_ids = []
    for s in project.scenes:
        sid = s["id"]
        has_asset = any(
            (assets_dir / f"scene_{sid:02d}{ext}").exists() for ext in exts
        )
        if not has_asset:
            empty_scene_ids.append(sid)

    uploaded = []
    for f, sid in zip(files, empty_scene_ids):
        suffix = Path(f.filename).suffix.lower()
        dst = assets_dir / f"scene_{sid:02d}{suffix}"
        with open(dst, "wb") as out:
            shutil.copyfileobj(f.file, out)
        uploaded.append(dst.name)

    return {"uploaded": uploaded, "remaining": len(empty_scene_ids) - len(uploaded)}


@app.get("/api/projects/{pid}/assets-status")
async def assets_status(pid: str):
    project = _load(pid)
    assets_dir = project.project_dir / "assets"
    exts = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov"}

    result = []
    for s in project.scenes:
        sid = s["id"]
        found = None
        for ext in sorted(exts):
            candidate = assets_dir / f"scene_{sid:02d}{ext}"
            if candidate.exists():
                found = candidate.name
                break
        result.append({"id": sid, "has_asset": found is not None, "filename": found})

    return {"scenes": result}


class ComposeRequest(BaseModel):
    bounce: bool = False


@app.post("/api/projects/{pid}/compose")
async def compose_video(pid: str, req: ComposeRequest | None = None):
    from services.composer import ShortsComposer

    project = _load(pid)
    if not project.music_file:
        raise HTTPException(400, "No music file.")

    bounce = req.bounce if req else False
    composer = ShortsComposer()
    fade_out = project.config.get("fade_out_sec", 0.0)

    # Determine title: title_lock > metadata > suno_prompt > genre
    title = None
    if project.title_lock:
        title = project.title_lock
    elif project.metadata:
        title = project.metadata.get("title")
    if not title and project.suno_prompt:
        title = project.suno_prompt.get("title_suggestion")
    if not title:
        title = project.genre

    try:
        composer.compose_full(
            project_dir=project.project_dir,
            scenes=project.scenes,
            music_file=project.music_file,
            fade_out_sec=fade_out,
            title=title,
            title_card_config=project.config.get("title_card"),
            bounce=bounce,
        )
    except FileNotFoundError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Compose failed: {e}")

    if not project.metadata:
        from services.metadata import MetadataGenerator

        meta_gen = MetadataGenerator()
        title_hint = (
            project.title_lock
            or (project.suno_prompt.get("title_suggestion", "") if project.suno_prompt else "")
        )
        try:
            project.metadata = meta_gen.generate(
                genre=project.genre,
                title_suggestion=title_hint,
                lyrics=project.lyrics,
                instrumental=project.instrumental,
                substyle=project.suno_prompt.get("substyle") if project.suno_prompt else None,
            )
        except Exception as e:
            logger.warning("Metadata fallback generation failed: %s", e)

    project.update_status("composed", step_name="compose")
    project.save()
    return _serialize(project)


@app.get("/api/projects/{pid}/download")
async def download_video(pid: str):
    project = _load(pid)
    finals = list((project.project_dir / "output").glob("*_shorts.mp4"))
    if not finals:
        raise HTTPException(404, "No output video")
    return FileResponse(finals[0], media_type="video/mp4", filename=finals[0].name)


# --- Beat Marker Export ---


def _format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


@app.get("/api/projects/{pid}/beat-markers.srt")
async def beat_markers_srt(pid: str):
    """비트 타임스탬프를 SRT 자막으로 내보내기 (CapCut import용)"""
    from fastapi.responses import Response

    project = _load(pid)
    if not project.beat_times:
        raise HTTPException(400, "No beat data. Upload music first.")

    srt_lines = []
    marker_dur = 0.1  # each marker shows for 100ms

    for i, t in enumerate(project.beat_times):
        idx = i + 1
        start = _format_srt_time(t)
        end = _format_srt_time(t + marker_dur)
        srt_lines.append(f"{idx}\n{start} --> {end}\n●  Beat {idx}\n")

    # Add scene cut markers if scenes exist
    if project.scenes:
        for s in project.scenes:
            idx = len(project.beat_times) + s["id"]
            start = _format_srt_time(s["start_sec"])
            end = _format_srt_time(s["start_sec"] + 0.5)
            srt_lines.append(f"{idx}\n{start} --> {end}\n▶ CUT {s['id']}\n")

    srt_content = "\n".join(srt_lines)
    filename = f"{project.id}_beats.srt"
    return Response(
        content=srt_content,
        media_type="text/srt",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/projects/{pid}/beat-markers.json")
async def beat_markers_json(pid: str):
    """비트 + 씬 데이터를 JSON으로 내보내기"""
    project = _load(pid)
    if not project.beat_times:
        raise HTTPException(400, "No beat data. Upload music first.")

    beats = [{"beat": i + 1, "time_sec": round(t, 3)} for i, t in enumerate(project.beat_times)]
    scenes = [
        {"scene": s["id"], "start_sec": s["start_sec"], "end_sec": s["end_sec"], "beat_count": s["beat_count"]}
        for s in (project.scenes or [])
    ]

    return {
        "project_id": project.id,
        "bpm": project.bpm,
        "duration_sec": project.duration_sec,
        "beats": beats,
        "scenes": scenes,
    }


# --- YouTube Comment API ---


@app.post("/api/projects/{pid}/comment")
async def post_first_comment(pid: str):
    """Post the first_comment from metadata as a comment on the YouTube video."""
    project = _load(pid)
    if not project.youtube_video_id:
        raise HTTPException(400, "No YouTube video linked to this project")
    if not project.metadata or not project.metadata.get("first_comment"):
        raise HTTPException(400, "No first_comment in metadata")

    from services.uploader import YouTubeUploader

    uploader = YouTubeUploader()
    try:
        result = uploader.post_comment(
            video_id=project.youtube_video_id,
            text=project.metadata["first_comment"],
        )
    except FileNotFoundError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Comment posting failed: {e}")

    return {"ok": True, "comment_id": result.get("id")}


# --- YouTube Comment Analysis ---


@app.get("/api/projects/{pid}/comments")
async def analyze_project_comments(pid: str):
    """Fetch and analyze YouTube comments for a project."""
    project = _load(pid)
    if not project.youtube_video_id:
        raise HTTPException(400, "No YouTube video linked")

    from services.comment_analyzer import analyze_comments, fetch_comments

    try:
        comments = fetch_comments(project.youtube_video_id)
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Comment fetch failed: {e}")

    if not comments:
        return {"comment_count": 0, "analysis": None}

    substyle = (project.suno_prompt or {}).get("substyle")
    try:
        analysis = analyze_comments(
            comments=comments,
            genre=project.genre,
            substyle=substyle,
        )
    except Exception as e:
        raise HTTPException(500, f"Comment analysis failed: {e}")

    return {"comment_count": len(comments), "analysis": analysis}


# --- YouTube Sync API ---


@app.post("/api/sync/youtube")
async def sync_youtube():
    from services.youtube_sync import sync_channel

    try:
        result = sync_channel()
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"YouTube sync failed: {e}")

    return result


# --- Genres API ---


@app.get("/api/genres")
async def get_genres():
    """장르별 설정 반환 (default_instrumental 포함)"""
    import json as _json

    genres_path = PROJECTS_DIR.parent / "config" / "genres.json"
    if not genres_path.exists():
        return {}
    data = _json.loads(genres_path.read_text(encoding="utf-8"))
    result = {}
    for name, info in data.get("genres", {}).items():
        result[name] = {"default_instrumental": info.get("default_instrumental", False)}
    # Add shranz default
    shranz = data.get("shranz_default", {})
    for alias in data.get("shranz_aliases", []):
        result[alias] = {"default_instrumental": shranz.get("default_instrumental", True)}
    return result


# --- Tags API ---


@app.get("/api/tags/moods")
async def list_moods():
    from services.tags import MOOD_TAGS

    return [
        {"name": m.name, "label": m.label, "description": m.description}
        for m in MOOD_TAGS
    ]


@app.get("/api/tags/motifs")
async def list_motifs():
    from services.tags import collect_motif_counts

    counts = collect_motif_counts()
    return [
        {"name": k, "count": v}
        for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


# --- Substyles API ---


@app.get("/api/substyles")
async def list_substyles():
    from services.shranz_substyles import SUBSTYLES, get_used_substyles_from_projects

    used = get_used_substyles_from_projects(str(PROJECTS_DIR))
    used_counts: dict[str, int] = {}
    for name in used:
        used_counts[name] = used_counts.get(name, 0) + 1

    return [
        {
            "name": s.name,
            "label": s.label,
            "bpm_range": list(s.bpm_range),
            "mood": s.mood,
            "used_count": used_counts.get(s.name, 0),
        }
        for s in SUBSTYLES
    ]


class BatchRequest(BaseModel):
    substyles: list[str]


@app.post("/api/projects/batch")
async def batch_create(req: BatchRequest):
    """빈 substyle에서 배치 프로젝트 생성"""
    from services.suno_prompt import SunoPromptGenerator
    from services.higgsfield_prompt import VideoPromptGenerator

    created = []
    for substyle_name in req.substyles:
        project = Project.create(genre="shranz", instrumental=True, aspect_ratio="9:16")
        project.update_status("created", step_name="create")

        gen = SunoPromptGenerator(projects_dir=str(PROJECTS_DIR))
        try:
            project.suno_prompt = gen.generate(
                genre="shranz", instrumental=True, substyle=substyle_name,
            )
        except Exception as e:
            logger.warning("Batch suno prompt failed for %s: %s", substyle_name, e)

        vgen = VideoPromptGenerator()
        try:
            project.video_prompts = vgen.generate(genre="shranz", style="")
        except Exception as e:
            logger.warning("Batch video prompt failed: %s", e)

        project.save()
        created.append({"id": project.id, "substyle": substyle_name})

    return {"created": created}


# --- Settings API ---


SETTINGS_KEYS = [
    "ANTHROPIC_API_KEY",
    "YOUTUBE_API_KEY",
    "YOUTUBE_CHANNEL_HANDLE",
    "ARTIST_NAME",
    "LLM_MODE",
]


@app.get("/api/settings")
async def get_settings():
    """현재 설정값 반환 (API 키는 마스킹)"""
    from config import _load_settings, get_setting

    result = {}
    for key in SETTINGS_KEYS:
        val = get_setting(key, "")
        if "KEY" in key and val:
            result[key] = "****..." + val[-2:] if len(val) > 4 else "****"
        else:
            result[key] = val
    return result


class SettingsRequest(BaseModel):
    settings: dict[str, str]


@app.put("/api/settings")
async def save_settings(req: SettingsRequest):
    """설정값 저장 (config/settings.json)"""
    from config import _load_settings, _save_settings

    current = _load_settings()
    for key, val in req.settings.items():
        if key not in SETTINGS_KEYS:
            continue
        # Don't overwrite with masked value
        if "KEY" in key and val and "..." in val:
            continue
        current[key] = val
    _save_settings(current)

    # Reset cached LLM client so new keys/mode take effect
    from services.llm import reset_default_client
    reset_default_client()

    return {"ok": True}


# --- Usage API (M5) ---


@app.get("/api/usage")
async def get_usage():
    """LLM 사용량/비용 집계"""
    import json as _json
    from services.llm import USAGE_LOG_PATH

    records = []
    if USAGE_LOG_PATH.exists():
        for line in USAGE_LOG_PATH.read_text(encoding="utf-8").strip().split("\n"):
            if line.strip():
                records.append(_json.loads(line))

    total_cost = sum(r.get("cost_usd", 0) for r in records)
    total_calls = len(records)
    total_input = sum(r.get("input_tokens", 0) for r in records)
    total_output = sum(r.get("output_tokens", 0) for r in records)

    by_model: dict[str, dict] = {}
    for r in records:
        m = r.get("model", "unknown")
        if m not in by_model:
            by_model[m] = {"calls": 0, "cost_usd": 0, "input_tokens": 0, "output_tokens": 0}
        by_model[m]["calls"] += 1
        by_model[m]["cost_usd"] += r.get("cost_usd", 0)
        by_model[m]["input_tokens"] += r.get("input_tokens", 0)
        by_model[m]["output_tokens"] += r.get("output_tokens", 0)

    recent = records[-10:][::-1]

    return {
        "total_cost": round(total_cost, 4),
        "total_calls": total_calls,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "by_model": by_model,
        "recent": recent,
    }


# --- Analytics API (M6) ---


@app.get("/api/analytics")
async def get_analytics():
    """YouTube 성과 분석 — 장르/substyle별 집계"""
    projects = Project.list_all()

    by_genre: dict[str, dict] = {}
    by_substyle: dict[str, dict] = {}
    top_performers: list[dict] = []

    for p in projects:
        stats = p.youtube_stats or {}
        views = stats.get("views", 0)
        likes = stats.get("likes", 0)
        comments = stats.get("comments", 0)

        genre = p.genre or "unknown"
        if genre not in by_genre:
            by_genre[genre] = {"count": 0, "views": 0, "likes": 0, "comments": 0}
        by_genre[genre]["count"] += 1
        by_genre[genre]["views"] += views
        by_genre[genre]["likes"] += likes
        by_genre[genre]["comments"] += comments

        substyle = (p.suno_prompt or {}).get("substyle")
        if substyle:
            if substyle not in by_substyle:
                by_substyle[substyle] = {"count": 0, "views": 0, "likes": 0, "comments": 0}
            by_substyle[substyle]["count"] += 1
            by_substyle[substyle]["views"] += views
            by_substyle[substyle]["likes"] += likes
            by_substyle[substyle]["comments"] += comments

        if views > 0:
            top_performers.append({
                "id": p.id,
                "title": p.title_lock or (p.metadata or {}).get("title", p.id),
                "genre": genre,
                "substyle": substyle,
                "views": views,
                "likes": likes,
                "comments": comments,
                "engagement": round((likes + comments) / views * 100, 2) if views else 0,
                "aspect_ratio": p.aspect_ratio,
            })

    top_performers.sort(key=lambda x: x["views"], reverse=True)

    # Genre performance ranking
    genre_ranking = sorted(
        [{"genre": g, **d, "avg_views": round(d["views"] / d["count"]) if d["count"] else 0}
         for g, d in by_genre.items()],
        key=lambda x: x["avg_views"],
        reverse=True,
    )

    substyle_ranking = sorted(
        [{"substyle": s, **d, "avg_views": round(d["views"] / d["count"]) if d["count"] else 0}
         for s, d in by_substyle.items()],
        key=lambda x: x["avg_views"],
        reverse=True,
    )

    return {
        "top_performers": top_performers[:20],
        "genre_ranking": genre_ranking,
        "substyle_ranking": substyle_ranking,
    }


# --- Static ---
app.mount("/", StaticFiles(directory="static", html=True), name="static")
