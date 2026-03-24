import json
import random
import re
import string
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config import PROJECTS_DIR


def _slugify(text: str, max_len: int = 20) -> str:
    slug = re.sub(r"[^\w]", "-", text).strip("-")
    return slug[:max_len].rstrip("-")


def _random_suffix(length: int = 4) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


@dataclass
class Project:
    id: str
    genre: str
    status: str = "created"
    created_at: str = ""
    steps_completed: list = field(default_factory=list)
    instrumental: bool = False
    lyrics: Optional[str] = None
    suno_prompt: Optional[dict] = None
    music_file: Optional[str] = None
    bpm: Optional[float] = None
    duration_sec: Optional[float] = None
    beat_times: Optional[list] = None
    scenes: list = field(default_factory=list)
    metadata: Optional[dict] = None
    config: dict = field(default_factory=lambda: {
        "upload_privacy": "private",
    })
    last_error: Optional[dict] = None
    _base_dir: Path = field(default=PROJECTS_DIR, repr=False)

    @classmethod
    def create(
        cls,
        genre: str,
        base_dir: Path = None,
        instrumental: bool = False,
        lyrics: str = None,
    ) -> "Project":
        base = base_dir or PROJECTS_DIR
        now = datetime.now(timezone.utc)
        project_id = f"{_slugify(genre)}-{now.strftime('%Y%m%d')}-{_random_suffix()}"
        project = cls(
            id=project_id,
            genre=genre,
            instrumental=instrumental,
            lyrics=lyrics,
            created_at=now.isoformat(),
            _base_dir=base,
        )
        project_dir = base / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "assets").mkdir(exist_ok=True)
        (project_dir / "music").mkdir(exist_ok=True)
        (project_dir / "output").mkdir(exist_ok=True)
        project.save()
        return project

    @classmethod
    def load(cls, project_id: str, base_dir: Path = None) -> "Project":
        base = base_dir or PROJECTS_DIR
        path = base / project_id / "project.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_base_dir"] = base
        return cls(**data)

    @classmethod
    def list_all(cls, base_dir: Path = None) -> list["Project"]:
        base = base_dir or PROJECTS_DIR
        if not base.exists():
            return []
        projects = []
        for d in sorted(base.iterdir()):
            pj = d / "project.json"
            if pj.exists():
                projects.append(cls.load(d.name, base_dir=base))
        return projects

    def save(self):
        data = asdict(self)
        data.pop("_base_dir", None)
        path = self._base_dir / self.id / "project.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def update_status(self, new_status: str, step_name: str = None):
        self.status = new_status
        step = step_name or new_status
        if step not in self.steps_completed:
            self.steps_completed.append(step)
        self.last_error = None

    def set_error(self, step: str, message: str):
        self.last_error = {
            "step": step,
            "message": message,
            "at": datetime.now(timezone.utc).isoformat(),
        }

    @property
    def project_dir(self) -> Path:
        return self._base_dir / self.id
