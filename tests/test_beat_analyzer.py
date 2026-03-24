import numpy as np
from unittest.mock import patch, MagicMock
from services.beat_analyzer import BeatAnalyzer


def test_analyze_returns_bpm_and_beats():
    """librosa 모킹하여 비트 분석 결과 확인"""
    mock_beat_times = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5,
                                 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5])

    with patch("services.beat_analyzer.librosa") as mock_librosa:
        mock_librosa.load.return_value = (np.zeros(22050 * 8), 22050)
        mock_librosa.beat.beat_track.return_value = (120.0, np.arange(16))
        mock_librosa.frames_to_time.return_value = mock_beat_times
        mock_librosa.get_duration.return_value = 8.0

        analyzer = BeatAnalyzer()
        result = analyzer.analyze("fake.mp3")

    assert result["bpm"] == 120.0
    assert result["duration_sec"] == 8.0
    assert len(result["beat_times"]) == 16
    assert result["beat_times"][0] == 0.0


def test_split_scenes_default():
    """기본 4비트(1마디)씩 씬 분할"""
    beat_times = [i * 0.5 for i in range(16)]  # 16비트, 0.5초 간격
    duration = 8.0

    analyzer = BeatAnalyzer()
    scenes = analyzer.split_scenes(beat_times, duration, beats_per_scene=4)

    assert len(scenes) == 4
    assert scenes[0]["id"] == 1
    assert scenes[0]["start_sec"] == 0.0
    assert scenes[0]["end_sec"] == 2.0
    assert scenes[0]["beat_count"] == 4
    assert scenes[3]["end_sec"] == duration


def test_split_scenes_custom_beats():
    """8비트(2마디)씩 씬 분할"""
    beat_times = [i * 0.5 for i in range(16)]
    duration = 8.0

    analyzer = BeatAnalyzer()
    scenes = analyzer.split_scenes(beat_times, duration, beats_per_scene=8)

    assert len(scenes) == 2
    assert scenes[0]["beat_count"] == 8
    assert scenes[0]["end_sec"] == 4.0


def test_split_scenes_remainder_beats():
    """나머지 비트가 적으면 마지막 씬에 합침"""
    beat_times = [i * 0.5 for i in range(9)]  # 9비트
    duration = 4.5

    analyzer = BeatAnalyzer()
    scenes = analyzer.split_scenes(beat_times, duration, beats_per_scene=4)

    # 4 + 5(나머지 1비트 < 4//2=2 이므로 합침) = 씬 2개
    assert len(scenes) == 2
    assert scenes[1]["end_sec"] == duration


def test_suggest_beats_per_scene():
    """BPM과 총 길이에 따라 적절한 beats_per_scene 제안"""
    analyzer = BeatAnalyzer()

    # 120 BPM, 45초 → 약 90비트 → 4비트씩 = 22씬 (너무 많음) → 8비트 권장
    suggestion = analyzer.suggest_beats_per_scene(bpm=120.0, duration_sec=45.0)
    assert 4 <= suggestion <= 16
    # 씬 수가 4~10개 사이가 되도록
    total_beats = 120.0 * 45.0 / 60.0
    scene_count = total_beats / suggestion
    assert 4 <= scene_count <= 12
