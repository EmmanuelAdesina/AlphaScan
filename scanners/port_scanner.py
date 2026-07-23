"""
Port scanner for AlphaScan v0.5.
Scans common ports for exposed services and API endpoints.
"""
import logging
import socket
from typing import List, Dict, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from scanners.base_scanner import BaseScanner, ScanResult
from utils.http_client import get_http_client

logger = logging.getLogger(__name__)


class PortScanner(BaseScanner):
    """
    Scanner that checks common ports for exposed services.
    Looks for services like Ollama (11434), HuggingFace (7860),
    FastAPI (8000), Flask (5000), etc.
    """

    # Common ports associated with exposed APIs and services
    COMMON_PORTS: List[int] = [
        80, 443, 3000, 5000, 7860, 8000, 8080, 8443,
        8888, 9000, 9090, 11434, 27017, 5432, 6379,
        9200, 11211, 1433, 1521, 3306, 5432, 5984,
        6379, 8086, 8123, 8529, 9042, 9080, 9200, 9300,
    ]

    # Ports to scan for specific API services
    API_PORTS: Dict[int, str] = {
        11434: "Ollama",
        7860: "HuggingFace",
        8000: "FastAPI/uvicorn",
        5000: "Flask",
        3000: "React/Vue dev server",
        8080: "HTTP alt",
        27017: "MongoDB",
        5432: "PostgreSQL",
        6379: "Redis",
        9200: "Elasticsearch",
        3306: "MySQL",
        1433: "SQL Server",
    }

    def __init__(self, target: str = "localhost",
                 ports: Optional[List[int]] = None,
                 max_workers: int = 50,
                 enabled: bool = True):
        super().__init__("port", enabled)
        self.target = target
        self.ports = ports or self.COMMON_PORTS
        self.max_workers = max_workers
        self._http = get_http_client()

    def scan(self) -> ScanResult:
        """
        Scan common ports for open services.
        Returns information about exposed services.
        """
        raw_data: List[str] = []
        metadata: Dict = {"target": self.target, "ports_scanned": len(self.ports),
                          "open_ports": 0, "services_found": []}

        open_ports = self._scan_ports()

        for port, service_name in open_ports.items():
            metadata["open_ports"] += 1
            metadata["services_found"].append({
                "port": port,
                "service": service_name,
            })

            # Try to get HTTP response from the service
            http_data = self._check_http(port)
            if http_data:
                raw_data.append(http_data)

            # Add port info as raw data
            raw_data.append(f"Open port {port}: {service_name}")

        return ScanResult(
            scanner_name=self.name,
            source=f"port_scan:{self.target}",
            raw_data=raw_data,
            metadata=metadata,
        )

    def _scan_ports(self) -> Dict[int, str]:
        """Scan ports in parallel using thread pool."""
        open_ports: Dict[int, str] = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._check_port, port): port
                for port in self.ports
            }

            for future in as_completed(futures):
                port = futures[future]
                try:
                    is_open = future.result(timeout=5)
                    if is_open:
                        service = self.API_PORTS.get(port, "unknown")
                        open_ports[port] = service
                except Exception:
                    pass

        return open_ports

    def _check_port(self, port: int) -> bool:
        """Check if a single port is open."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((self.target, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _check_http(self, port: int) -> Optional[str]:
        """Try to get HTTP response from an open port."""
        urls_to_try = [
            f"http://{self.target}:{port}/",
            f"http://{self.target}:{port}/.env",
            f"http://{self.target}:{port}/api",
            f"http://{self.target}:{port}/config",
        ]

        for url in urls_to_try:
            try:
                response = self._http.get(url, timeout=5)
                if response and response.status_code == 200 and response.text:
                    return response.text
            except Exception:
                continue

        return None


class ServiceScanner(BaseScanner):
    """
    Scanner that checks specific service endpoints for exposed APIs.
    Looks for services like Ollama, HuggingFace, etc.
    """

    SERVICE_ENDPOINTS: Dict[str, List[str]] = {
        "ollama": [
            "http://localhost:11434/api/tags",
            "http://localhost:11434/api/show",
        ],
        "huggingface": [
            "http://localhost:7860/",
            "http://localhost:7860/api/pipelines",
        ],
        "fastapi": [
            "http://localhost:8000/docs",
            "http://localhost:8000/openapi.json",
        ],
    }

    def __init__(self, enabled: bool = True):
        super().__init__("service", enabled)
        self._http = get_http_client()

    def scan(self) -> ScanResult:
        """Scan service endpoints for exposed APIs."""
        raw_data: List[str] = []
        metadata: Dict = {"services_checked": 0, "services_found": []}

        for service_name, endpoints in self.SERVICE_ENDPOINTS.items():
            for endpoint in endpoints:
                try:
                    response = self._http.get(endpoint, timeout=5)
                    if response and response.status_code == 200:
                        metadata["services_found"].append({
                            "service": service_name,
                            "endpoint": endpoint,
                        })
                        raw_data.append(response.text)
                    metadata["services_checked"] += 1
                except Exception:
                    metadata["services_checked"] += 1
                    continue

        return ScanResult(
            scanner_name=self.name,
            source="service_scan",
            raw_data=raw_data,
            metadata=metadata,
        )