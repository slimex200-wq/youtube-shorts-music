"""이미지 + 음악 → 풀 길이 비디오 에디터 (Shorts 제한 없음)"""
import logging
import random
import shutil
import tempfile
from pathlib import Path

from services.composer import ShortsComposer, SUPPORTED_IMAGE_EXTS

logger = logging.getLogger(__name__)

SUPPORTED_AUDIO_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"}


class EditorComposer:
    def __init__(self):
        self._composer = ShortsComposer()

    def get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration without full beat analysis."""
        import librosa
        return librosa.get_duration(filename=str(audio_path))

    def discover_files(self, directory: Path, extensions: set[str]) -> list[Path]:
        """Discover and sort files by name in a directory."""
        files = []
        for f in sorted(directory.iterdir()):
            if f.suffix.lower() in extensions and f.is_file():
                files.append(f)
        return files

    def distribute_images(self, images: list[Path], duration: float) -> list[dict]:
        """Evenly distribute images across the song duration as scene dicts."""
        n = len(images)
        seg_dur = duration / n
        scenes = []
        for i, img in enumerate(images):
            scenes.append({
                "id": i + 1,
                "start_sec": round(i * seg_dur, 3),
                "end_sec": round((i + 1) * seg_dur, 3),
                "asset_file": img.name,
                "beat_count": 0,
                "image_prompt": None,
                "video_prompt": None,
                "lyrics_line": None,
            })
        return scenes

    def compose_one(
        self,
        audio_path: Path,
        images: list[Path],
        output_path: Path,
    ) -> Path:
        """Produce one full-length video for one song."""
        duration = self.get_audio_duration(audio_path)
        scenes = self.distribute_images(images, duration)
        images_dir = images[0].parent

        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)

            # Render each scene clip (Ken Burns zoom for images)
            clips = []
            for scene in scenes:
                clip = self._composer.compose_scene(scene, images_dir, work_dir)
                clips.append(clip)

            # Concatenate all clips
            concat_path = work_dir / "concat.mp4"
            self._composer.concat_clips(clips, concat_path)

            # Merge with audio (no trim, no fade — full length)
            merged_path = work_dir / "merged.mp4"
            self._composer.merge_audio(concat_path, audio_path, merged_path)

            shutil.copy2(merged_path, output_path)

        return output_path

    def compose_all(
        self,
        songs_dir: Path,
        images_dir: Path,
        output_dir: Path,
        shuffle: bool = False,
    ) -> list[Path]:
        """Process all songs, one video each."""
        songs = self.discover_files(songs_dir, SUPPORTED_AUDIO_EXTS)
        images = self.discover_files(images_dir, SUPPORTED_IMAGE_EXTS)

        if not songs:
            raise FileNotFoundError(f"음악 파일 없음: {songs_dir}")
        if not images:
            raise FileNotFoundError(f"이미지 파일 없음: {images_dir}")

        if shuffle:
            images = list(images)
            random.shuffle(images)

        output_dir.mkdir(parents=True, exist_ok=True)
        results = []

        for song in songs:
            output_path = output_dir / f"{song.stem}_editor.mp4"
            logger.info("편집 시작: %s (%d개 이미지)", song.name, len(images))
            self.compose_one(song, images, output_path)
            results.append(output_path)

        return results
