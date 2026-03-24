"""YouTube Shorts 9:16 비트 싱크 영상 조립기"""
import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
SUPPORTED_VIDEO_EXTS = {".mp4", ".mov"}
SUPPORTED_EXTS = SUPPORTED_IMAGE_EXTS | SUPPORTED_VIDEO_EXTS

WIDTH = 1080
HEIGHT = 1920


class ShortsComposer:
    def match_assets(self, scenes: list[dict], assets_dir: Path) -> list[dict]:
        missing = []
        for scene in scenes:
            scene_id = scene["id"]
            matched = False
            for ext in sorted(SUPPORTED_EXTS):
                candidate = assets_dir / f"scene_{scene_id:02d}{ext}"
                if candidate.exists():
                    scene["asset_file"] = candidate.name
                    matched = True
                    break
            if not matched:
                missing.append(f"scene_{scene_id:02d}")
        if missing:
            raise FileNotFoundError(
                f"에셋 누락: {', '.join(missing)}\n"
                f"지원 포맷: {', '.join(sorted(SUPPORTED_EXTS))}"
            )
        return scenes

    def get_subtitle_style(self) -> str:
        return (
            "FontSize=42,FontName=Arial,PrimaryColour=&HFFFFFF,"
            "OutlineColour=&H000000,Outline=3,Shadow=1,"
            "Alignment=10,MarginV=400"
        )

    def generate_lyrics_srt(self, scenes: list[dict]) -> str:
        """가사가 있는 씬만 SRT 자막 생성"""
        srt_lines = []
        idx = 1
        for scene in scenes:
            if not scene.get("lyrics_line"):
                continue
            start = self._format_srt_time(scene["start_sec"])
            end = self._format_srt_time(scene["end_sec"])
            srt_lines.append(f"{idx}\n{start} --> {end}\n{scene['lyrics_line']}\n")
            idx += 1
        return "\n".join(srt_lines)

    def build_scene_cmd(
        self, asset_path: Path, duration: float, output_path: Path
    ) -> list[str]:
        """씬 하나의 FFmpeg 명령어 생성 (오디오 없이 비주얼만)"""
        is_video = asset_path.suffix.lower() in SUPPORTED_VIDEO_EXTS
        scale_filter = (
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2"
        )

        if is_video:
            return [
                "ffmpeg", "-y",
                "-i", str(asset_path),
                "-vf", scale_filter,
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-an", "-t", str(duration),
                "-movflags", "+faststart",
                str(output_path),
            ]
        else:
            frames = int(duration * 30)
            zoom = (
                f"zoompan=z='min(zoom+0.0008,1.2)':"
                f"d={frames}:s={WIDTH}x{HEIGHT}:fps=30"
            )
            return [
                "ffmpeg", "-y",
                "-loop", "1", "-i", str(asset_path),
                "-vf", zoom,
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-t", str(duration),
                "-movflags", "+faststart",
                str(output_path),
            ]

    def compose_scene(
        self, scene: dict, assets_dir: Path, work_dir: Path
    ) -> Path:
        """씬 하나를 비주얼 클립으로 렌더링 (오디오 없음)"""
        asset_path = assets_dir / scene["asset_file"]
        output_path = work_dir / f"clip_{scene['id']:02d}.mp4"
        duration = scene["end_sec"] - scene["start_sec"]

        cmd = self.build_scene_cmd(asset_path, duration, output_path)

        logger.info("씬 %d 클립 생성 (%.1f초)", scene["id"], duration)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg 에러 (씬 {scene['id']}): {result.stderr[:500]}")
        return output_path

    def concat_clips(self, clips: list[Path], output_path: Path) -> Path:
        """클립들을 순서대로 합침"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            for clip in clips:
                f.write(f"file '{clip}'\n")
            list_path = f.name

        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-movflags", "+faststart",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        Path(list_path).unlink(missing_ok=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg concat 에러: {result.stderr[:500]}")
        return output_path

    def merge_audio(self, video_path: Path, audio_path: Path, output_path: Path) -> Path:
        """비주얼 영상 + 음악 파일 합치기"""
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path), "-i", str(audio_path),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"오디오 머지 에러: {result.stderr[:500]}")
        return output_path

    def add_subtitles(self, video_path: Path, srt_path: Path, output_path: Path) -> Path:
        """가사 자막 burn-in"""
        style = self.get_subtitle_style()
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vf", f"subtitles={self._escape_ffmpeg_path(srt_path)}:force_style='{style}'",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "copy", "-movflags", "+faststart",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"자막 burn-in 에러: {result.stderr[:500]}")
        return output_path

    def compose_full(self, project_dir: Path, scenes: list[dict], music_file: str) -> Path:
        """전체 파이프라인: 씬 렌더 → concat → 음악 합치기 → (자막)"""
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

            merged_path = work_dir / "merged.mp4"
            self.merge_audio(concat_path, music_path, merged_path)

            srt_content = self.generate_lyrics_srt(scenes)
            project_id = project_dir.name
            final_path = output_dir / f"{project_id}_shorts.mp4"

            if srt_content:
                srt_path = work_dir / "lyrics.srt"
                srt_path.write_text(srt_content, encoding="utf-8")
                self.add_subtitles(merged_path, srt_path, final_path)
            else:
                import shutil
                shutil.copy2(merged_path, final_path)

        return final_path

    @staticmethod
    def _escape_ffmpeg_path(path: Path) -> str:
        s = str(path).replace("\\", "/")
        s = s.replace(":", "\\:")
        return s

    @staticmethod
    def _format_srt_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
