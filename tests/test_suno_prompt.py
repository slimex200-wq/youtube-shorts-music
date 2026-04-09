import json
from unittest.mock import MagicMock, patch
from services.suno_prompt import SunoPromptGenerator

MOCK_RESPONSE = {
    "style": "lo-fi hip hop, jazzy piano, vinyl crackle, mellow drums, chill vibes",
    "prompt": "A peaceful late-night study session, rain tapping on the window, warm lo-fi beats with soft piano melodies and gentle vinyl crackle",
    "title_suggestion": "Midnight Rain",
    "bpm_suggestion": 85,
    "substyle": None,
}


def _make_mock_msg(response=None):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(response or MOCK_RESPONSE))]
    return mock_msg


def test_generate_basic():
    gen = SunoPromptGenerator("fake-key")

    with patch.object(gen.client.messages, "create", return_value=_make_mock_msg()):
        result = gen.generate(genre="lo-fi hip hop")

    assert "style" in result
    assert "prompt" in result
    assert "title_suggestion" in result
    assert "lo-fi" in result["style"].lower()


def test_generate_with_options():
    gen = SunoPromptGenerator("fake-key")

    with patch.object(gen.client.messages, "create", return_value=_make_mock_msg()) as mock_create:
        gen.generate(genre="dark trap", bpm=140, mood="aggressive", instruments=["808 bass", "hi-hats"])

    user_msg = mock_create.call_args[1]["messages"][0]["content"]
    assert "dark trap" in user_msg
    assert "140" in user_msg
    assert "aggressive" in user_msg
    assert "808 bass" in user_msg


def test_generate_with_lyrics():
    gen = SunoPromptGenerator("fake-key")

    with patch.object(gen.client.messages, "create", return_value=_make_mock_msg()) as mock_create:
        gen.generate(genre="k-pop", lyrics="밤이 깊어가고 별이 빛나")

    user_msg = mock_create.call_args[1]["messages"][0]["content"]
    assert "밤이 깊어가고" in user_msg


def test_generate_instrumental():
    gen = SunoPromptGenerator("fake-key")

    with patch.object(gen.client.messages, "create", return_value=_make_mock_msg()) as mock_create:
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


def test_generate_shranz_includes_substyle_context():
    """shranz 장르 시 서브스타일이 시스템 프롬프트에 주입되는지 확인"""
    gen = SunoPromptGenerator("fake-key")

    with patch.object(gen.client.messages, "create", return_value=_make_mock_msg()) as mock_create:
        gen.generate(genre="shranz", bpm=155)

    system_msg = mock_create.call_args[1]["system"]
    assert "SELECTED SCHRANZ SUBSTYLE" in system_msg


def test_generate_shranz_with_explicit_substyle():
    """명시적 서브스타일 선택 시 해당 스타일이 주입되는지 확인"""
    gen = SunoPromptGenerator("fake-key")

    with patch.object(gen.client.messages, "create", return_value=_make_mock_msg()) as mock_create:
        result = gen.generate(genre="shranz", substyle="acid_schranz")

    system_msg = mock_create.call_args[1]["system"]
    assert "Acid Schranz" in system_msg
    assert result["substyle"] == "acid_schranz"


def test_generate_shranz_user_prompt_includes_substyle():
    """shranz 생성 시 user prompt에 서브스타일이 포함되는지 확인"""
    gen = SunoPromptGenerator("fake-key")

    with patch.object(gen.client.messages, "create", return_value=_make_mock_msg()) as mock_create:
        gen.generate(genre="shranz")

    user_msg = mock_create.call_args[1]["messages"][0]["content"]
    assert "서브스타일" in user_msg


def test_generate_non_shranz_no_substyle():
    """non-shranz 장르는 서브스타일 주입 없음"""
    gen = SunoPromptGenerator("fake-key")

    with patch.object(gen.client.messages, "create", return_value=_make_mock_msg()) as mock_create:
        gen.generate(genre="lo-fi hip hop")

    system_msg = mock_create.call_args[1]["system"]
    assert "SELECTED SCHRANZ SUBSTYLE" not in system_msg
    user_msg = mock_create.call_args[1]["messages"][0]["content"]
    assert "서브스타일" not in user_msg
