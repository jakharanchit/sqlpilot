# ============================================================
# tests/test_client_manager.py
# Tests for tools/client_manager.py
# ============================================================

import json
from pathlib import Path

import pytest


class TestGetActiveClient:
    def test_returns_string(self, temp_project):
        from tools.client_manager import get_active_client
        result = get_active_client()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_reads_from_active_client_file(self, temp_project, monkeypatch):
        from tools.client_manager import get_active_client
        import tools.client_manager as cm

        marker = temp_project / ".active_client"
        marker.write_text("client_test", encoding="utf-8")
        monkeypatch.setattr(cm, "ACTIVE_CLIENT_FILE", marker)

        result = get_active_client()
        assert result == "client_test"

    def test_falls_back_to_config(self, temp_project, monkeypatch):
        from tools.client_manager import get_active_client
        import tools.client_manager as cm

        # No .active_client file
        missing = temp_project / ".active_client_nonexistent"
        monkeypatch.setattr(cm, "ACTIVE_CLIENT_FILE", missing)

        result = get_active_client()
        assert isinstance(result, str)


class TestSetActiveClient:
    def test_writes_client_name_to_file(self, temp_project, monkeypatch):
        from tools.client_manager import set_active_client, get_active_client
        import tools.client_manager as cm

        # Create the client dir
        client_dir = temp_project / "projects" / "test_client"
        client_dir.mkdir(parents=True)

        marker = temp_project / ".active_client"
        monkeypatch.setattr(cm, "ACTIVE_CLIENT_FILE", marker)
        monkeypatch.setattr(cm, "PROJECTS_DIR", str(temp_project / "projects"))

        set_active_client("test_client")
        assert marker.read_text().strip() == "test_client"

    def test_raises_for_nonexistent_client(self, temp_project, monkeypatch):
        from tools.client_manager import set_active_client
        from tools.error_handler import ConfigError
        import tools.client_manager as cm

        monkeypatch.setattr(cm, "PROJECTS_DIR", str(temp_project / "projects"))
        monkeypatch.setattr(
            cm, "ACTIVE_CLIENT_FILE", temp_project / ".active_client"
        )

        with pytest.raises(ConfigError):
            set_active_client("nonexistent_client_xyz")


class TestGetClientPaths:
    def test_returns_all_required_keys(self, temp_project, monkeypatch):
        from tools.client_manager import get_client_paths
        import tools.client_manager as cm

        monkeypatch.setattr(cm, "PROJECTS_DIR", str(temp_project / "projects"))
        monkeypatch.setattr(
            cm, "ACTIVE_CLIENT_FILE", temp_project / ".active_client"
        )
        (temp_project / ".active_client").write_text("client_acme")

        paths = get_client_paths("client_acme")

        required = [
            "name", "base", "migrations", "reports",
            "deployments", "snapshots", "runs",
            "history_db", "config_file",
        ]
        for key in required:
            assert key in paths, f"Missing key: {key}"

    def test_paths_contain_client_name(self, temp_project, monkeypatch):
        from tools.client_manager import get_client_paths
        import tools.client_manager as cm

        monkeypatch.setattr(cm, "PROJECTS_DIR", str(temp_project / "projects"))

        paths = get_client_paths("my_client")
        assert "my_client" in paths["base"]
        assert "my_client" in paths["migrations"]
        assert "my_client" in paths["history_db"]


