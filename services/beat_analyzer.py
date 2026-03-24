import logging
from pathlib import Path

import librosa
import numpy as np

logger = logging.getLogger(__name__)


class BeatAnalyzer:
    def analyze(self, audio_path: str | Path) -> dict:
        """음악 파일에서 BPM과 비트 타임스탬프 추출"""
        y, sr = librosa.load(str(audio_path), sr=22050)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        duration = librosa.get_duration(y=y, sr=sr)

        # tempo가 ndarray일 수 있음
        bpm = float(tempo) if np.isscalar(tempo) else float(tempo[0])

        logger.info("BPM: %.1f, 비트 수: %d, 길이: %.1f초", bpm, len(beat_times), duration)

        return {
            "bpm": round(bpm, 1),
            "duration_sec": round(duration, 2),
            "beat_times": [round(float(t), 3) for t in beat_times],
        }

    def split_scenes(
        self,
        beat_times: list[float],
        duration: float,
        beats_per_scene: int = 4,
    ) -> list[dict]:
        """비트 타임스탬프를 beats_per_scene 단위로 그룹핑하여 씬 분할"""
        scenes = []
        total_beats = len(beat_times)
        scene_id = 1
        i = 0

        while i < total_beats:
            start_idx = i
            end_idx = min(i + beats_per_scene, total_beats)

            # 남은 비트가 beats_per_scene의 절반 미만이면 이전 씬에 합침
            remaining = total_beats - end_idx
            if 0 < remaining < beats_per_scene // 2 and scenes:
                end_idx = total_beats

            start_sec = beat_times[start_idx]
            end_sec = beat_times[end_idx - 1] if end_idx < total_beats else duration

            # end_sec가 마지막 비트면 다음 비트 위치 추정
            if end_idx < total_beats:
                end_sec = beat_times[end_idx]

            scenes.append({
                "id": scene_id,
                "start_sec": round(start_sec, 3),
                "end_sec": round(end_sec, 3),
                "beat_count": end_idx - start_idx,
                "image_prompt": None,
                "video_prompt": None,
                "asset_file": None,
                "lyrics_line": None,
            })

            scene_id += 1
            i = end_idx

        # 마지막 씬의 end_sec를 전체 길이로 맞춤
        if scenes:
            scenes[-1]["end_sec"] = round(duration, 3)

        return scenes

    def suggest_beats_per_scene(self, bpm: float, duration_sec: float) -> int:
        """BPM과 길이에 따라 적절한 씬당 비트 수 제안 (목표: 4~10 씬)"""
        total_beats = bpm * duration_sec / 60.0
        target_scenes = 6  # 이상적인 씬 수

        raw = total_beats / target_scenes
        # 4의 배수로 반올림 (음악적으로 자연스러움: 1마디=4비트)
        beats = max(4, round(raw / 4) * 4)
        return min(beats, 16)  # 최대 4마디
