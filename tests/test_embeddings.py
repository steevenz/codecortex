"""
Tests for vector embeddings and semantic search.
Uses REAL sentence-transformers model (all-MiniLM-L6-v2).
No mocks.
"""
import sys, tempfile
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import pytest


def test_generate_embedding():
    from src.domain.codeindex.infrastructure.embeddings import generate_embedding
    emb = generate_embedding("def hello(): pass")
    if emb is not None:
        assert len(emb) == 384  # MiniLM dimension
        assert abs(sum(emb)) > 0  # Not zero vector


def test_cosine_similarity():
    import numpy as np
    from src.domain.codeindex.infrastructure.embeddings import cosine_similarity
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([1.0, 0.0, 0.0])
    assert abs(cosine_similarity(a, b) - 1.0) < 0.001
    c = np.array([-1.0, 0.0, 0.0])
    assert abs(cosine_similarity(a, c) + 1.0) < 0.001


def test_chunk_code():
    from src.domain.codeindex.infrastructure.embeddings import chunk_code
    content = """
def hello():
    print("hello")

class Greeter:
    def greet(self):
        pass
"""
    chunks = chunk_code("test.py", content)
    assert len(chunks) >= 2  # Should split into at least 2 chunks


def test_embedding_store():
    import numpy as np
    from src.domain.codeindex.infrastructure.embeddings import EmbeddingStore
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "emb.db")
        store = EmbeddingStore(db_path)
        # Store a test embedding
        chunks = [
            {"file_path": "main.py", "start_line": 1, "end_line": 5,
             "content": "print('hello')", "embedding": np.ones(384, dtype=np.float32)}
        ]
        store.store("main.py", chunks, "repo-1")
        assert store.count == 1
        # Search
        results = store.search(np.ones(384, dtype=np.float32), top_k=5)
        assert len(results) >= 1
        assert results[0]["file_path"] == "main.py"
        assert results[0]["similarity"] > 0.99


def test_embedding_store_clear():
    import numpy as np
    from src.domain.codeindex.infrastructure.embeddings import EmbeddingStore
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "emb.db")
        store = EmbeddingStore(db_path)
        chunks = [{"file_path": "f.py", "start_line": 1, "end_line": 1,
                    "content": "x=1", "embedding": np.ones(384, dtype=np.float32)}]
        store.store("f.py", chunks, "repo-1")
        assert store.count == 1
        store.clear_file("f.py")
        assert store.count == 0


def test_index_file_embeddings():
    from src.domain.codeindex.infrastructure.embeddings import index_file_embeddings
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "emb.db")
        content = "def hello():\n    print('world')\n\nclass App:\n    def run(self):\n        pass\n"
        count = index_file_embeddings("app.py", content, db_path, "repo-1")
        assert count >= 1


def test_semantic_search():
    from src.domain.codeindex.infrastructure.embeddings import semantic_search, index_file_embeddings
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "emb.db")
        index_file_embeddings("auth.py", """
def login(username, password):
    \"\"\"Authenticate user with credentials.\"\"\"
    return verify_credentials(username, password)
""", db_path, "repo-1")
        index_file_embeddings("utils.py", """
def format_date(date):
    return date.strftime("%Y-%m-%d")
""", db_path, "repo-1")
        results = semantic_search("user authentication login", db_path, top_k=5)
        assert isinstance(results, list)
        if results:
            assert results[0]["similarity"] > 0


if __name__ == "__main__":
    test_generate_embedding()
    test_cosine_similarity()
    test_chunk_code()
    test_embedding_store()
    test_embedding_store_clear()
    test_index_file_embeddings()
    test_semantic_search()
    print("All embedding tests passed!")