class TestCreateClient:
    def test_creates_directory_structure(self, temp_project, monkeypatch):
        from tools.client_manager import create_client
        import tools.client_manager as cm

        projects_dir = temp_project / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(cm, "PROJECTS_DIR", str(projects_dir))
        monkeypatch.setattr(cm, "TEMPLATE_DIR", projects_dir / "_template")
        monkeypatch.setattr(
            cm, "ACTIVE_CLIENT_FILE", temp_project / ".active_client"
        )

        result = create_client(
            name         = "test_client",
            display_name = "Test Client Corp",
            database     = "TestDB",
            set_active   = False,
        )

        client_dir = projects_dir / "test_client"
        assert client_dir.exists()
        assert (client_dir / "migrations").exists()
        assert (client_dir / "reports").exists()
        assert (client_dir / "deployments").exists()
        assert (client_dir / "runs").exists()

    def test_creates_client_json(self, temp_project, monkeypatch):
        from tools.client_manager import create_client
        import tools.client_manager as cm

        projects_dir = temp_project / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(cm, "PROJECTS_DIR", str(projects_dir))
        monkeypatch.setattr(cm, "TEMPLATE_DIR", projects_dir / "_template")
        monkeypatch.setattr(
            cm, "ACTIVE_CLIENT_FILE", temp_project / ".active_client"
        )

        create_client(
            name         = "json_test",
            display_name = "JSON Test",
            database     = "JSONDB",
            set_active   = False,
        )

        config_file = projects_dir / "json_test" / "client.json"
        assert config_file.exists()

        cfg = json.loads(config_file.read_text())
        assert cfg["name"]         == "json_test"
        assert cfg["display_name"] == "JSON Test"
        assert cfg["db_config"]["database"] == "JSONDB"

    def test_creates_baseline_migration(self, temp_project, monkeypatch):
        from tools.client_manager import create_client
        import tools.client_manager as cm

        projects_dir = temp_project / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(cm, "PROJECTS_DIR", str(projects_dir))
        monkeypatch.setattr(cm, "TEMPLATE_DIR", projects_dir / "_template")
        monkeypatch.setattr(
            cm, "ACTIVE_CLIENT_FILE", temp_project / ".active_client"
        )

        create_client(name="baseline_test", set_active=False)

        baseline = projects_dir / "baseline_test" / "migrations" / "000_baseline.sql"
        assert baseline.exists()
        content = baseline.read_text()
        assert "BASELINE" in content

    def test_raises_for_invalid_name(self, temp_project, monkeypatch):
        from tools.client_manager import create_client
        from tools.error_handler import ConfigError
        import tools.client_manager as cm

        projects_dir = temp_project / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(cm, "PROJECTS_DIR", str(projects_dir))

        with pytest.raises(ConfigError):
            create_client(name="invalid name with spaces", set_active=False)

    def test_raises_for_duplicate_name(self, temp_project, monkeypatch):
        from tools.client_manager import create_client
        from tools.error_handler import ConfigError
        import tools.client_manager as cm

        projects_dir = temp_project / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(cm, "PROJECTS_DIR", str(projects_dir))
        monkeypatch.setattr(cm, "TEMPLATE_DIR", projects_dir / "_template")
        monkeypatch.setattr(
            cm, "ACTIVE_CLIENT_FILE", temp_project / ".active_client"
        )

        create_client(name="dup_test", set_active=False)

        with pytest.raises(ConfigError):
            create_client(name="dup_test", set_active=False)


class TestListClients:
    def test_returns_list(self, temp_project, monkeypatch):
        from tools.client_manager import list_clients
        import tools.client_manager as cm

        projects_dir = temp_project / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(cm, "PROJECTS_DIR", str(projects_dir))
        monkeypatch.setattr(
            cm, "ACTIVE_CLIENT_FILE", temp_project / ".active_client"
        )

        result = list_clients()
        assert isinstance(result, list)

    def test_includes_created_clients(self, temp_project, monkeypatch):
        from tools.client_manager import create_client, list_clients
        import tools.client_manager as cm

        projects_dir = temp_project / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(cm, "PROJECTS_DIR", str(projects_dir))
        monkeypatch.setattr(cm, "TEMPLATE_DIR", projects_dir / "_template")
        monkeypatch.setattr(
            cm, "ACTIVE_CLIENT_FILE", temp_project / ".active_client"
        )

        create_client(name="list_test_a", set_active=False)
        create_client(name="list_test_b", set_active=False)

        clients = list_clients()
        names = [c["name"] for c in clients]
        assert "list_test_a" in names
        assert "list_test_b" in names

    def test_marks_active_client(self, temp_project, monkeypatch):
        from tools.client_manager import create_client, list_clients, set_active_client
        import tools.client_manager as cm

        projects_dir = temp_project / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        marker = temp_project / ".active_client"
        monkeypatch.setattr(cm, "PROJECTS_DIR", str(projects_dir))
        monkeypatch.setattr(cm, "TEMPLATE_DIR", projects_dir / "_template")
        monkeypatch.setattr(cm, "ACTIVE_CLIENT_FILE", marker)

        create_client(name="active_test", set_active=False)
        marker.write_text("active_test")

        clients = list_clients()
        active  = [c for c in clients if c["active"]]
        assert len(active) == 1
        assert active[0]["name"] == "active_test"

    def test_excludes_template_folder(self, temp_project, monkeypatch):
        from tools.client_manager import list_clients
        import tools.client_manager as cm

        projects_dir = temp_project / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        (projects_dir / "_template").mkdir()
        monkeypatch.setattr(cm, "PROJECTS_DIR", str(projects_dir))
        monkeypatch.setattr(
            cm, "ACTIVE_CLIENT_FILE", temp_project / ".active_client"
        )

        clients = list_clients()
        names   = [c["name"] for c in clients]
        assert "_template" not in names


