"""YouTube Shorts 9:16 비트 싱크 영상 조립기"""
import logging
import math
import shutil
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

    def calc_bounce_repeats(self, clip_duration: float, scene_duration: float) -> int:
        """바운스(정+역) 1회 길이 기준으로 씬을 채우는 반복 횟수 계산"""
        bounce_duration = clip_duration * 2
        return max(1, math.ceil(scene_duration / bounce_duration))

    def build_scene_cmd(
        self,
        asset_path: Path,
        duration: float,
        output_path: Path,
        bounce: bool = False,
        asset_duration: float | None = None,
    ) -> list[str]:
        """씬 하나의 FFmpeg 명령어 생성 (오디오 없이 비주얼만)"""
        is_video = asset_path.suffix.lower() in SUPPORTED_VIDEO_EXTS
        scale_filter = (
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2"
        )

        if is_video and bounce and asset_duration:
            repeats = self.calc_bounce_repeats(asset_duration, duration)
            return [
                "ffmpeg", "-y",
                "-stream_loop", str(repeats),
                "-i", str(asset_path),
                "-filter_complex",
                f"[0:v]{scale_filter}[s];[s]reverse[r];[s][r]concat=n=2:v=1:a=0[out]",
                "-map", "[out]",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-preset", "fast", "-crf", "23",
                "-an", "-t", str(duration),
                "-movflags", "+faststart",
                str(output_path),
            ]
        elif is_video:
            return [
                "ffmpeg", "-y",
                "-i", str(asset_path),
                "-vf", scale_filter,
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-preset", "fast", "-crf", "23",
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
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-preset", "fast", "-crf", "23",
                "-t", str(duration),
                "-movflags", "+faststart",
                str(output_path),
            ]

    def _probe_duration(self, path: Path) -> float | None:
        """ffprobe로 영상 길이(초) 조회"""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except (subprocess.TimeoutExpired, ValueError):
            pass
        return None

    def compose_scene(
        self, scene: dict, assets_dir: Path, work_dir: Path, bounce: bool = False
    ) -> Path:
        """씬 하나를 비주얼 클립으로 렌더링 (오디오 없음)"""
        asset_path = assets_dir / scene["asset_file"]
        output_path = work_dir / f"clip_{scene['id']:02d}.mp4"
        duration = scene["end_sec"] - scene["start_sec"]

        asset_duration = None
        if bounce and asset_path.suffix.lower() in SUPPORTED_VIDEO_EXTS:
            asset_duration = self._probe_duration(asset_path)

        cmd = self.build_scene_cmd(
            asset_path, duration, output_path,
            bounce=bounce, asset_duration=asset_duration,
        )

        logger.info("씬 %d 클립 생성 (%.1f초%s)", scene["id"], duration, " bounce" if bounce else "")
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

    def build_audio_cmd(
        self,
        audio_path: Path,
        duration: float,
        fade_out_sec: float,
        output_path: Path,
    ) -> list[str]:
        """오디오 트리밍 + fade out FFmpeg 명령어 생성"""
        cmd = ["ffmpeg", "-y", "-i", str(audio_path)]
        if fade_out_sec > 0:
            fade_start = duration - fade_out_sec
            cmd += [
                "-af", f"afade=t=out:st={fade_start}:d={fade_out_sec}",
                "-t", str(duration),
            ]
        cmd += ["-c:a", "aac", "-b:a", "192k", str(output_path)]
        return cmd

    def trim_audio(
        self,
        audio_path: Path,
        duration: float,
        fade_out_sec: float,
        output_path: Path,
    ) -> Path:
        """오디오를 duration으로 자르고 fade out 적용"""
        cmd = self.build_audio_cmd(audio_path, duration, fade_out_sec, output_path)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"오디오 트리밍 에러: {result.stderr[:500]}")
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
            "-vf", f"subtitles={self._escape_ffmpeg_path(srt_path)}:charenc=UTF-8:force_style='{style}'",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "copy", "-movflags", "+faststart",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"자막 burn-in 에러: {result.stderr[:500]}")
        return output_path

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

    def compose_full(
        self,
        project_dir: Path,
        scenes: list[dict],
        music_file: str,
        fade_out_sec: float = 0.0,
        title: str | None = None,
        title_card_config: dict | None = None,
        bounce: bool = False,
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
                clip = self.compose_scene(scene, assets_dir, work_dir, bounce=bounce)
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

            if title and tc_config.get("enabled", True):
                fonts_dir = project_dir / "assets" / "fonts"
                if not fonts_dir.exists():
                    fonts_dir = Path(__file__).parent.parent / "assets" / "fonts"

                self.add_title_card(
                    video_path=current_video,
                    output_path=final_path,
                    title=title,
                    title_card_config=tc_config,
                    fonts_dir=fonts_dir,
                )
            else:
                shutil.copy2(current_video, final_path)

        return final_path

    def build_bounce_cmd(self, clip_path: Path, output_path: Path) -> list[str]:
        """정방향+역방향 바운스 루프 FFmpeg 명령어 생성"""
        return [
            "ffmpeg", "-y",
            "-i", str(clip_path),
            "-filter_complex",
            "[0:v]reverse[r];[0:v][r]concat=n=2:v=1:a=0[out]",
            "-map", "[out]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(output_path),
        ]

    def build_stream_loop_cmd(
        self, clip_path: Path, output_path: Path, repeat: int = 30
    ) -> list[str]:
        """바운스 클립을 N번 반복하는 FFmpeg 명령어 생성"""
        return [
            "ffmpeg", "-y",
            "-stream_loop", str(repeat),
            "-i", str(clip_path),
            "-c", "copy",
            "-movflags", "+faststart",
            str(output_path),
        ]

    def bounce_loop(
        self, clip_path: Path, output_path: Path, repeat: int = 30
    ) -> Path:
        """클립 → 정방향+역방향 바운스 → N번 반복해서 긴 영상 생성"""
        work_dir = output_path.parent

        bounce_path = work_dir / f"_bounce_{clip_path.stem}.mp4"
        cmd = self.build_bounce_cmd(clip_path, bounce_path)
        logger.info("바운스 루프 생성: %s", clip_path.name)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"바운스 루프 에러: {result.stderr[:500]}")

        cmd = self.build_stream_loop_cmd(bounce_path, output_path, repeat)
        logger.info("스트림 루프 %d회 반복", repeat)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"스트림 루프 에러: {result.stderr[:500]}")

        bounce_path.unlink(missing_ok=True)
        return output_path

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
