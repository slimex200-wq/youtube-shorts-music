import json
from unittest.mock import MagicMock

from services.prompt_generator import PromptGenerator

MOCK_PROMPTS = [
    {
        "id": 1,
        "image_prompt": "Rainy city window at night, neon reflections, moody lighting, 9:16 vertical",
        "video_prompt": "Slow zoom into rain-streaked window with neon city lights, 9:16 vertical, 6 seconds",
        "lyrics_line": "밤이 깊어가고",
    },
    {
        "id": 2,
        "image_prompt": "Empty street with puddles reflecting streetlights, cinematic, 9:16 vertical",
        "video_prompt": "Gentle pan across wet empty street, streetlight reflections in puddles, 9:16 vertical, 5 seconds",
        "lyrics_line": "별이 빛나는 하늘",
    },
]


def _make_llm(payload) -> MagicMock:
    mock_llm = MagicMock()
    mock_llm.complete.return_value = json.dumps(payload, ensure_ascii=False)
    return mock_llm


def _user_arg(mock_llm):
    return mock_llm.complete.call_args.kwargs["user"]


def _scene(scene_id: int, start: float, end: float) -> dict:
    return {
        "id": scene_id,
        "start_sec": start,
        "end_sec": end,
        "beat_count": 8,
        "image_prompt": None,
        "video_prompt": None,
        "asset_file": None,
        "lyrics_line": None,
    }


def test_generate_prompts():
    gen = PromptGenerator(llm=_make_llm(MOCK_PROMPTS))
    scenes = [_scene(1, 0.0, 6.0), _scene(2, 6.0, 11.0)]
    result = gen.generate(genre="lo-fi hip hop", scenes=scenes)

    assert len(result) == 2
    assert "9:16" in result[0]["image_prompt"]
    assert "9:16" in result[0]["video_prompt"]
    assert result[0]["lyrics_line"] == "밤이 깊어가고"


def test_generate_instrumental_no_lyrics():
    mock_response = [
        {
            "id": 1,
            "image_prompt": "Abstract waves, 9:16",
            "video_prompt": "Flowing abstract, 9:16, 6s",
            "lyrics_line": None,
        }
    ]
    mock_llm = _make_llm(mock_response)
    gen = PromptGenerator(llm=mock_llm)
    gen.generate(genre="ambient", scenes=[_scene(1, 0.0, 6.0)], instrumental=True)

    assert "instrumental" in _user_arg(mock_llm).lower()


def test_generate_with_style_anime():
    mock_response = [
        {
            "id": 1,
            "image_prompt": "Anime style scene, 9:16 vertical",
            "video_prompt": "Anime pan, 9:16 vertical, 6 seconds",
            "lyrics_line": None,
        }
    ]
    mock_llm = _make_llm(mock_response)
    gen = PromptGenerator(llm=mock_llm)
    gen.generate(
        genre="shranz",
        scenes=[_scene(1, 0.0, 6.0)],
        instrumental=True,
        style="anime",
    )

    assert "anime" in _user_arg(mock_llm).lower()


def test_generate_with_lyrics_distribution():
    mock_llm = _make_llm(MOCK_PROMPTS)
    gen = PromptGenerator(llm=mock_llm)
    scenes = [_scene(1, 0.0, 5.0), _scene(2, 5.0, 10.0)]
    gen.generate(
        genre="k-pop",
        scenes=scenes,
        lyrics="밤이 깊어가고\n별이 빛나는 하늘",
    )

    assert "밤이 깊어가고" in _user_arg(mock_llm)
