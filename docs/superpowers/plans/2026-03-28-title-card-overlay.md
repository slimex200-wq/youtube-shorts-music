# Title Card Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Suno YouTube Shorts 영상 인트로에 `곡 제목 · Eisenherz` 형태의 시네마틱 타이틀 카드를 ASS 자막으로 렌더링한다.

**Architecture:** 새 `services/title_card.py` 모듈이 ASS 파일 생성을 담당. `ShortsComposer.compose_full()`의 마지막 단계에서 타이틀 카드를 burn-in. Project 모델에 `title_card` 설정 필드 추가.

**Tech Stack:** Python, FFmpeg (ASS subtitle filter), Montserrat font (Google Fonts OFL)

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `services/title_card.py` | ASS 파일 생성 (스타일, 타이밍, 언더라인) |
| Create | `tests/test_title_card.py` | title_card 모듈 단위 테스트 |
| Create | `tests/test_composer_title.py` | composer 타이틀 카드 통합 테스트 |
| Create | `assets/fonts/Montserrat-SemiBold.ttf` | 폰트 파일 |
| Modify | `services/composer.py:179-243` | add_title_card(), compose_full() 통합 |
| Modify | `models/project.py:23-43` | title_card 필드 추가 |
| Modify | `cli.py:17-54` | --artist 옵션 추가 |

---

### Task 1: Montserrat 폰트 다운로드

**Files:**
- Create: `assets/fonts/Montserrat-SemiBold.ttf`

- [ ] **Step 1: fonts 디렉토리 생성 및 폰트 다운로드**

```bash
mkdir -p assets/fonts
curl -L -o assets/fonts/Montserrat-SemiBold.ttf \
  "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-SemiBold.ttf"
```

- [ ] **Step 2: 파일 존재 확인**

```bash
ls -la assets/fonts/Montserrat-SemiBold.ttf
# Expected: 파일 크기 > 0 (약 100KB+)
```

- [ ] **Step 3: .gitignore에 폰트 제외되지 않았는지 확인**

```bash
git check-ignore assets/fonts/Montserrat-SemiBold.ttf
# Expected: 출력 없음 (무시되지 않음)
```

- [ ] **Step 4: Commit**

```bash
git add assets/fonts/Montserrat-SemiBold.ttf
git commit -m "chore: add Montserrat SemiBold font for title card overlay"
```

---

### Task 2: TitleCardGenerator 테스트 작성

**Files:**
- Create: `tests/test_title_card.py`

- [ ] **Step 1: 테스트 파일 생성**

