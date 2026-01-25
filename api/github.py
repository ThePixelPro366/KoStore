"""
GitHub API Handler for KOReader Plugins and Patches
"""

import requests
import logging

logger = logging.getLogger(__name__)


class GitHubAPI:
    """GitHub API Handler for KOReader Plugins and Patches"""
    
    def __init__(self, token=None):
        logger.info("Initializing GitHub API")
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"
            logger.info("GitHub API initialized with authentication token")
        else:
            logger.info("GitHub API initialized without authentication token")
    
    def is_fast_path_valid_plugin(self, repo_data):
        """
        Fast-path validation for KOReader repositories.
        Returns True immediately for clearly valid KOReader repos without file checks.
        """
        name = repo_data.get("name", "").lower()
        description = (repo_data.get("description") or "").lower()
        topics = repo_data.get("topics", [])
        
        # Fast-path 1: Name patterns that are clearly KOReader plugins
        if (name.endswith(".koplugin") or 
            "koplugin" in name or 
            name.endswith(".patch") or
            "koreader.patches" in name.lower() or
            "koreader" in name):
            logger.debug(f"Fast-path valid: {name} (name pattern)")
            return True
        
        # Fast-path 2: Topic-based validation
        if any(topic in topics for topic in ["koreader-plugin", "koreader-user-patch", "koreader"]):
            logger.debug(f"Fast-path valid: {name} (topic: {topics})")
            return True
        
        # Fast-path 3: Description mentions KOReader
        if "koreader" in description:
            logger.debug(f"Fast-path valid: {name} (description mentions KOReader)")
            return True
        
        return False

    def has_required_plugin_files(self, owner, repo):
        """
        Check if repository has required KOReader plugin files.
        KOReader plugins can have different structures:
        1. Files in root directory (_meta.lua + main.lua)
        2. Files in a subdirectory (e.g., pluginname.koplugin/_meta.lua + pluginname.koplugin/main.lua)
        3. Alternative meta file names (manifest.lua instead of _meta.lua)
        """
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/contents"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            files = response.json()
            file_names = [file["name"] for file in files]
            
            # Check if files are in root directory
            has_main_lua_root = "main.lua" in file_names
            has_meta_lua_root = "_meta.lua" in file_names
            has_manifest_lua_root = "manifest.lua" in file_names
            
            # If both files are in root, it's valid
            if has_main_lua_root and (has_meta_lua_root or has_manifest_lua_root):
                logger.debug(f"{owner}/{repo}: Valid plugin with files in root")
                return True
            
            # Check subdirectories for plugin structure
            for file in files:
                if file["type"] == "dir":
                    # Check if this subdirectory contains the required files
                    sub_url = f"{self.base_url}/repos/{owner}/{repo}/contents/{file['name']}"
                    try:
                        sub_response = requests.get(sub_url, headers=self.headers, timeout=10)
                        sub_response.raise_for_status()
                        sub_files = sub_response.json()
                        sub_file_names = [f["name"] for f in sub_files]
                        
                        sub_has_main = "main.lua" in sub_file_names
                        sub_has_meta = "_meta.lua" in sub_file_names
                        sub_has_manifest = "manifest.lua" in sub_file_names
                        
                        if sub_has_main and (sub_has_meta or sub_has_manifest):
                            logger.debug(f"{owner}/{repo}: Valid plugin with files in {file['name']}/")
                            return True
                            
                    except Exception as e:
                        logger.debug(f"Failed to check subdirectory {file['name']}: {e}")
                        continue
            
            # Check for split structure (main.lua in root, meta in subdirectory)
            if has_main_lua_root:
                for file in files:
                    if file["type"] == "dir":
                        sub_url = f"{self.base_url}/repos/{owner}/{repo}/contents/{file['name']}"
                        try:
                            sub_response = requests.get(sub_url, headers=self.headers, timeout=10)
                            sub_response.raise_for_status()
                            sub_files = sub_response.json()
                            sub_file_names = [f["name"] for f in sub_files]
                            
                            if "_meta.lua" in sub_file_names or "manifest.lua" in sub_file_names:
                                logger.debug(f"{owner}/{repo}: Valid plugin with split structure")
                                return True
                                
                        except Exception as e:
                            continue
            
            logger.debug(f"{owner}/{repo}: No valid plugin structure found")
            return False
            
        except Exception as e:
            logger.debug(f"Failed to check files for {owner}/{repo}: {e}")
            return False

    def is_valid_plugin_repo(self, owner, repo):
        """
        More lenient validation - follow KOReader's approach
        KOReader validates during installation, not during search
        """
        # KOReader's approach: almost no validation during search
        # They rely on topic: koreader-plugin and name patterns
        # Real validation happens when downloading/installing
        
        # Only filter out obvious non-plugins - be much more lenient
        try:
            # Skip the expensive API call for now - just check name patterns
            name = repo.lower()
            
            # If it has plugin-related keywords, assume it's valid
            if any(keyword in name for keyword in ["koplugin", "plugin", "plugins"]):
                return True
            
            # If it has koreader topic, assume it's valid
            # (This would be checked in search results)
            return True
            
        except Exception as e:
            logger.debug(f"Skipping validation for {owner}/{repo}: {e}")
            # If we can't check, assume it's valid (KOReader's approach)
            return True

    def search_repositories(self, topic=None, name_patterns=None):
        queries = []

        if topic:
            queries.append(f"topic:{topic}")

        if name_patterns:
            for pattern in name_patterns:
                queries.append(f"{pattern} in:name")

        all_results = []
        seen = set()

        for q in queries:
            url = f"{self.base_url}/search/repositories"
            params = {
                "q": q,
                "per_page": 100,
                "sort": "stars",
                "order": "desc"
            }

            try:
                r = requests.get(url, headers=self.headers, params=params, timeout=10)
                r.raise_for_status()

                for repo in r.json().get("items", []):
                    if repo["id"] in seen:
                        continue

                    seen.add(repo["id"])

                    name = repo["name"].lower()

                    if (
                        "koplugin" in name
                        or name.endswith("plugin")
                        or name.endswith("plugins")
                    ):
                        repo["repo_type"] = "plugin"

                    elif (
                        "patch" in name
                        or "patches" in name
                    ):
                        repo["repo_type"] = "patch"

                    else:
                        continue  # Müll rausfiltern

                    # Validate plugins - use fast-path validation only (no expensive file checks)
                    if repo.get("repo_type") == "plugin":
                        owner = repo["owner"]["login"]
                        repo_name = repo["name"]
                        
                        # Only validate based on name patterns and topics - skip expensive file checks
                        if not self.is_fast_path_valid_plugin(repo):
                            logger.info(f"Filtering out plugin: {owner}/{repo_name} (not KOReader-related)")
                            continue  # Skip plugins that don't match KOReader patterns

                    all_results.append(repo)

            except Exception as e:
                logger.error(f"GitHub search failed for '{q}': {e}")

        return all_results

    
    def get_repository_readme(self, owner, repo):
        """Get README content from a repository with fallback mechanisms"""
        logger.info(f"Fetching README for repository {owner}/{repo}")
        
        # Try different README filenames in order of preference
        readme_names = ["README.md", "README", "readme.md", "readme", "README.rst", "README.txt"]
        
        for readme_name in readme_names:
            url = f"{self.base_url}/repos/{owner}/{repo}/contents/{readme_name}"
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                readme_data = response.json()
                
                # Download raw content
                content_url = readme_data.get("download_url")
                if content_url:
                    logger.debug(f"Downloading {readme_name} from: {content_url}")
                    content_response = requests.get(content_url, timeout=10)
                    content_response.raise_for_status()
                    logger.info(f"Successfully fetched {readme_name} for {owner}/{repo}")
                    
                    # Process content to handle relative image paths
                    content = content_response.text
                    content = self._process_image_paths(content, owner, repo)
                    
                    return content
                else:
                    # Try to get content directly if it's small
                    content = readme_data.get("content")
                    if content:
                        import base64
                        try:
                            decoded_content = base64.b64decode(content).decode('utf-8')
                            # Process content to handle relative image paths
                            decoded_content = self._process_image_paths(decoded_content, owner, repo)
                            logger.info(f"Successfully fetched {readme_name} for {owner}/{repo}")
                            return decoded_content
                        except Exception as decode_error:
                            logger.warning(f"Failed to decode {readme_name} content: {decode_error}")
                            
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    # Try next README filename
                    continue
                else:
                    logger.error(f"HTTP error fetching {readme_name} for {owner}/{repo}: {e}")
                    return f"README not available (HTTP {e.response.status_code})"
            except requests.exceptions.RequestException as e:
                logger.error(f"Network error fetching {readme_name} for {owner}/{repo}: {e}")
                return "README not available (network error)"
            except Exception as e:
                logger.error(f"Unexpected error fetching {readme_name} for {owner}/{repo}: {e}")
                continue
        
        # If all README attempts failed, try the GitHub API readme endpoint as last resort
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/readme"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            readme_data = response.json()
            
            content_url = readme_data.get("download_url")
            if content_url:
                logger.debug(f"Downloading README from GitHub API endpoint: {content_url}")
                content_response = requests.get(content_url, timeout=10)
                content_response.raise_for_status()
                logger.info(f"Successfully fetched README via API for {owner}/{repo}")
                
                # Process content to handle relative image paths
                content = content_response.text
                content = self._process_image_paths(content, owner, repo)
                
                return content
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"No README found for {owner}/{repo} (tried all options)")
                return "No README file found in this repository"
            else:
                logger.error(f"HTTP error fetching README via API for {owner}/{repo}: {e}")
                return f"README not available (HTTP {e.response.status_code})"
        except Exception as e:
            logger.error(f"Error fetching README via API for {owner}/{repo}: {e}")
        
        logger.info(f"No README found for {owner}/{repo} after trying all options")
        return "No README file found in this repository"
    
    def get_latest_release(self, owner, repo):
        """Get the latest release information for a repository"""
        logger.info(f"Getting latest release for {owner}/{repo}")
        
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/releases/latest"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            release_data = response.json()
            
            return {
                "tag_name": release_data.get("tag_name", ""),
                "name": release_data.get("name", ""),
                "published_at": release_data.get("published_at", ""),
                "body": release_data.get("body", ""),
                "html_url": release_data.get("html_url", ""),
                "assets": release_data.get("assets", [])
            }
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"No releases found for {owner}/{repo}")
                return None
            else:
                logger.error(f"HTTP error getting releases for {owner}/{repo}: {e}")
                return None
        except Exception as e:
            logger.error(f"Error getting releases for {owner}/{repo}: {e}")
            return None
    
    def get_repository_commits(self, owner, repo, since=None):
        """Get recent commits for a repository as fallback for update checking"""
        logger.info(f"Getting recent commits for {owner}/{repo}")
        
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/commits"
            params = {
                "per_page": 10,
                "sort": "created",
                "direction": "desc"
            }
            
            if since:
                params["since"] = since
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            commits = response.json()
            
            if commits:
                return {
                    "latest_commit": commits[0]["sha"],
                    "latest_commit_date": commits[0]["commit"]["committer"]["date"],
                    "commit_count": len(commits)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting commits for {owner}/{repo}: {e}")
            return None
    
    def _process_image_paths(self, content, owner, repo):
        """Process README content to convert relative image paths to absolute GitHub URLs"""
        import re
        
        # Pattern to match markdown images: ![alt](path)
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        
        def replace_image(match):
            alt_text = match.group(1)
            image_path = match.group(2)
            
            # Skip if it's already an absolute URL
            if image_path.startswith(('http://', 'https://')):
                return match.group(0)
            
            # Convert relative path to GitHub raw URL
            github_base_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/"
            absolute_url = github_base_url + image_path.lstrip('/')
            
            return f'![{alt_text}]({absolute_url})'
        
        # Replace all relative image paths
        content = re.sub(image_pattern, replace_image, content)
        
        return content
    
    def download_repository_zip(self, owner, repo, branch="main"):
        """Download repository as ZIP, trying releases first then source code"""
        logger.info(f"Downloading {owner}/{repo} (branch: {branch})")
        
        # First, try to get releases and download the latest release ZIP
        try:
            logger.debug(f"Checking for releases of {owner}/{repo}")
            releases_url = f"{self.base_url}/repos/{owner}/{repo}/releases"
            response = requests.get(releases_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            releases = response.json()
            
            if releases and len(releases) > 0:
                latest_release = releases[0]  # Get the latest release
                for asset in latest_release.get("assets", []):
                    if asset.get("name", "").endswith(".zip"):
                        zip_url = asset["browser_download_url"]
                        logger.info(f"Found release ZIP: {asset['name']} ({zip_url})")
                        logger.debug(f"Downloading release ZIP from: {zip_url}")
                        response = requests.get(zip_url, stream=True, timeout=30)
                        response.raise_for_status()
                        content = response.content
                        logger.info(f"Successfully downloaded release ZIP ({len(content)} bytes)")
                        return content
                logger.info("No ZIP assets found in latest release")
            else:
                logger.info("No releases found for repository")
        except Exception as e:
            logger.warning(f"Failed to download release ZIP for {owner}/{repo}: {e}")
        
        # Fallback to source code archive
        try:
            logger.debug(f"Falling back to source archive for {owner}/{repo}")
            url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            content = response.content
            logger.info(f"Successfully downloaded source archive ({len(content)} bytes)")
            return content
        except Exception as e:
            logger.error(f"Failed to download source archive for {owner}/{repo}: {e}")
        
        # Try master branch as final fallback
        try:
            logger.debug(f"Trying master branch for {owner}/{repo}")
            url = f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip"
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            content = response.content
            logger.info(f"Successfully downloaded master branch archive ({len(content)} bytes)")
            return content
        except Exception as e:
            logger.error(f"Failed to download master branch for {owner}/{repo}: {e}")
        
        return None
    
    def get_repository_contents(self, owner, repo, path=""):
        """Get repository contents (files and directories)"""
        logger.info(f"Getting repository contents for {owner}/{repo}, path: {path}")
        
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            contents = response.json()
            
            # If it's a single file, return it in a list
            if isinstance(contents, dict):
                contents = [contents]
            
            # Recursively get contents for subdirectories
            for item in contents:
                if item.get('type') == 'dir':
                    try:
                        sub_path = f"{path}/{item['name']}" if path else item['name']
                        item['contents'] = self.get_repository_contents(owner, repo, sub_path)
                    except Exception as e:
                        logger.warning(f"Failed to get contents for subdirectory {item['name']}: {e}")
                        item['contents'] = []
            
            return contents
            
        except Exception as e:
            logger.error(f"Error getting repository contents for {owner}/{repo}: {e}")
            return []
    
    def get_patch_files(self, owner, repo):
        """Liste alle .lua Patch-Dateien"""
        url = f"{self.base_url}/repos/{owner}/{repo}/contents"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            files = response.json()
            patches = []
            for file in files:
                if file["name"].endswith(".lua") and file["name"][0].isdigit():
                    patches.append({
                        "name": file["name"],
                        "download_url": file["download_url"],
                        "sha": file["sha"]
                    })
            return patches
        except:
            return []
