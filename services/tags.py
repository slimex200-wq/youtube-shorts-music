"""Mood tag enum and motif aggregation.

Moods are hard-coded because they anchor the channel's visual direction
and drift would defeat the purpose. Motifs are free-form — new ones
surface as users use them.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from config import PROJECTS_DIR


@dataclass(frozen=True)
class MoodTag:
    name: str
    label: str
    description: str


MOOD_TAGS: tuple[MoodTag, ...] = (
    MoodTag(
        name="crimson",
        label="Crimson Ritual",
        description="빨강 + 폐허, 왕좌, 의식. 피의 의례, 순교, 붉은 제단.",
    ),
    MoodTag(
        name="void",
        label="Void Meditation",
        description="청록 + 우주, 명상, 고독. 무중력, 침묵, 심연에서의 자아.",
    ),
    MoodTag(
        name="frost",
        label="Frost Melancholy",
        description="차가운 블루 + 해골, 고딕. 얼어붙은 슬픔, 겨울의 조용한 종말.",
    ),
    MoodTag(
        name="steel",
        label="Steel Warfare",
        description="회색 + 사이버 솔저, 도시. 철과 콘크리트, 기계화된 갈등.",
    ),
    MoodTag(
        name="ember",
        label="Ember Pilgrim",
        description="주황 + 사막, 순례, 황혼. 재 속의 여정, 마지막 불꽃.",
    ),
    MoodTag(
        name="shadow",
        label="Shadow Cult",
        description="검정 + 의식, 제단, 컬트. 후드, 촛불, 비밀결사.",
    ),
)

MOOD_NAMES: frozenset[str] = frozenset(m.name for m in MOOD_TAGS)


def validate_moods(moods: Iterable[str]) -> list[str]:
    """Drop any mood name that isn't in the enum. Preserves order."""
    seen: set[str] = set()
    out: list[str] = []
    for m in moods:
        if m in MOOD_NAMES and m not in seen:
            out.append(m)
            seen.add(m)
    return out


def clean_motifs(motifs: Iterable[str]) -> list[str]:
    """Trim, lowercase, dedupe free-form motif tags. Preserves order."""
    seen: set[str] = set()
    out: list[str] = []
    for m in motifs:
        norm = (m or "").strip().lower()
        if norm and norm not in seen:
            out.append(norm)
            seen.add(norm)
    return out


def collect_motif_counts(projects_dir: Path | None = None) -> dict[str, int]:
    """Aggregate motif usage across all saved projects for autocomplete."""
    base = projects_dir or PROJECTS_DIR
    counts: dict[str, int] = {}
    if not base.exists():
        return counts

    import json

    for d in base.iterdir():
        pj = d / "project.json"
        if not pj.exists():
            continue
        try:
            data = json.loads(pj.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for tag in data.get("motif_tags", []) or []:
            if isinstance(tag, str) and tag:
                counts[tag] = counts.get(tag, 0) + 1
    return counts