```python
"""services/title_card.py 단위 테스트"""
from pathlib import Path

from services.title_card import TitleCardGenerator


class TestTitleCardGenerator:
    def test_generate_ass_contains_script_info(self, tmp_path: Path):
        gen = TitleCardGenerator()
        ass_path = gen.generate(
            title="MIDNIGHT ACID",
            artist_name="Eisenherz",
            output_dir=tmp_path,
        )
        content = ass_path.read_text(encoding="utf-8")
        assert "[Script Info]" in content
        assert "PlayResX: 1080" in content
        assert "PlayResY: 1920" in content

    def test_generate_ass_contains_title_dialogue(self, tmp_path: Path):
        gen = TitleCardGenerator()
        ass_path = gen.generate(
            title="DARK TRAP",
            artist_name="Eisenherz",
            output_dir=tmp_path,
        )
        content = ass_path.read_text(encoding="utf-8")
        assert "DARK TRAP" in content
        assert "EISENHERZ" in content
        # middle dot separator
        assert "\u00b7" in content or "·" in content

    def test_generate_ass_contains_fade(self, tmp_path: Path):
        gen = TitleCardGenerator()
        ass_path = gen.generate(
            title="TEST",
            artist_name="Eisenherz",
            output_dir=tmp_path,
            fade_in_ms=800,
            fade_out_ms=800,
        )
        content = ass_path.read_text(encoding="utf-8")
        assert "\\fad(800,800)" in content

    def test_generate_ass_custom_timing(self, tmp_path: Path):
        gen = TitleCardGenerator()
        ass_path = gen.generate(
            title="TEST",
            artist_name="Eisenherz",
            output_dir=tmp_path,
            start_sec=1.0,
            duration_sec=5,
        )
        content = ass_path.read_text(encoding="utf-8")
        # start at 1.0s
        assert "0:00:01.00" in content
        # end at 6.0s (1.0 + 5)
        assert "0:00:06.00" in content

    def test_generate_ass_uppercase_title(self, tmp_path: Path):
        gen = TitleCardGenerator()
        ass_path = gen.generate(
            title="midnight acid",
            artist_name="eisenherz",
            output_dir=tmp_path,
        )
        content = ass_path.read_text(encoding="utf-8")
        assert "MIDNIGHT ACID" in content
        assert "EISENHERZ" in content

    def test_generate_ass_underline_drawing(self, tmp_path: Path):
        gen = TitleCardGenerator()
        ass_path = gen.generate(
            title="TEST",
            artist_name="Eisenherz",
            output_dir=tmp_path,
        )
        content = ass_path.read_text(encoding="utf-8")
        # ASS drawing mode marker
        assert "\\p1" in content
        # underline delayed start
        assert "0:00:00.80" in content

    def test_generate_ass_output_filename(self, tmp_path: Path):
        gen = TitleCardGenerator()
        ass_path = gen.generate(
            title="TEST",
            artist_name="Eisenherz",
            output_dir=tmp_path,
        )
        assert ass_path.name == "title_card.ass"
        assert ass_path.parent == tmp_path

    def test_format_ass_time(self):
        gen = TitleCardGenerator()
        assert gen._format_ass_time(0.0) == "0:00:00.00"
        assert gen._format_ass_time(0.5) == "0:00:00.50"
        assert gen._format_ass_time(65.3) == "0:01:05.30"
        assert gen._format_ass_time(3661.5) == "1:01:01.50"
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
cd C:/Users/slime/claude-projects/youtube-shorts-music
python -m pytest tests/test_title_card.py -v
```

Expected: `ModuleNotFoundError: No module named 'services.title_card'`

- [ ] **Step 3: Commit**

```bash
git add tests/test_title_card.py
git commit -m "test: add title card generator unit tests (RED)"
```

---

### Task 3: TitleCardGenerator 구현

**Files:**
- Create: `services/title_card.py`

- [ ] **Step 1: 구현 파일 생성**

```python
"""ASS 자막 기반 타이틀 카드 생성기"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ASS 색상: &HAABBGGRR (Alpha, Blue, Green, Red)
_WHITE = "&H00FFFFFF"
_BLACK = "&H00000000"
_BG_SEMI = "&H80000000"
_TRANSPARENT = "&HFF000000"

# 언더라인 alpha: 30% opacity → 70% alpha → 0xB3
_UNDERLINE_ALPHA = "&HB3&"

# 글자당 예상 폭 (Montserrat SemiBold 28pt, 1080p 기준)
_CHAR_WIDTH_PX = 18


class TitleCardGenerator:
    """Shorts 영상 인트로에 들어갈 타이틀 카드 ASS 파일 생성"""

    def generate(
        self,
        title: str,
        artist_name: str,
        output_dir: Path,
        start_sec: float = 0.5,
        duration_sec: int = 4,
        fade_in_ms: int = 800,
        fade_out_ms: int = 800,
    ) -> Path:
        title_upper = title.upper()
        artist_upper = artist_name.upper()
        display_text = f"{title_upper} \u00b7 {artist_upper}"

        end_sec = start_sec + duration_sec
        underline_start = start_sec + 0.3
        underline_end = end_sec - 0.3
        underline_width = len(display_text) * _CHAR_WIDTH_PX

        # MarginV for underline: title is at MarginV=60 from bottom,
        # font ~28px, so underline at ~1920 - 60 + 2 = 1862
        underline_y = 1920 - 60 + 2

        content = (
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            "PlayResX: 1080\n"
            "PlayResY: 1920\n"
            "\n"
            "[V4+ Styles]\n"
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,"
            "OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,"
            "ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
            "Alignment,MarginL,MarginR,MarginV,Encoding\n"
            f"Style: TitleCard,Montserrat SemiBold,28,{_WHITE},{_WHITE},"
            f"{_BLACK},{_BG_SEMI},-1,0,0,0,100,100,2,0,1,2,0,1,20,0,60,1\n"
            f"Style: Underline,Montserrat SemiBold,28,{_WHITE},{_WHITE},"
            f"{_TRANSPARENT},{_TRANSPARENT},0,0,0,0,100,100,0,0,1,0,0,1,20,0,60,1\n"
            "\n"
            "[Events]\n"
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
            f"Dialogue: 0,{self._format_ass_time(start_sec)},"
            f"{self._format_ass_time(end_sec)},TitleCard,,20,0,60,,"
            f"{{\\fad({fade_in_ms},{fade_out_ms})}}{display_text}\n"
            f"Dialogue: 1,{self._format_ass_time(underline_start)},"
            f"{self._format_ass_time(underline_end)},Underline,,0,0,0,,"
            f"{{\\fad({fade_in_ms - 200},{fade_out_ms - 200})"
            f"\\pos(20,{underline_y})\\p1"
            f"\\1a{_UNDERLINE_ALPHA}\\3a&HFF&}}"
            f"m 0 0 l {underline_width} 0 l {underline_width} 1 l 0 1"
            "{\\p0}\n"
        )

        output_path = output_dir / "title_card.ass"
        output_path.write_text(content, encoding="utf-8")
        logger.info("타이틀 카드 ASS 생성: %s", output_path)
        return output_path

    @staticmethod
    def _format_ass_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds % 1) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
```

