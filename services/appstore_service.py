"""
AppStore service for KOReader Store - GitHub API integration
Ported from omer-faruq/appstore.koplugin (main.lua + appstore_net_github.lua)
"""

from typing import Optional, Tuple, Dict, Any, List
import requests
import json
import urllib.parse
import logging
from utils.versioning import is_newer_version
import time

logger = logging.getLogger(__name__)

# Constants from original Lua code
BASE_URL = "https://api.github.com"
USER_AGENT = "KOReader-AppStore"
ACCEPT_HEADER = "application/vnd.github+json"

# GitHub search queries
PLUGIN_TOPICS = ["koreader-plugin"]
PATCH_TOPICS = ["koreader-user-patch"]
PLUGIN_NAME_QUERIES = ['in:name ".koplugin" fork:true']
PATCH_NAME_QUERIES = ['in:name "KOReader.patches" fork:true']


class AppStoreService:
    """Service for fetching KOReader plugins and patches from GitHub"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token
        logger.info("AppStore service initialized")
    
    def _get_auth_headers(self) -> Optional[Dict[str, str]]:
        """Get authentication headers for GitHub API"""
        if not self.github_token or self.github_token == "your_github_token":
            return None
        return {"Authorization": f"token {self.github_token}"}
    
    def _request(self, path: str, query: Optional[str] = None, timeout: int = 15) -> Tuple[Optional[int], str]:
        """Low-level GET request to GitHub API"""
        target = BASE_URL + path
        if query and query != "":
            target = target + "?" + query

        headers = {
            "Accept": ACCEPT_HEADER,
            "User-Agent": USER_AGENT,
        }
        auth_headers = self._get_auth_headers()
        if auth_headers:
            headers.update(auth_headers)

        logger.debug("GitHub API GET: %s", target)
        try:
            r = requests.get(target, headers=headers, timeout=timeout)
            return r.status_code, r.text
        except requests.RequestException as e:
            logger.warning("HTTP request failed: %s", e)
            return None, str(e)

    def _build_query(self, opts: Dict[str, Any]) -> str:
        """Build query string for GitHub API"""
        parts: List[str] = []
        if opts.get("q"):
            parts.append("q=" + urllib.parse.quote_plus(opts["q"]))
        if opts.get("sort"):
            parts.append("sort=" + urllib.parse.quote_plus(str(opts["sort"])))
        if opts.get("order"):
            parts.append("order=" + urllib.parse.quote_plus(str(opts["order"])))
        parts.append("page=" + str(opts.get("page", 1)))
        parts.append("per_page=" + str(opts.get("per_page", 30)))
        return "&".join(parts)

    def search_repositories(self, opts: Optional[Dict[str, Any]] = None) -> Tuple[Optional[Dict[str, Any]], Optional[Any]]:
        """Search GitHub repositories"""
        opts = opts or {}
        query = self._build_query(opts)
        code, body = self._request("/search/repositories", query)
        if code != 200:
            logger.warning("GitHub search error: %s %s", code, body)
            return None, {"code": code, "body": body}
        try:
            parsed = json.loads(body)
        except Exception as e:
            logger.warning("GitHub search decode error: %s", e)
            return None, "decode"
        return parsed, None

    def _repo_unique_key(self, repo: Dict[str, Any]) -> Optional[str]:
        """Build deduplication key for repository"""
        if not repo:
            return None
        if repo.get("full_name"):
            return str(repo["full_name"])
        if repo.get("id"):
            return str(repo["id"])
        if repo.get("name"):
            return str(repo["name"])
        return None

    def _append_unique_repo(self, target: List[Dict[str, Any]], seen: Dict[str, bool], repo: Dict[str, Any]):
        """Append repository to target list if not already seen"""
        key = self._repo_unique_key(repo)
        if not key or key in seen:
            return
        seen[key] = True
        target.append(repo)

    def _fetch_by_queries(self, kind_label: str, queries: List[str], opts: Dict[str, Any], collected: List[Dict[str, Any]], seen: Dict[str, bool]):
        """Fetch repositories by name queries"""
        if not queries:
            return
        per_page = opts.get("per_page", 100)
        sort = opts.get("sort", "stars")
        order = opts.get("order", "desc")

        for query in queries:
            if not query or query == "":
                continue
            page = 1
            while True:
                request_opts = {
                    "q": query,
                    "per_page": per_page,
                    "sort": sort,
                    "order": order,
                    "page": page
                }
                response, err = self.search_repositories(request_opts)
                if not response:
                    # GitHub caps search results at 1000; treat 422 as end of pagination
                    if isinstance(err, dict) and err.get("code") == 422:
                        logger.warning("%s query hit GitHub 1000-result cap (%s), stopping pagination", kind_label, query)
                        break
                    body = err.get("body") if isinstance(err, dict) else err
                    raise RuntimeError(f"{kind_label} query failed ({query}): {body}")
                items = response.get("items", [])
                if not items:
                    break
                for repo in items:
                    self._append_unique_repo(collected, seen, repo)
                if len(items) < per_page:
                    break
                page += 1

    def fetch_repositories(self, kind: str) -> List[Dict[str, Any]]:
        """
        Fetch repositories of a specific kind (plugin or patch)

        Args:
            kind: "plugin" or "patch"

        Returns:
            List of repository objects
        """
        collected: List[Dict[str, Any]] = []
        seen: Dict[str, bool] = {}

        if kind == "plugin":
            topics = PLUGIN_TOPICS
            name_queries = PLUGIN_NAME_QUERIES
            label = "Plugin"
        elif kind == "patch":
            topics = PATCH_TOPICS
            name_queries = PATCH_NAME_QUERIES
            label = "Patch"
        else:
            raise ValueError(f"Unknown kind: {kind}")

        # Topic-based search
        if topics:
            parts = []
            for t in topics:
                if t and t != "":
                    parts.append(f"topic:{t}")
            parts.append("fork:true")
            topic_query = " ".join(parts)

            per_page = 100
            sort = "stars"
            order = "desc"
            page = 1
            while True:
                request_opts = {
                    "q": topic_query,
                    "per_page": per_page,
                    "sort": sort,
                    "order": order,
                    "page": page
                }
                response, err = self.search_repositories(request_opts)
                if not response:
                    # GitHub caps search results at 1000; treat 422 as end of pagination
                    if isinstance(err, dict) and err.get("code") == 422:
                        logger.warning("%s topic search hit GitHub 1000-result cap, stopping pagination", label)
                        break
                    body = err.get("body") if isinstance(err, dict) else err
                    raise RuntimeError(f"{label} topic search failed ({topic_query}): {body}")
                items = response.get("items", [])
                if not items:
                    break
                for repo in items:
                    self._append_unique_repo(collected, seen, repo)
                if len(items) < per_page:
                    break
                page += 1

        # Name-based queries
        if name_queries:
            self._fetch_by_queries(label, name_queries, {"per_page": 100, "sort": "stars", "order": "desc"}, collected, seen)

        logger.info(f"Fetched {len(collected)} {kind} repositories")
        return collected

    def filter_patch_repos_only(self, repos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter patch repositories to only include actual patch repos, not individual patches
        """
        filtered = []
        for repo in repos:
            name = (repo.get("name") or "").lower()
            description = (repo.get("description") or "").lower()

            is_patch_repo = (
                "koreader.patches" in name or
                "patch" in name or
                "patches" in name or
                "koreader-patches" in name or
                any(keyword in description for keyword in ["patch", "patches", "koreader patches"])
            )

            is_individual_patch = (
                name.endswith(".patch") or
                name.endswith(".diff") or
                "fix-" in name or
                "add-" in name and len(name.split("-")) > 2
            )

            if is_patch_repo and not is_individual_patch:
                filtered.append(repo)

        logger.info(f"Filtered {len(repos)} patch repos to {len(filtered)} actual patch repositories")
        return filtered

    def get_repository_readme(self, owner: str, repo: str) -> str:
        """Get README content from a repository"""
        path = f"/repos/{owner}/{repo}/readme"
        code, body = self._request(path)
        if code != 200:
            logger.warning("GitHub fetch README error %s/%s %s", owner, repo, code)
            return ""

        try:
            data = json.loads(body)
            import base64
            content = base64.b64decode(data['content']).decode('utf-8')
            return content
        except Exception as e:
            logger.warning("GitHub README decode error: %s", e)
            return ""

    def get_repository_contents(self, owner: str, repo: str, path: str = "") -> List[Dict[str, Any]]:
        """Get repository contents (file tree)"""
        api_path = f"/repos/{owner}/{repo}/contents"
        if path:
            api_path = f"/repos/{owner}/{repo}/contents/{path}"

        code, body = self._request(api_path)
        if code != 200:
            logger.warning("GitHub fetch contents error %s/%s/%s %s", owner, repo, path, code)
            return []

        try:
            data = json.loads(body)
            if isinstance(data, dict):
                return [data]
            return data
        except Exception as e:
            logger.warning("GitHub contents decode error: %s", e)
            return []

    def get_patch_files(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """
        List the installable patch files in a patch repository.

        Walks the repository contents and returns files that look like
        patches (``.patch``/``.diff``/``.lua``/``.sh`` extensions or "patch"
        in the name), each as a dict with ``name``, ``path`` and
        ``download_url`` ready for direct download.
        """
        patch_extensions = (".patch", ".diff", ".lua", ".sh")
        contents = self.get_repository_contents(owner, repo)

        files: List[Dict[str, Any]] = []
        for item in contents:
            if item.get("type") != "file":
                continue
            name = item.get("name", "")
            lower = name.lower()
            if lower.endswith(patch_extensions) or "patch" in lower:
                files.append({
                    "name": name,
                    "path": item.get("path", name),
                    "download_url": item.get("download_url"),
                })

        logger.info("Found %d patch file(s) in %s/%s", len(files), owner, repo)
        return files

    def download_repository_zip(
        self,
        owner: str,
        repo: str,
        ref: str = "HEAD",
        timeout: int = 60,
    ) -> bytes:
        """
        Download a repository as a ZIP archive.

        Uses GitHub's zipball endpoint which returns a redirect to the
        actual archive.  ``requests`` follows the redirect automatically.

        Args:
            owner:   Repository owner (GitHub username or org).
            repo:    Repository name.
            ref:     Git ref to download — branch name, tag, or commit SHA.
                     Defaults to ``"HEAD"`` (the default branch).
            timeout: Request timeout in seconds (archives can be large).

        Returns:
            Raw ZIP bytes, ready to pass to ``PluginInstaller.install_plugin_from_zip()``.

        Raises:
            RuntimeError: If the download fails or returns a non-200 status.
        """
        url = f"{BASE_URL}/repos/{owner}/{repo}/zipball/{ref}"

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        }
        auth_headers = self._get_auth_headers()
        if auth_headers:
            headers.update(auth_headers)

        logger.info("Downloading ZIP for %s/%s @ %s", owner, repo, ref)

        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True,   # GitHub redirects to S3/CDN
                stream=True,            # Don't load the whole file into memory at once
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Network error downloading {owner}/{repo}: {exc}") from exc

        if response.status_code != 200:
            raise RuntimeError(
                f"GitHub returned HTTP {response.status_code} for {owner}/{repo} zipball.\n"
                f"Response: {response.text[:200]}"
            )

        # Read streamed response into bytes
        chunks = []
        total = 0
        for chunk in response.iter_content(chunk_size=65536):
            if chunk:
                chunks.append(chunk)
                total += len(chunk)

        data = b"".join(chunks)
        logger.info("Downloaded %s/%s ZIP: %.1f KB", owner, repo, total / 1024)
        return data

    def get_latest_release_zip(
        self,
        owner: str,
        repo: str,
        timeout: int = 60,
    ) -> bytes:
        """
        Download the ZIP from the latest GitHub Release (if one exists),
        falling back to the default-branch zipball if there are no releases.

        This is preferable to ``download_repository_zip`` for plugins that
        publish proper releases, as it gives you the tagged stable version.
        """
        # Try to find the latest release's zipball asset
        code, body = self._request(f"/repos/{owner}/{repo}/releases/latest")
        if code == 200:
            try:
                release = json.loads(body)
                tag = release.get("tag_name")
                if tag:
                    logger.info("Found latest release %s for %s/%s", tag, owner, repo)
                    return self.download_repository_zip(owner, repo, ref=tag, timeout=timeout)
            except Exception as exc:
                logger.warning("Could not parse release info for %s/%s: %s", owner, repo, exc)

        # No releases — fall back to HEAD
        logger.info("No releases found for %s/%s, downloading HEAD", owner, repo)
        return self.download_repository_zip(owner, repo, timeout=timeout)

    def get_latest_release(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for the latest GitHub release of a repository.

        Returns the parsed release object (with ``tag_name``, ``body``,
        ``published_at``, ``assets`` …), or ``None`` if the repository has
        no releases or the request fails.
        """
        code, body = self._request(f"/repos/{owner}/{repo}/releases/latest")
        if code != 200:
            logger.debug("No latest release for %s/%s (HTTP %s)", owner, repo, code)
            return None
        try:
            return json.loads(body)
        except Exception as e:
            logger.warning("GitHub release decode error %s/%s: %s", owner, repo, e)
            return None

    def get_repository_commits(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """
        Get information about the most recent commit on a repository.

        Returns a dict with ``latest_commit`` (SHA) and ``latest_commit_date``
        (ISO 8601 string), or ``None`` if no commits are found or the request
        fails.
        """
        code, body = self._request(f"/repos/{owner}/{repo}/commits", query="per_page=1")
        if code != 200:
            logger.debug("Could not fetch commits for %s/%s (HTTP %s)", owner, repo, code)
            return None
        try:
            commits = json.loads(body)
        except Exception as e:
            logger.warning("GitHub commits decode error %s/%s: %s", owner, repo, e)
            return None

        if not commits or not isinstance(commits, list):
            return None

        latest = commits[0]
        commit_date = (
            latest.get("commit", {}).get("committer", {}).get("date")
            or latest.get("commit", {}).get("author", {}).get("date")
        )
        if not commit_date:
            return None

        return {
            "latest_commit": latest.get("sha", ""),
            "latest_commit_date": commit_date,
        }

    def check_app_update(self, current_version: str) -> Optional[Dict[str, Any]]:
        """
        Check whether a newer KoStore release is available on GitHub.

        Returns a dict with ``latest_version`` and ``html_url`` when an
        update is available, or ``None`` when already up-to-date or when the
        check fails.
        """
        release = self.get_latest_release("ThePixelPro366", "KoStore")
        if not release:
            logger.debug("App update check: no release info returned")
            return None
        latest_tag = release.get("tag_name", "")
        if not latest_tag:
            return None
        if is_newer_version(current_version, latest_tag):
            logger.info("App update available: %s -> %s", current_version, latest_tag)
            return {
                "latest_version": latest_tag,
                "html_url": release.get(
                    "html_url",
                    "https://github.com/ThePixelPro366/KoStore/releases",
                ),
            }
        logger.debug("App update check: already up-to-date (%s)", current_version)
        return None