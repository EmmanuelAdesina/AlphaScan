"""
GitHub scanner for APIS.
Uses the GitHub API (free tier) to scan public repositories for hardcoded secrets.
"""
import logging
import base64
from typing import List, Dict, Optional
from scanners.base_scanner import BaseScanner, ScanResult
from config.settings import GITHUB_TOKEN, GITHUB_SEARCH_QUERY

logger = logging.getLogger(__name__)


class GitHubScanner(BaseScanner):
    """
    Scanner that uses GitHub's code search API to find files containing
    potential API keys, secrets, and configuration files.
    """

    # File extensions and names to look for
    TARGET_FILES = {
        ".env", "config.py", "settings.py", "secrets.json",
        "config.json", "credentials.json", "app.config",
    }

    def __init__(self, token: Optional[str] = None,
                 query: Optional[str] = None,
                 enabled: bool = True):
        super().__init__("github", enabled)
        self.token = token or GITHUB_TOKEN
        self.query = query or GITHUB_SEARCH_QUERY
        self._client = None

    def _get_client(self):
        """Lazily initialize the GitHub client."""
        if self._client is None:
            if not self.token:
                raise ValueError("GitHub token not configured")
            from github import Github
            self._client = Github(self.token)
        return self._client

    def scan(self) -> ScanResult:
        """
        Search GitHub for code containing potential API keys.
        Uses GitHub's code search API to find files with secrets.
        """
        client = self._get_client()
        raw_data: List[str] = []
        metadata: Dict = {"query": self.query, "files_found": 0, "repos_searched": 0}

        try:
            # Search for code matching the query
            results = client.search_code(self.query, per_page=30)

            for file_content in results:
                try:
                    # Get file content
                    content = file_content.decoded_content.decode("utf-8", errors="ignore")
                    if content:
                        raw_data.append(content)
                        metadata["files_found"] += 1

                    # Track repository
                    repo_name = file_content.repository.full_name
                    metadata["repos_searched"] += 1

                except Exception as e:
                    logger.debug(f"Failed to read file {file_content.name}: {e}")
                    continue

        except Exception as e:
            logger.error(f"GitHub search failed: {e}")
            raise

        return ScanResult(
            scanner_name=self.name,
            source="github",
            raw_data=raw_data,
            metadata=metadata,
        )


class GitHubRepoScanner(BaseScanner):
    """
    Scanner that searches specific repositories for secrets.
    Useful for scanning known repositories that may contain exposed keys.
    """

    def __init__(self, token: Optional[str] = None,
                 target_repos: Optional[List[str]] = None,
                 enabled: bool = True):
        super().__init__("github_repos", enabled)
        self.token = token or GITHUB_TOKEN
        self.target_repos = target_repos or []
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.token:
                raise ValueError("GitHub token not configured")
            from github import Github
            self._client = Github(self.token)
        return self._client

    def scan(self) -> ScanResult:
        """Scan specific repositories for exposed secrets."""
        client = self._get_client()
        raw_data: List[str] = []
        metadata: Dict = {"repos_scanned": 0, "files_found": 0}

        for repo_name in self.target_repos:
            try:
                repo = client.get_repo(repo_name)
                metadata["repos_scanned"] += 1

                # Get the default branch
                default_branch = repo.default_branch

                # Search for files with potential secrets
                for file_path in self._find_secret_files(repo):
                    try:
                        file_content = repo.get_contents(file_path, ref=default_branch)
                        if file_content and file_content.decoded_content:
                            content = file_content.decoded_content.decode(
                                "utf-8", errors="ignore"
                            )
                            raw_data.append(content)
                            metadata["files_found"] += 1
                    except Exception as e:
                        logger.debug(f"Failed to read {file_path} in {repo_name}: {e}")

            except Exception as e:
                logger.warning(f"Failed to scan repo {repo_name}: {e}")
                continue

        return ScanResult(
            scanner_name=self.name,
            source="github_repos",
            raw_data=raw_data,
            metadata=metadata,
        )

    def _find_secret_files(self, repo) -> List[str]:
        """Find files that may contain secrets in a repository."""
        secret_files = []
        try:
            contents = repo.get_contents("", ref=repo.default_branch)
            for item in contents:
                if item.type == "file" and item.name in self.TARGET_FILES:
                    secret_files.append(item.path)
        except Exception:
            pass
        return secret_files
