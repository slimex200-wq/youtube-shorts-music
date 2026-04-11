import json
from unittest.mock import MagicMock

from services.metadata import MetadataGenerator

MOCK_METADATA = {
    "title": "Midnight Rain 🌧️ Lo-fi Chill #Shorts",
    "description": "A peaceful lo-fi track for your late-night study session.\n\n#lofi #chill #study #Shorts",
    "tags": ["lofi", "chill", "study music", "lo-fi hip hop", "Shorts"],
    "first_comment": "Perfect for late-night study 🌧️\nDrop a like if this helps you focus!\n#lofi #chill #studymusic #Shorts",
}


def _make_llm(payload: dict) -> MagicMock:
    mock_llm = MagicMock()
    mock_llm.complete.return_value = json.dumps(payload)
    return mock_llm


def test_generate_metadata():
    gen = MetadataGenerator(llm=_make_llm(MOCK_METADATA))
    result = gen.generate(genre="lo-fi hip hop", title_suggestion="Midnight Rain")

    assert "title" in result
    assert "description" in result
    assert "tags" in result
    assert "first_comment" in result
    assert "#Shorts" in result["title"]
    assert "Shorts" in result["tags"]
    assert result["first_comment"]


def test_generate_includes_genre_in_prompt():
    mock_llm = _make_llm(MOCK_METADATA)
    gen = MetadataGenerator(llm=mock_llm)
    gen.generate(genre="dark trap", title_suggestion="Shadow")

    user_arg = mock_llm.complete.call_args.kwargs.get("user")
    assert user_arg is not None
    assert "dark trap" in user_arg
    assert "Shadow" in user_arg


def test_generate_ensures_shorts_tag():
    no_shorts = {
        "title": "Test #Shorts",
        "description": "desc",
        "tags": ["lofi", "chill"],
    }
    gen = MetadataGenerator(llm=_make_llm(no_shorts))
    result = gen.generate(genre="lo-fi", title_suggestion="Test")

    assert "Shorts" in result["tags"]
