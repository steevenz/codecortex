"""
Tests for route extraction.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.modules.codegraph.core.route import RouteExtractor, extract_routes_from_files


def test_fastapi_route():
    extractor = RouteExtractor()
    content = """
@router.get("/users")
def list_users():
    pass

@app.post("/users")
def create_user():
    pass
"""
    routes = extractor.extract("routes.py", content)
    assert len(routes) == 2
    methods = {(r.method, r.path) for r in routes}
    assert ("GET", "/users") in methods
    assert ("POST", "/users") in methods


def test_django_route():
    extractor = RouteExtractor()
    content = """
urlpatterns = [
    path("users/", views.list_users),
    path("users/<int:pk>/", views.user_detail),
]
"""
    routes = extractor.extract("urls.py", content)
    assert len(routes) >= 2


def test_flask_route():
    extractor = RouteExtractor()
    content = """
@app.route("/api/users")
def list_users():
    pass
"""
    routes = extractor.extract("app.py", content)
    assert len(routes) >= 1
    assert routes[0].path == "/api/users"


def test_express_route():
    extractor = RouteExtractor()
    content = """
router.get("/users", getUsers);
router.post("/users", createUser);
"""
    routes = extractor.extract("routes.js", content)
    assert len(routes) >= 2


def test_nextjs_pages():
    extractor = RouteExtractor()
    routes = extractor.extract("/pages/users/[id].tsx", "")
    assert len(routes) >= 1
    assert ":id" in routes[0].path


def test_extract_routes_from_files():
    files = [
        {"path": "main.py", "content": "@app.get('/health')\ndef health(): pass\n"},
    ]
    routes = extract_routes_from_files(files)
    assert len(routes) >= 1
    assert routes[0].path == "/health"


if __name__ == "__main__":
    test_fastapi_route()
    test_django_route()
    test_flask_route()
    test_express_route()
    test_nextjs_pages()
    test_extract_routes_from_files()
    print("All route extraction tests passed.")
