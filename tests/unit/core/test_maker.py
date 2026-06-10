import tempfile
from src.modules.scaffolder.core.maker import make_class, list_types, list_stacks, ClassType

ALL_TYPES = list_types()
ALL_STACKS = list_stacks()


def test_list_types():
    assert len(ALL_TYPES) >= 19


def test_list_stacks():
    assert len(ALL_STACKS) >= 14


def test_every_type_python():
    for info in ALL_TYPES:
        r = make_class(info["id"], "User", stack="python")
        assert r["success"], f"{info['id']}: {r}"
        assert r["class_name"] == "User"
        assert r["relative_path"].endswith("user.py")


def test_python_controller():
    r = make_class("controller", "User", stack="python")
    assert r["success"]
    assert r["relative_path"] == "controllers/http/user.py"
    assert "async def index" in r["content"]


def test_python_service():
    r = make_class("service", "User", stack="python")
    assert r["success"]
    assert r["relative_path"] == "services/user.py"
    assert "async def execute" in r["content"]


def test_python_model():
    r = make_class("model", "User", stack="python")
    assert r["success"]
    assert r["relative_path"] == "models/entities/user.py"
    assert "def __init__" in r["content"]


def test_python_interface():
    r = make_class("interface", "User", stack="python")
    assert r["success"]
    assert "abstractmethod" in r["content"]
    assert r["relative_path"] == "contracts/user.py"


def test_python_enum():
    r = make_class("enum", "Status", stack="python")
    assert r["success"]
    assert "DEFAULT" in r["content"]


def test_module_context():
    r = make_class("controller", "Payment", stack="python", module="payment")
    assert r["success"]
    assert r["relative_path"] == "payment/controllers/http/payment.py"


def test_typescript_service():
    r = make_class("service", "AuthService", stack="typescript")
    assert r["success"]
    assert r["file_name"] == "AuthService.ts"
    assert "extends Service" in r["content"]


def test_php_controller():
    r = make_class("controller", "User", stack="php")
    assert r["success"]
    assert r["relative_path"] == "Controllers/Http/User.php"
    assert r["content"].startswith("<?php")


def test_go_model():
    r = make_class("model", "User", stack="go")
    assert r["success"]
    assert "type User struct" in r["content"]


def test_write_file():
    with tempfile.TemporaryDirectory() as tmp:
        r = make_class("controller", "Health", stack="python", target_path=tmp)
        assert r["success"]
        assert r["written"]
        import os
        assert os.path.exists(r["absolute_path"])


def test_preview_no_write():
    r = make_class("controller", "Health", stack="python")
    assert r["success"]
    assert not r["written"]
    assert r.get("absolute_path") is None


def test_invalid_type():
    r = make_class("invalid_type", "User")
    assert not r["success"]
    assert "error" in r


def test_invalid_stack():
    r = make_class("controller", "User", stack="invalid")
    assert not r["success"]
    assert "error" in r


def test_empty_name():
    r = make_class("controller", "")
    assert not r["success"]
