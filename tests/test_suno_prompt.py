import json
from unittest.mock import MagicMock

from services.suno_prompt import SunoPromptGenerator

MOCK_RESPONSE = {
    "style": "lo-fi hip hop, jazzy piano, vinyl crackle, mellow drums, chill vibes",
    "prompt": "A peaceful late-night study session, rain tapping on the window, warm lo-fi beats with soft piano melodies and gentle vinyl crackle",
    "title_suggestion": "Midnight Rain",
    "bpm_suggestion": 85,
    "substyle": None,
}


def _make_llm(payload=None, raw_text=None) -> MagicMock:
    mock_llm = MagicMock()
    if raw_text is not None:
        mock_llm.complete.return_value = raw_text
    else:
        mock_llm.complete.return_value = json.dumps(payload or MOCK_RESPONSE)
    return mock_llm


def _system_arg(mock_llm):
    return mock_llm.complete.call_args.kwargs["system"]


def _user_arg(mock_llm):
    return mock_llm.complete.call_args.kwargs["user"]


def test_generate_basic():
    mock_llm = _make_llm()
    gen = SunoPromptGenerator(llm=mock_llm)
    result = gen.generate(genre="lo-fi hip hop")

    assert "style" in result
    assert "prompt" in result
    assert "title_suggestion" in result
    assert "lo-fi" in result["style"].lower()


def test_generate_with_options():
    mock_llm = _make_llm()
    gen = SunoPromptGenerator(llm=mock_llm)
    gen.generate(genre="dark trap", bpm=140, mood="aggressive", instruments=["808 bass", "hi-hats"])

    user = _user_arg(mock_llm)
    assert "dark trap" in user
    assert "140" in user
    assert "aggressive" in user
    assert "808 bass" in user


def test_generate_with_lyrics():
    mock_llm = _make_llm()
    gen = SunoPromptGenerator(llm=mock_llm)
    gen.generate(genre="k-pop", lyrics="밤이 깊어가고 별이 빛나")

    assert "밤이 깊어가고" in _user_arg(mock_llm)


def test_generate_instrumental():
    mock_llm = _make_llm()
    gen = SunoPromptGenerator(llm=mock_llm)
    gen.generate(genre="ambient", instrumental=True)

    assert "instrumental" in _user_arg(mock_llm).lower()


def test_generate_handles_markdown_json():
    wrapped = f"```json\n{json.dumps(MOCK_RESPONSE)}\n```"
    mock_llm = _make_llm(raw_text=wrapped)
    gen = SunoPromptGenerator(llm=mock_llm)
    result = gen.generate(genre="jazz")

    assert "style" in result


def test_generate_shranz_includes_substyle_context():
    mock_llm = _make_llm()
    gen = SunoPromptGenerator(llm=mock_llm)
    gen.generate(genre="shranz", bpm=155)

    assert "SELECTED SCHRANZ SUBSTYLE" in _system_arg(mock_llm)


def test_generate_shranz_with_explicit_substyle():
    mock_llm = _make_llm()
    gen = SunoPromptGenerator(llm=mock_llm)
    result = gen.generate(genre="shranz", substyle="acid_schranz")

    assert "Acid Schranz" in _system_arg(mock_llm)
    assert result["substyle"] == "acid_schranz"


def test_generate_shranz_user_prompt_includes_substyle():
    mock_llm = _make_llm()
    gen = SunoPromptGenerator(llm=mock_llm)
    gen.generate(genre="shranz")

    assert "서브스타일" in _user_arg(mock_llm)


def test_generate_non_shranz_no_substyle():
    mock_llm = _make_llm()
    gen = SunoPromptGenerator(llm=mock_llm)
    gen.generate(genre="lo-fi hip hop")

    assert "SELECTED SCHRANZ SUBSTYLE" not in _system_arg(mock_llm)
    assert "서브스타일" not in _user_arg(mock_llm)