- [ ] **Step 2: 테스트 실행 → 통과 확인**

```bash
cd C:/Users/slime/claude-projects/youtube-shorts-music
python -m pytest tests/test_title_card.py -v
```

Expected: 8 passed

- [ ] **Step 3: Commit**

```bash
git add services/title_card.py
git commit -m "feat: add TitleCardGenerator for ASS subtitle title cards"
```

---

### Task 4: Project 모델에 title_card 필드 추가 (테스트 → 구현)

**Files:**
- Create: `tests/test_project_title_card.py`
- Modify: `models/project.py:23-43`

- [ ] **Step 1: 테스트 작성**

```python
"""Project 모델 title_card 필드 테스트"""
import json
from pathlib import Path

from models.project import Project


def test_project_default_title_card(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("models.project.PROJECTS_DIR", tmp_path)
    project = Project.create(genre="lo-fi", base_dir=tmp_path)
    assert project.config["title_card"]["enabled"] is True
    assert project.config["title_card"]["artist_name"] == "Eisenherz"


def test_project_title_card_persists(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("models.project.PROJECTS_DIR", tmp_path)
    project = Project.create(genre="ambient", base_dir=tmp_path)
    project.config["title_card"]["artist_name"] = "CustomArtist"
    project.save()

    loaded = Project.load(project.id, base_dir=tmp_path)
    assert loaded.config["title_card"]["artist_name"] == "CustomArtist"


def test_project_title_card_custom_values(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("models.project.PROJECTS_DIR", tmp_path)
    project = Project.create(genre="techno", base_dir=tmp_path)
    tc = project.config["title_card"]
    assert tc["fade_in_ms"] == 800
    assert tc["fade_out_ms"] == 800
    assert tc["duration_sec"] == 4
    assert tc["start_sec"] == 0.5
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
python -m pytest tests/test_project_title_card.py -v
```

Expected: FAIL — `KeyError: 'title_card'`

- [ ] **Step 3: models/project.py 수정 — config 기본값에 title_card 추가**

`models/project.py`의 `config` 필드 기본값을 수정:

```python
    config: dict = field(default_factory=lambda: {
        "upload_privacy": "private",
        "title_card": {
            "enabled": True,
            "artist_name": "Eisenherz",
            "fade_in_ms": 800,
            "fade_out_ms": 800,
            "duration_sec": 4,
            "start_sec": 0.5,
        },
    })
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

```bash
python -m pytest tests/test_project_title_card.py -v
```

Expected: 3 passed

- [ ] **Step 5: 기존 테스트 깨지지 않았는지 확인**

```bash
python -m pytest tests/ -v
```

Expected: 전체 통과

- [ ] **Step 6: Commit**

```bash
git add models/project.py tests/test_project_title_card.py
git commit -m "feat: add title_card config to Project model with defaults"
```

---

### Task 5: composer에 타이틀 카드 통합 (테스트 → 구현)

**Files:**
- Create: `tests/test_composer_title.py`
- Modify: `services/composer.py:179-243`

- [ ] **Step 1: 통합 테스트 작성**

```python
"""composer 타이틀 카드 통합 테스트 (FFmpeg 없이 ASS 생성만 검증)"""
from pathlib import Path
from unittest.mock import patch, MagicMock

