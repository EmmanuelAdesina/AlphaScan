from fastapi.testclient import TestClient
import pytest

import api.routes as routes


class FakeScannerManager:
    def get_scanner_stats(self):
        return [
            {
                "name": "dummy",
                "enabled": True,
                "scan_count": 0,
                "last_scan": None,
            }
        ]

    def get_enabled_scanners(self):
        return ["dummy"]


class FakeLLMManager:
    @staticmethod
    def get_active_provider():
        return "regex"


class FakeParser:
    @property
    def llm_manager(self):
        return FakeLLMManager()


class FakeGitManager:
    def get_status(self):
        return {"available": False}

    def is_available(self):
        return False


class FakeImprover:
    def trigger_improvement(self, description: str):
        return True, f"Improvement requested: {description}"

    def get_metrics(self):
        return {
            "metrics": {"items": []},
            "success_rate": 1.0,
            "improvement_history": [],
            "deployment_history": [],
        }


class FakeState:
    def __init__(self):
        self.running = False
        self.cycle = 0
        self.last_scan_time = None
        self.last_scan_duration = 0.0


class FakeEngine:
    def __init__(self):
        self.state = FakeState()
        self.scanner_manager = FakeScannerManager()
        self.parser = FakeParser()
        self.git_manager = FakeGitManager()
        self.verifier = True
        self.improver = FakeImprover()

    def run(self):
        return None

    def stop(self):
        self.state.running = False

    def get_status(self):
        return {
            "running": False,
            "cycle": 0,
            "total_keys_found": 0,
            "total_scans": 0,
            "last_scan_time": None,
            "last_scan_duration": 0.0,
            "last_error": None,
            "discovered_key_types": [],
            "scan_interval": 300,
            "enabled_scanners": ["dummy"],
            "autonomous_mode": False,
            "autonomous_decisions": 0,
            "uptime_start": None,
            "keys_by_rank": {},
            "current_strategy": "none",
        }

    def force_scan(self):
        return {"cycle": 1, "keys_found": 0}

    def get_results(self):
        return [{"cycle": 1, "keys_found": 0, "timestamp": None, "scanner_stats": []}]

    def get_keys(self):
        return []


@pytest.fixture(autouse=True)
def fake_engine(monkeypatch):
    engine = FakeEngine()
    monkeypatch.setattr(routes, "get_engine", lambda: engine)
    return engine


def test_root_endpoint_returns_service_info():
    with TestClient(routes.app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json()["service"] == "AlphaScan"
    assert "/status" in response.json()["endpoints"]


def test_status_endpoint_returns_engine_status():
    with TestClient(routes.app) as client:
        response = client.get("/status")

    assert response.status_code == 200
    assert response.json()["running"] is False
    assert response.json()["total_scans"] == 0


def test_scan_endpoint_triggers_engine_scan():
    with TestClient(routes.app) as client:
        response = client.post("/scan", json={"scanners": [], "parallel": True})

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "scan_id" in response.json()


def test_results_endpoint_returns_recent_results():
    with TestClient(routes.app) as client:
        response = client.get("/results")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert isinstance(response.json()["results"], list)


def test_keys_endpoint_returns_key_list():
    with TestClient(routes.app) as client:
        response = client.get("/keys")

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["keys"] == []


def test_improvement_endpoint_invokes_self_improvement():
    with TestClient(routes.app) as client:
        response = client.post("/improvement", json={"description": "Validate endpoint"})

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "Improvement requested" in response.json()["message"]


def test_metrics_endpoint_returns_improvement_metrics():
    with TestClient(routes.app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert response.json()["success_rate"] == 1.0
    assert response.json()["metrics"]["items"] == []