class TestUpdateClientConfig:
    def test_updates_database_field(self, temp_project, monkeypatch):
        from tools.client_manager import create_client, update_client_config
        import tools.client_manager as cm

        projects_dir = temp_project / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(cm, "PROJECTS_DIR", str(projects_dir))
        monkeypatch.setattr(cm, "TEMPLATE_DIR", projects_dir / "_template")
        monkeypatch.setattr(
            cm, "ACTIVE_CLIENT_FILE", temp_project / ".active_client"
        )

        create_client(name="update_test", database="OldDB", set_active=False)
        update_client_config(client="update_test", database="NewDB")

        cfg_file = projects_dir / "update_test" / "client.json"
        cfg      = json.loads(cfg_file.read_text())
        assert cfg["db_config"]["database"] == "NewDB"

    def test_updates_bak_path(self, temp_project, monkeypatch):
        from tools.client_manager import create_client, update_client_config
        import tools.client_manager as cm

        projects_dir = temp_project / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(cm, "PROJECTS_DIR", str(projects_dir))
        monkeypatch.setattr(cm, "TEMPLATE_DIR", projects_dir / "_template")
        monkeypatch.setattr(
            cm, "ACTIVE_CLIENT_FILE", temp_project / ".active_client"
        )

        create_client(name="bak_test", set_active=False)
        update_client_config(client="bak_test", bak_path=r"C:\new\path.bak")

        cfg_file = projects_dir / "bak_test" / "client.json"
        cfg      = json.loads(cfg_file.read_text())
        assert cfg["bak_path"] == r"C:\new\path.bak"

    def test_only_updates_provided_fields(self, temp_project, monkeypatch):
        from tools.client_manager import create_client, update_client_config
        import tools.client_manager as cm

        projects_dir = temp_project / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(cm, "PROJECTS_DIR", str(projects_dir))
        monkeypatch.setattr(cm, "TEMPLATE_DIR", projects_dir / "_template")
        monkeypatch.setattr(
            cm, "ACTIVE_CLIENT_FILE", temp_project / ".active_client"
        )

        create_client(
            name="selective_test", display_name="Original Name",
            database="OrigDB", set_active=False
        )
        update_client_config(client="selective_test", database="NewDB")

        cfg_file = projects_dir / "selective_test" / "client.json"
        cfg      = json.loads(cfg_file.read_text())
        # Database updated
        assert cfg["db_config"]["database"] == "NewDB"
        # Display name NOT changed
        assert cfg["display_name"] == "Original Name"


class TestWithClientContextManager:
    def test_switches_and_restores(self, temp_project, monkeypatch):
        from tools.client_manager import (
            create_client, set_active_client,
            get_active_client, with_client
        )
        import tools.client_manager as cm

        projects_dir = temp_project / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        marker = temp_project / ".active_client"
        monkeypatch.setattr(cm, "PROJECTS_DIR", str(projects_dir))
        monkeypatch.setattr(cm, "TEMPLATE_DIR", projects_dir / "_template")
        monkeypatch.setattr(cm, "ACTIVE_CLIENT_FILE", marker)

        create_client(name="ctx_a", set_active=False)
        create_client(name="ctx_b", set_active=False)
        marker.write_text("ctx_a")

        assert get_active_client() == "ctx_a"

        with with_client("ctx_b"):
            assert get_active_client() == "ctx_b"

        assert get_active_client() == "ctx_a"

    def test_restores_on_exception(self, temp_project, monkeypatch):
        from tools.client_manager import (
            create_client, with_client, get_active_client
        )
        import tools.client_manager as cm

        projects_dir = temp_project / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        marker = temp_project / ".active_client"
        monkeypatch.setattr(cm, "PROJECTS_DIR", str(projects_dir))
        monkeypatch.setattr(cm, "TEMPLATE_DIR", projects_dir / "_template")
        monkeypatch.setattr(cm, "ACTIVE_CLIENT_FILE", marker)

        create_client(name="exc_a", set_active=False)
        create_client(name="exc_b", set_active=False)
        marker.write_text("exc_a")

        try:
            with with_client("exc_b"):
                raise RuntimeError("something broke")
        except RuntimeError:
            pass

        # Should be restored to exc_a even after exception
        assert get_active_client() == "exc_a"
