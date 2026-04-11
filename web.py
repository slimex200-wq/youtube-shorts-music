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
        "mood_tags": p.mood_tags,
        "motif_tags": p.motif_tags,
        "visual_refs": p.visual_refs,
        "notes": p.notes,
        "title_lock": p.title_lock,
        "created_at": p.created_at,
        "last_edited_at": p.last_edited_at,
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

    from services.suno_prompt import SunoPromptGenerator

    gen = SunoPromptGenerator(projects_dir=str(PROJECTS_DIR))
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
        dst = refs_dir / f.filename
        # Avoid name collision
        n = 1
        while dst.exists():
            dst = refs_dir / f"{Path(f.filename).stem}_{n}{suffix}"
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

    project = _load(pid)

    meta_gen = MetadataGenerator()
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

    if not project.metadata:
        from services.metadata import MetadataGenerator

        meta_gen = MetadataGenerator()
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
