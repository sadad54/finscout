from app.rag.chunker import chunk_text


def test_chunk_text_basic():
    text = " ".join(f"word{i}" for i in range(500))
    chunks = chunk_text(text, chunk_size=200, overlap=40)
    assert len(chunks) > 1
    assert chunks[0].startswith("word0 word1")


def test_chunk_text_overlap():
    text = " ".join(f"word{i}" for i in range(500))
    chunks = chunk_text(text, chunk_size=200, overlap=40)
    first_words = chunks[0].split()
    second_words = chunks[1].split()
    assert first_words[-40:] == second_words[:40]


def test_chunk_text_empty():
    assert chunk_text("") == []


def test_chunk_text_short_text_single_chunk():
    text = "just a few words here"
    chunks = chunk_text(text, chunk_size=200, overlap=40)
    assert len(chunks) == 1
    assert chunks[0] == text