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
    substyle: str | None = None


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

        gen = SunoPromptGenerator(cfg.anthropic_api_key, projects_dir=str(PROJECTS_DIR))
        try:
            project.suno_prompt = gen.generate(
                genre=req.genre,
                bpm=req.bpm,
                mood=req.mood,
                lyrics=req.lyrics,
                instrumental=req.instrumental,
                substyle=req.substyle,
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
    try:
        shutil.rmtree(p.project_dir)
    except PermissionError:
        # Windows: 열린 파일이 있으면 재시도
        import gc
        import time
        gc.collect()
        time.sleep(0.5)
        shutil.rmtree(p.project_dir, ignore_errors=True)
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


@app.post("/api/projects/{pid}/metadata")
async def generate_metadata(pid: str):
    from services.metadata import MetadataGenerator

    cfg = Config.from_env()
    if not cfg.anthropic_api_key:
        raise HTTPException(400, "ANTHROPIC_API_KEY not set")

    project = _load(pid)

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
            substyle=project.suno_prompt.get("substyle") if project.suno_prompt else None,
        )
    except Exception as e:
        raise HTTPException(500, f"Metadata generation failed: {e}")

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
    try:
        composer.compose_full(
            project_dir=project.project_dir,
            scenes=project.scenes,
            music_file=project.music_file,
            fade_out_sec=fade_out,
            bounce=bounce,
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
                substyle=project.suno_prompt.get("substyle") if project.suno_prompt else None,
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


# --- Editor API ---


@app.post("/api/editor/compose")
async def editor_compose(
    songs: list[UploadFile] = File(...),
    images: list[UploadFile] = File(...),
):
    """이미지 + 음악 → 풀 길이 비디오 (Shorts 제한 없음)"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        songs_dir = tmp / "songs"
        images_dir = tmp / "images"
        output_dir = tmp / "output"
        songs_dir.mkdir()
        images_dir.mkdir()
        output_dir.mkdir()

        for f in songs:
            dst = songs_dir / f.filename
            with open(dst, "wb") as out:
                shutil.copyfileobj(f.file, out)

        for f in images:
            dst = images_dir / f.filename
            with open(dst, "wb") as out:
                shutil.copyfileobj(f.file, out)

        from services.editor import EditorComposer

        composer = EditorComposer()
        try:
            results = composer.compose_all(songs_dir, images_dir, output_dir)
        except FileNotFoundError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            raise HTTPException(500, f"Editor compose failed: {e}")

        # Move results to persistent location
        persist_dir = PROJECTS_DIR / "_editor_output"
        persist_dir.mkdir(parents=True, exist_ok=True)
        output_files = []
        for r in results:
            dst = persist_dir / r.name
            shutil.copy2(r, dst)
            output_files.append(r.name)

    return {"files": output_files}


@app.get("/api/editor/download/{filename}")
async def editor_download(filename: str):
    filepath = PROJECTS_DIR / "_editor_output" / filename
    if not filepath.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(filepath, media_type="video/mp4", filename=filename)


@app.get("/api/editor/files")
async def editor_list_files():
    output_dir = PROJECTS_DIR / "_editor_output"
    if not output_dir.exists():
        return {"files": []}
    files = [f.name for f in sorted(output_dir.iterdir()) if f.suffix == ".mp4"]
    return {"files": files}


# --- Static ---
app.mount("/", StaticFiles(directory="static", html=True), name="static")
