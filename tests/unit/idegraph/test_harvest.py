import os
import sys
sys.path.insert(0, os.path.abspath('.'))

import json
from pathlib import Path
from unittest.mock import MagicMock

from src.modules.idegraph.services.ide_harvest import IdeHarvest
from src.modules.idegraph.services.storage import Storage

def test_harvest_installations(tmp_path: Path):
    storage_mock = MagicMock(spec=Storage)
    storage_mock.ensure_ide.return_value = "ide-123"
    storage_mock.upsert_configuration.return_value = True
    storage_mock.upsert_ide_setting.return_value = True
    
    harvest = IdeHarvest(storage=storage_mock)
    
    # Create fake installation dir
    inst = tmp_path / "cursor-inst"
    user_dir = inst / "User"
    user_dir.mkdir(parents=True)
    
    # Fake settings
    (user_dir / "settings.json").write_text(json.dumps({
        "editor.formatOnSave": True,
        "mcp.servers": {"test": {}}
    }))
    (user_dir / "keybindings.json").write_text(json.dumps([{"key": "ctrl+c", "command": "copy"}]))
    
    # Fake extension
    ext_dir = inst / "extensions" / "testpublisher.testext-1.0.0"
    ext_dir.mkdir(parents=True)
    (ext_dir / "package.json").write_text(json.dumps({
        "name": "testext",
        "publisher": "testpublisher",
        "version": "1.0.0"
    }))
    
    counts = harvest.harvest_installations(
        ide_name="cursor",
        ide_type="editor",
        installations=[inst],
        request_id="req-123"
    )
    
    assert counts["installations_seen"] == 1
    assert counts["configurations_upserted"] > 0
    assert counts["ide_settings_upserted"] > 0
    
    # Assert storage was called
    storage_mock.ensure_ide.assert_called_once()
    storage_mock.upsert_configuration.assert_called()

if __name__ == "__main__":
    import tempfile
    import shutil
    tmp = Path(tempfile.mkdtemp())
    try:
        test_harvest_installations(tmp)
        print("All test_harvest tests PASSED")
    finally:
        shutil.rmtree(tmp)