from services.composer import ShortsComposer


class TestComposerTitleCard:
    def test_add_title_card_generates_ass(self, tmp_path: Path):
        """타이틀 카드 ASS 파일이 생성되는지 확인"""
        composer = ShortsComposer()

        # 더미 입력 영상
        video_path = tmp_path / "input.mp4"
        video_path.write_bytes(b"fake")
        output_path = tmp_path / "output.mp4"
        fonts_dir = tmp_path / "fonts"
        fonts_dir.mkdir()

        title_card_config = {
            "enabled": True,
            "artist_name": "Eisenherz",
            "fade_in_ms": 800,
            "fade_out_ms": 800,
            "duration_sec": 4,
            "start_sec": 0.5,
        }

        # FFmpeg 호출은 mock
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            composer.add_title_card(
                video_path=video_path,
                output_path=output_path,
                title="Midnight Acid",
                title_card_config=title_card_config,
                fonts_dir=fonts_dir,
            )

        # ASS 파일이 생성되었는지
        ass_files = list(tmp_path.glob("*.ass"))
        assert len(ass_files) == 1
        content = ass_files[0].read_text(encoding="utf-8")
        assert "MIDNIGHT ACID" in content
        assert "EISENHERZ" in content

    def test_add_title_card_ffmpeg_command(self, tmp_path: Path):
        """FFmpeg 명령에 ass 필터와 fontsdir가 포함되는지 확인"""
        composer = ShortsComposer()

        video_path = tmp_path / "input.mp4"
        video_path.write_bytes(b"fake")
        output_path = tmp_path / "output.mp4"
        fonts_dir = tmp_path / "fonts"
        fonts_dir.mkdir()

        title_card_config = {
            "enabled": True,
            "artist_name": "Eisenherz",
            "fade_in_ms": 800,
            "fade_out_ms": 800,
            "duration_sec": 4,
            "start_sec": 0.5,
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            composer.add_title_card(
                video_path=video_path,
                output_path=output_path,
                title="Test Song",
                title_card_config=title_card_config,
                fonts_dir=fonts_dir,
            )

        cmd = mock_run.call_args[0][0]
        cmd_str = " ".join(cmd)
        assert "ass=" in cmd_str
        assert "fontsdir=" in cmd_str

    def test_add_title_card_disabled_skips(self, tmp_path: Path):
        """title_card.enabled=False면 스킵"""
        composer = ShortsComposer()

        video_path = tmp_path / "input.mp4"
        video_path.write_bytes(b"fake")
        output_path = tmp_path / "output.mp4"

        title_card_config = {"enabled": False}

        with patch("subprocess.run") as mock_run:
            result = composer.add_title_card(
                video_path=video_path,
                output_path=output_path,
                title="Test",
                title_card_config=title_card_config,
                fonts_dir=tmp_path,
            )

        mock_run.assert_not_called()
        assert result == video_path  # 원본 반환
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
python -m pytest tests/test_composer_title.py -v
```

Expected: FAIL — `AttributeError: 'ShortsComposer' object has no attribute 'add_title_card'`

- [ ] **Step 3: composer.py에 add_title_card() 메서드 추가**

`services/composer.py`의 `add_subtitles()` 메서드 아래에 추가:

```python
    def add_title_card(
        self,
        video_path: Path,
        output_path: Path,
        title: str,
        title_card_config: dict,
        fonts_dir: Path,
    ) -> Path:
        """타이틀 카드 ASS 자막 burn-in"""
        if not title_card_config.get("enabled", True):
            return video_path

        from services.title_card import TitleCardGenerator

        gen = TitleCardGenerator()
        ass_path = gen.generate(
            title=title,
            artist_name=title_card_config.get("artist_name", "Eisenherz"),
            output_dir=video_path.parent,
            start_sec=title_card_config.get("start_sec", 0.5),
            duration_sec=title_card_config.get("duration_sec", 4),
            fade_in_ms=title_card_config.get("fade_in_ms", 800),
            fade_out_ms=title_card_config.get("fade_out_ms", 800),
        )

        escaped_ass = self._escape_ffmpeg_path(ass_path)
        escaped_fonts = self._escape_ffmpeg_path(fonts_dir)

        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vf", f"ass={escaped_ass}:fontsdir={escaped_fonts}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy", "-movflags", "+faststart",
            str(output_path),
        ]

        logger.info("타이틀 카드 burn-in: %s", title)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"타이틀 카드 burn-in 에러: {result.stderr[:500]}")
        return output_path
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

