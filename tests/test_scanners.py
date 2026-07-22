"""
Tests for scanner modules.
Uses mocking to avoid actual API calls and costs.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from scanners.base_scanner import BaseScanner, ScanResult
from scanners.censys_scanner import CensysScanner
from scanners.github_scanner import GitHubScanner
from scanners.port_scanner import PortScanner, ServiceScanner
from core.scanner_manager import ScannerManager


class TestBaseScanner:
    """Tests for the base scanner."""

    def test_scanner_initialization(self):
        """Test scanner initialization."""
        scanner = MockScanner("test_scanner")
        assert scanner.name == "test_scanner"
        assert scanner.enabled is True
        assert scanner._scan_count == 0

    def test_scanner_enable_disable(self):
        """Test enabling/disabling scanner."""
        scanner = MockScanner("test", enabled=False)
        assert scanner.is_enabled() is False
        scanner.enabled = True
        assert scanner.is_enabled() is True

    def test_scanner_stats(self):
        """Test scanner statistics."""
        scanner = MockScanner("test")
        stats = scanner.get_stats()
        assert stats["name"] == "test"
        assert stats["enabled"] is True
        assert stats["scan_count"] == 0

    def test_safe_scan_success(self):
        """Test safe_scan with successful scan."""
        scanner = MockScanner("test")
        result = scanner.safe_scan()
        assert result is not None
        assert result.scanner_name == "test"
        assert scanner._scan_count == 1

    def test_safe_scan_failure(self):
        """Test safe_scan with failing scan."""
        scanner = FailingScanner("fail_test")
        result = scanner.safe_scan()
        assert result is None
        assert scanner._scan_count == 3  # Retried 3 times


class TestCensysScanner:
    """Tests for Censys scanner."""

    def test_censys_initialization(self):
        """Test Censys scanner initialization."""
        scanner = CensysScanner(api_id="test_id", api_secret="test_secret")
        assert scanner.name == "censys"
        assert scanner.api_id == "test_id"
        assert scanner.api_secret == "test_secret"

    def test_censys_disabled_without_credentials(self):
        """Test Censys scanner is disabled without credentials."""
        scanner = CensysScanner()
        assert scanner.api_id == ""
        assert scanner.api_secret == ""

    @patch("scanners.censys_scanner.CensysScanner._get_client")
    def test_censys_scan_mocked(self, mock_client):
        """Test Censys scan with mocked client."""
        mock_client.return_value.search.return_value = [
            {"results": [{"services": [{"port": 8080, "service_name": "http"}]}]}
        ]
        scanner = CensysScanner(api_id="test", api_secret="test")
        result = scanner.scan()
        assert result.scanner_name == "censys"
        assert len(result.raw_data) > 0


class TestGitHubScanner:
    """Tests for GitHub scanner."""

    def test_github_initialization(self):
        """Test GitHub scanner initialization."""
        scanner = GitHubScanner(token="test_token")
        assert scanner.name == "github"
        assert scanner.token == "test_token"

    def test_github_disabled_without_token(self):
        """Test GitHub scanner is disabled without token."""
        scanner = GitHubScanner()
        assert scanner.token == ""


class TestPortScanner:
    """Tests for port scanner."""

    def test_port_scanner_initialization(self):
        """Test port scanner initialization."""
        scanner = PortScanner(target="localhost")
        assert scanner.name == "port"
        assert scanner.target == "localhost"
        assert len(scanner.ports) > 0

    @patch("scanners.port_scanner.PortScanner._scan_ports")
    def test_port_scan_mocked(self, mock_scan):
        """Test port scan with mocked port checking."""
        mock_scan.return_value = {8000: "FastAPI/uvicorn"}
        scanner = PortScanner(target="localhost")
        result = scanner.scan()
        assert result.scanner_name == "port"
        assert len(result.raw_data) > 0

    @patch("scanners.port_scanner.PortScanner._check_http")
    def test_port_check_http_mocked(self, mock_http):
        """Test HTTP check with mocked response."""
        mock_http.return_value = "test response"
        scanner = PortScanner(target="localhost")
        result = scanner.scan()
        assert len(result.raw_data) > 0


class TestServiceScanner:
    """Tests for service scanner."""

    def test_service_scanner_initialization(self):
        """Test service scanner initialization."""
        scanner = ServiceScanner()
        assert scanner.name == "service"

    @patch("scanners.port_scanner.requests.get")
    def test_service_scan_mocked(self, mock_get):
        """Test service scan with mocked requests."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "service info"
        mock_get.return_value = mock_response

        scanner = ServiceScanner()
        result = scanner.scan()
        assert result.scanner_name == "service"
        assert len(result.raw_data) > 0


class TestScannerManager:
    """Tests for scanner manager."""

    def test_manager_initialization(self):
        """Test scanner manager initialization."""
        manager = ScannerManager()
        assert len(manager.scanners) == 0

    def test_add_scanner(self):
        """Test adding a scanner."""
        manager = ScannerManager()
        scanner = MockScanner("test")
        manager.add_scanner(scanner)
        assert len(manager.scanners) == 1
        assert manager.get_scanner("test") is not None

    def test_remove_scanner(self):
        """Test removing a scanner."""
        manager = ScannerManager()
        scanner = MockScanner("test")
        manager.add_scanner(scanner)
        assert manager.remove_scanner("test") is True
        assert len(manager.scanners) == 0

    def test_scan_all_empty(self):
        """Test scan_all with no scanners."""
        manager = ScannerManager()
        results = manager.scan_all()
        assert results == []

    def test_scan_all_with_scanners(self):
        """Test scan_all with scanners."""
        manager = ScannerManager()
        manager.add_scanner(MockScanner("test1"))
        manager.add_scanner(MockScanner("test2"))
        results = manager.scan_all()
        assert len(results) == 2

    def test_get_all_raw_data(self):
        """Test extracting raw data from results."""
        manager = ScannerManager()
        manager.add_scanner(MockScanner("test"))
        results = manager.scan_all()
        raw_data = manager.get_all_raw_data(results)
        assert len(raw_data) > 0


# ── Mock Scanners for Testing ──────────────────────────────────────────────

class MockScanner(BaseScanner):
    """Mock scanner for testing."""

    def scan(self) -> ScanResult:
        return ScanResult(
            scanner_name=self.name,
            source="mock",
            raw_data=["mock data 1", "mock data 2"],
        )


class FailingScanner(BaseScanner):
    """Scanner that always fails for testing retry logic."""

    def scan(self) -> ScanResult:
        raise Exception("Intentional failure for testing")
