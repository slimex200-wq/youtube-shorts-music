import json
from unittest.mock import MagicMock, patch
from services.suno_prompt import SunoPromptGenerator

MOCK_RESPONSE = {
    "style": "lo-fi hip hop, jazzy piano, vinyl crackle, mellow drums, chill vibes",
    "prompt": "A peaceful late-night study session, rain tapping on the window, warm lo-fi beats with soft piano melodies and gentle vinyl crackle",
    "title_suggestion": "Midnight Rain",
    "bpm_suggestion": 85
}


def test_generate_basic():
    gen = SunoPromptGenerator("fake-key")
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(MOCK_RESPONSE))]

    with patch.object(gen.client.messages, "create", return_value=mock_msg):
        result = gen.generate(genre="lo-fi hip hop")

    assert "style" in result
    assert "prompt" in result
    assert "title_suggestion" in result
    assert "lo-fi" in result["style"].lower()


def test_generate_with_options():
    gen = SunoPromptGenerator("fake-key")
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(MOCK_RESPONSE))]

    with patch.object(gen.client.messages, "create", return_value=mock_msg) as mock_create:
        gen.generate(genre="dark trap", bpm=140, mood="aggressive", instruments=["808 bass", "hi-hats"])

    user_msg = mock_create.call_args[1]["messages"][0]["content"]
    assert "dark trap" in user_msg
    assert "140" in user_msg
    assert "aggressive" in user_msg
    assert "808 bass" in user_msg


def test_generate_with_lyrics():
    gen = SunoPromptGenerator("fake-key")
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(MOCK_RESPONSE))]

    with patch.object(gen.client.messages, "create", return_value=mock_msg) as mock_create:
        gen.generate(genre="k-pop", lyrics="밤이 깊어가고 별이 빛나")

    user_msg = mock_create.call_args[1]["messages"][0]["content"]
    assert "밤이 깊어가고" in user_msg


def test_generate_instrumental():
    gen = SunoPromptGenerator("fake-key")
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(MOCK_RESPONSE))]

    with patch.object(gen.client.messages, "create", return_value=mock_msg) as mock_create:
        gen.generate(genre="ambient", instrumental=True)

    user_msg = mock_create.call_args[1]["messages"][0]["content"]
    assert "instrumental" in user_msg.lower()


def test_generate_handles_markdown_json():
    gen = SunoPromptGenerator("fake-key")
    wrapped = f"```json\n{json.dumps(MOCK_RESPONSE)}\n```"
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=wrapped)]

    with patch.object(gen.client.messages, "create", return_value=mock_msg):
        result = gen.generate(genre="jazz")

    assert "style" in result


def test_generate_shranz_includes_genre_context():
    """shranz 장르 시 시스템 프롬프트에 장르 지식이 반영되는지 확인"""
    gen = SunoPromptGenerator("fake-key")
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(MOCK_RESPONSE))]

    with patch.object(gen.client.messages, "create", return_value=mock_msg) as mock_create:
        gen.generate(genre="shranz", bpm=155)

    system_msg = mock_create.call_args[1]["system"]
    assert "distort" in system_msg.lower() or "kick" in system_msg.lower()