```bash
python -m pytest tests/test_composer_title.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add services/composer.py tests/test_composer_title.py
git commit -m "feat: add title card burn-in to ShortsComposer"
```

---

### Task 6: compose_full()에 타이틀 카드 단계 통합

**Files:**
- Modify: `services/composer.py:194-244`

- [ ] **Step 1: compose_full() 수정**

`compose_full()` 메서드의 시그니처에 `title`, `title_card_config`, `fonts_dir` 파라미터를 추가하고, 자막 burn-in 후 타이틀 카드 단계를 삽입.

현재 `compose_full()` 끝 부분 (`srt_content` 분기 이후)을 수정:

```python
    def compose_full(
        self,
        project_dir: Path,
        scenes: list[dict],
        music_file: str,
        fade_out_sec: float = 0.0,
        title: str | None = None,
        title_card_config: dict | None = None,
    ) -> Path:
        """전체 파이프라인: 씬 렌더 → concat → 오디오 트리밍/fade out → 음악 합치기 → (자막) → (타이틀 카드)"""
        assets_dir = project_dir / "assets"
        music_path = project_dir / "music" / music_file
        output_dir = project_dir / "output"
        output_dir.mkdir(exist_ok=True)

        scenes = self.match_assets(scenes, assets_dir)

        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)

            clips = []
            for scene in scenes:
                clip = self.compose_scene(scene, assets_dir, work_dir)
                clips.append(clip)

            concat_path = work_dir / "concat.mp4"
            self.concat_clips(clips, concat_path)

            # 오디오 트리밍 + fade out
            if fade_out_sec > 0:
                total_duration = scenes[-1]["end_sec"]
                trimmed_audio = work_dir / "audio_trimmed.aac"
                self.trim_audio(music_path, total_duration, fade_out_sec, trimmed_audio)
                audio_for_merge = trimmed_audio
            else:
                audio_for_merge = music_path

            merged_path = work_dir / "merged.mp4"
            self.merge_audio(concat_path, audio_for_merge, merged_path)

            # 자막 처리
            srt_content = self.generate_lyrics_srt(scenes)
            if srt_content:
                srt_path = work_dir / "lyrics.srt"
                srt_path.write_text(srt_content, encoding="utf-8")
                subtitled_path = work_dir / "subtitled.mp4"
                self.add_subtitles(merged_path, srt_path, subtitled_path)
                current_video = subtitled_path
            else:
                current_video = merged_path

            # 타이틀 카드 처리
            project_id = project_dir.name
            final_path = output_dir / f"{project_id}_shorts.mp4"
            tc_config = title_card_config or {}

            if title and tc_config.get("enabled", False):
                fonts_dir = project_dir / "assets" / "fonts"
                if not fonts_dir.exists():
                    # fallback: 프로젝트 루트의 assets/fonts
                    fonts_dir = Path(__file__).parent.parent / "assets" / "fonts"

                self.add_title_card(
                    video_path=current_video,
                    output_path=final_path,
                    title=title,
                    title_card_config=tc_config,
                    fonts_dir=fonts_dir,
                )
            else:
                import shutil
                shutil.copy2(current_video, final_path)

        return final_path
```

- [ ] **Step 2: 기존 테스트 통과 확인**

```bash
python -m pytest tests/ -v
```

Expected: 전체 통과 (기존 compose 호출은 title=None이므로 이전 동작 유지)

- [ ] **Step 3: Commit**

```bash
git add services/composer.py
git commit -m "feat: integrate title card into compose_full pipeline"
```

---

### Task 7: CLI --artist 옵션 추가 (테스트 → 구현)

