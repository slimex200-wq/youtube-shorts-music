import json
from unittest.mock import MagicMock, patch
from services.prompt_generator import PromptGenerator

MOCK_PROMPTS = [
    {
        "id": 1,
        "image_prompt": "Rainy city window at night, neon reflections, moody lighting, 9:16 vertical",
        "video_prompt": "Slow zoom into rain-streaked window with neon city lights, 9:16 vertical, 6 seconds",
        "lyrics_line": "밤이 깊어가고"
    },
    {
        "id": 2,
        "image_prompt": "Empty street with puddles reflecting streetlights, cinematic, 9:16 vertical",
        "video_prompt": "Gentle pan across wet empty street, streetlight reflections in puddles, 9:16 vertical, 5 seconds",
        "lyrics_line": "별이 빛나는 하늘"
    },
]


def test_generate_prompts():
    gen = PromptGenerator("fake-key")
    scenes = [
        {"id": 1, "start_sec": 0.0, "end_sec": 6.0, "beat_count": 8,
         "image_prompt": None, "video_prompt": None, "asset_file": None, "lyrics_line": None},
        {"id": 2, "start_sec": 6.0, "end_sec": 11.0, "beat_count": 8,
         "image_prompt": None, "video_prompt": None, "asset_file": None, "lyrics_line": None},
    ]

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(MOCK_PROMPTS, ensure_ascii=False))]

    with patch.object(gen.client.messages, "create", return_value=mock_msg):
        result = gen.generate(genre="lo-fi hip hop", scenes=scenes)

    assert len(result) == 2
    assert "9:16" in result[0]["image_prompt"]
    assert "9:16" in result[0]["video_prompt"]
    assert result[0]["lyrics_line"] == "밤이 깊어가고"


def test_generate_instrumental_no_lyrics():
    gen = PromptGenerator("fake-key")
    scenes = [
        {"id": 1, "start_sec": 0.0, "end_sec": 6.0, "beat_count": 8,
         "image_prompt": None, "video_prompt": None, "asset_file": None, "lyrics_line": None},
    ]

    mock_response = [{"id": 1, "image_prompt": "Abstract waves, 9:16", "video_prompt": "Flowing abstract, 9:16, 6s", "lyrics_line": None}]
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(mock_response))]

    with patch.object(gen.client.messages, "create", return_value=mock_msg) as mock_create:
        gen.generate(genre="ambient", scenes=scenes, instrumental=True)

    user_msg = mock_create.call_args[1]["messages"][0]["content"]
    assert "instrumental" in user_msg.lower()


def test_generate_with_style_anime():
    """style='anime' 전달 시 user prompt에 포함"""
    gen = PromptGenerator("fake-key")
    scenes = [
        {"id": 1, "start_sec": 0.0, "end_sec": 6.0, "beat_count": 8,
         "image_prompt": None, "video_prompt": None, "asset_file": None, "lyrics_line": None},
    ]

    mock_response = [{"id": 1, "image_prompt": "Anime style scene, 9:16 vertical", "video_prompt": "Anime pan, 9:16 vertical, 6 seconds", "lyrics_line": None}]
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(mock_response))]

    with patch.object(gen.client.messages, "create", return_value=mock_msg) as mock_create:
        gen.generate(genre="shranz", scenes=scenes, instrumental=True, style="anime")

    user_msg = mock_create.call_args[1]["messages"][0]["content"]
    assert "anime" in user_msg.lower()


def test_generate_with_lyrics_distribution():
    gen = PromptGenerator("fake-key")
    scenes = [
        {"id": 1, "start_sec": 0.0, "end_sec": 5.0, "beat_count": 4,
         "image_prompt": None, "video_prompt": None, "asset_file": None, "lyrics_line": None},
        {"id": 2, "start_sec": 5.0, "end_sec": 10.0, "beat_count": 4,
         "image_prompt": None, "video_prompt": None, "asset_file": None, "lyrics_line": None},
    ]

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(MOCK_PROMPTS, ensure_ascii=False))]

    with patch.object(gen.client.messages, "create", return_value=mock_msg) as mock_create:
        gen.generate(genre="k-pop", scenes=scenes, lyrics="밤이 깊어가고\n별이 빛나는 하늘")

    user_msg = mock_create.call_args[1]["messages"][0]["content"]
    assert "밤이 깊어가고" in user_msg
