import json
from unittest.mock import MagicMock, patch
from services.metadata import MetadataGenerator

MOCK_METADATA = {
    "title": "Midnight Rain 🌧️ Lo-fi Chill #Shorts",
    "description": "A peaceful lo-fi track for your late-night study session.\n\n#lofi #chill #study #Shorts",
    "tags": ["lofi", "chill", "study music", "lo-fi hip hop", "Shorts"],
    "first_comment": "Perfect for late-night study 🌧️\nDrop a like if this helps you focus!\n#lofi #chill #studymusic #Shorts",
}


def test_generate_metadata():
    gen = MetadataGenerator("fake-key")
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(MOCK_METADATA))]

    with patch.object(gen.client.messages, "create", return_value=mock_msg):
        result = gen.generate(genre="lo-fi hip hop", title_suggestion="Midnight Rain")

    assert "title" in result
    assert "description" in result
    assert "tags" in result
    assert "first_comment" in result
    assert "#Shorts" in result["title"]
    assert "Shorts" in result["tags"]
    assert result["first_comment"]


def test_generate_includes_genre_in_prompt():
    gen = MetadataGenerator("fake-key")
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(MOCK_METADATA))]

    with patch.object(gen.client.messages, "create", return_value=mock_msg) as mock_create:
        gen.generate(genre="dark trap", title_suggestion="Shadow")

    user_msg = mock_create.call_args[1]["messages"][0]["content"]
    assert "dark trap" in user_msg
    assert "Shadow" in user_msg


def test_generate_ensures_shorts_tag():
    gen = MetadataGenerator("fake-key")
    no_shorts = {
        "title": "Test #Shorts",
        "description": "desc",
        "tags": ["lofi", "chill"]
    }
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(no_shorts))]

    with patch.object(gen.client.messages, "create", return_value=mock_msg):
        result = gen.generate(genre="lo-fi", title_suggestion="Test")

    assert "Shorts" in result["tags"]