**Files:**
- Modify: `cli.py:17-54`
- Modify: `cli.py:170-228`

- [ ] **Step 1: CLI 테스트 추가**

`tests/test_cli.py` 끝에 추가:

```python
def test_create_with_artist(tmp_path, monkeypatch):
    """--artist 옵션이 title_card.artist_name에 저장되는지"""
    monkeypatch.setattr("cli.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr("models.project.PROJECTS_DIR", tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["create", "--genre", "techno", "--artist", "TestArtist"])
    assert result.exit_code == 0

    dirs = list(tmp_path.iterdir())
    data = json.loads((dirs[0] / "project.json").read_text(encoding="utf-8"))
    assert data["config"]["title_card"]["artist_name"] == "TestArtist"


def test_create_default_artist(tmp_path, monkeypatch):
    """--artist 없으면 기본값 Eisenherz"""
    monkeypatch.setattr("cli.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr("models.project.PROJECTS_DIR", tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["create", "--genre", "lo-fi"])
    assert result.exit_code == 0

    dirs = list(tmp_path.iterdir())
    data = json.loads((dirs[0] / "project.json").read_text(encoding="utf-8"))
    assert data["config"]["title_card"]["artist_name"] == "Eisenherz"
```

- [ ] **Step 2: 테스트 실행 → test_create_with_artist 실패 확인**

```bash
python -m pytest tests/test_cli.py::test_create_with_artist -v
```

Expected: FAIL — `no such option: --artist`

- [ ] **Step 3: cli.py create 명령에 --artist 옵션 추가**

`cli.py`의 `create` 함수를 수정:

```python
@cli.command()
@click.option("--genre", required=True, help="음악 장르 (예: lo-fi hip hop, dark trap, shranz)")
@click.option("--style", default=None, help="비주얼 아트 스타일 (예: anime, cyberpunk, retro)")
@click.option("--instrumental", is_flag=True, help="인스트루멘탈 (가사 없음)")
@click.option("--lyrics", default=None, help="가사 텍스트")
@click.option("--bpm", type=int, default=None, help="원하는 BPM")
@click.option("--mood", default=None, help="분위기 (예: aggressive, dreamy)")
@click.option("--artist", default=None, help="아티스트명 (기본: Eisenherz)")
def create(genre, style, instrumental, lyrics, bpm, mood, artist):
```

그리고 `project.save()` 직전에:

```python
    if artist:
        project.config["title_card"]["artist_name"] = artist
```

- [ ] **Step 4: compose 명령에서 title 전달하도록 수정**

`cli.py`의 `compose` 함수에서 `composer.compose_full()` 호출 시 title과 title_card_config 전달:

```python
    try:
        # 제목 결정: metadata > suno_prompt > genre
        title = None
        if project.metadata:
            title = project.metadata.get("title")
        if not title and project.suno_prompt:
            title = project.suno_prompt.get("title_suggestion")
        if not title:
            title = project.genre

        final_path = composer.compose_full(
            project_dir=project.project_dir,
            scenes=project.scenes,
            music_file=project.music_file,
            fade_out_sec=fade_out,
            title=title,
            title_card_config=project.config.get("title_card"),
        )
```

- [ ] **Step 5: 테스트 실행 → 전체 통과 확인**

```bash
python -m pytest tests/ -v
```

Expected: 전체 통과

- [ ] **Step 6: Commit**

```bash
git add cli.py tests/test_cli.py
git commit -m "feat: add --artist CLI option and title card config to compose"
```

---

### Task 8: 전체 통합 검증

**Files:** (수정 없음, 검증만)

- [ ] **Step 1: 전체 테스트 실행**

```bash
cd C:/Users/slime/claude-projects/youtube-shorts-music
python -m pytest tests/ -v --tb=short
```

Expected: 전체 통과 (기존 + 새 테스트)

- [ ] **Step 2: 수동 스모크 테스트 (프로젝트가 있으면)**

기존 프로젝트가 있다면:

```bash
python cli.py compose <existing_project_id>
```

Expected: `output/` 디렉토리에 `_shorts.mp4` 생성, 인트로에 타이틀 카드 표시

- [ ] **Step 3: Final commit (필요 시)**

```bash
git add -A
git commit -m "chore: title card overlay feature complete"
```
