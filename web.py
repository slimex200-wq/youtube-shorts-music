"""YouTube Shorts Music -- Web API"""
import shutil
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import Config, PROJECTS_DIR
from models.project import Project

app = FastAPI(title="YouTube Shorts Music")


class CreateRequest(BaseModel):
    genre: str
    style: str | None = None
    instrumental: bool = False
    lyrics: str | None = None
    bpm: int | None = None
    mood: str | None = None


def _serialize(p: Project) -> dict:
    return {
        "id": p.id,
        "genre": p.genre,
        "style": p.style,
        "status": p.status,
        "steps_completed": p.steps_completed,
        "instrumental": p.instrumental,
        "lyrics": p.lyrics,
        "suno_prompt": p.suno_prompt,
        "music_file": p.music_file,
        "bpm": p.bpm,
        "duration_sec": p.duration_sec,
        "scenes": p.scenes,
        "metadata": p.metadata,
        "last_error": p.last_error,
    }


def _load(pid: str) -> Project:
    try:
        return Project.load(pid)
    except FileNotFoundError:
        raise HTTPException(404, f"Project not found: {pid}")


# --- API ---


@app.post("/api/projects")
async def create_project(req: CreateRequest):
    project = Project.create(
        genre=req.genre, instrumental=req.instrumental, lyrics=req.lyrics, style=req.style
    )
    project.update_status("created", step_name="create")

    cfg = Config.from_env()
    if cfg.anthropic_api_key:
        from services.suno_prompt import SunoPromptGenerator

        gen = SunoPromptGenerator(cfg.anthropic_api_key)
        try:
            project.suno_prompt = gen.generate(
                genre=req.genre,
                bpm=req.bpm,
                mood=req.mood,
                lyrics=req.lyrics,
                instrumental=req.instrumental,
            )
        except Exception:
            pass

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


@app.patch("/api/projects/{pid}")
async def update_project(pid: str, req: UpdateRequest):
    p = _load(pid)
    if req.style is not None:
        p.style = req.style
    p.save()
    return _serialize(p)


@app.delete("/api/projects/{pid}")
async def delete_project(pid: str):
    p = _load(pid)
    shutil.rmtree(p.project_dir)
    return {"ok": True}


@app.post("/api/projects/{pid}/music")
async def upload_music(pid: str, file: UploadFile = File(...)):
    from services.beat_analyzer import BeatAnalyzer

    project = _load(pid)

    dst = project.project_dir / "music" / file.filename
    with open(dst, "wb") as f:
        shutil.copyfileobj(file.file, f)

    project.music_file = file.filename

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


@app.post("/api/projects/{pid}/prompts")
async def generate_prompts(pid: str):
    from services.prompt_generator import PromptGenerator

    cfg = Config.from_env()
    if not cfg.anthropic_api_key:
        raise HTTPException(400, "ANTHROPIC_API_KEY not set")

    project = _load(pid)
    if not project.scenes:
        raise HTTPException(400, "No scenes. Upload music first.")

    gen = PromptGenerator(cfg.anthropic_api_key)
    try:
        project.scenes = gen.generate(
            genre=project.genre,
            scenes=project.scenes,
            lyrics=project.lyrics,
            instrumental=project.instrumental,
            suno_prompt=project.suno_prompt,
            style=project.style,
        )
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


@app.post("/api/projects/{pid}/compose")
async def compose_video(pid: str):
    from services.composer import ShortsComposer

    project = _load(pid)
    if not project.music_file:
        raise HTTPException(400, "No music file.")

    composer = ShortsComposer()
    fade_out = project.config.get("fade_out_sec", 0.0)
    try:
        composer.compose_full(
            project_dir=project.project_dir,
            scenes=project.scenes,
            music_file=project.music_file,
            fade_out_sec=fade_out,
        )
    except FileNotFoundError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Compose failed: {e}")

    cfg = Config.from_env()
    if cfg.anthropic_api_key and not project.metadata:
        from services.metadata import MetadataGenerator

        meta_gen = MetadataGenerator(cfg.anthropic_api_key)
        try:
            project.metadata = meta_gen.generate(
                genre=project.genre,
                title_suggestion=(
                    project.suno_prompt.get("title_suggestion", "")
                    if project.suno_prompt
                    else ""
                ),
                lyrics=project.lyrics,
                instrumental=project.instrumental,
            )
        except Exception:
            pass

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


# --- Static ---
app.mount("/", StaticFiles(directory="static", html=True), name="static")
