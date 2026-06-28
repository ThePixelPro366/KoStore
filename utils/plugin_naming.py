"""
Helpers for deriving KOReader plugin folder names.
"""

import re


def derive_plugin_folder_name(found_dir_name: str, repo_name: str) -> str:
    """
    Work out the correct ``*.koplugin`` folder name for an installed plugin.

    GitHub zipball downloads extract to a top-level folder named
    ``<owner>-<repo>-<shortsha>`` (e.g. ``AndyHazz-bookends.koplugin-f0ea842``).
    Using that name verbatim produces broken folders like
    ``AndyHazz-bookends.koplugin-f0ea842.koplugin`` whose name changes with
    every commit, which both looks wrong and prevents update detection /
    overwriting.

    Strategy:
      * If ``found_dir_name`` already ends in ``.koplugin`` it is a genuine
        plugin directory (e.g. a real ``foo.koplugin/`` subfolder inside the
        repo) — use it as-is.
      * Otherwise ``found_dir_name`` is the zipball root (or some other plain
        folder), so derive a stable name from the repository name instead.

    Args:
        found_dir_name: Name of the directory located inside the extracted ZIP.
        repo_name:      The GitHub repository name (e.g. ``bookends.koplugin``).

    Returns:
        A clean folder name ending in ``.koplugin``.
    """
    if found_dir_name.endswith(".koplugin"):
        return found_dir_name

    # Fall back to the repository name. Strip a trailing zipball-style
    # "-<sha>" if one somehow slipped through, then normalise the suffix.
    base = repo_name.strip()
    if base.endswith(".koplugin"):
        return base
    # Guard against repo names that already carry a stray ".koplugin-<sha>".
    base = re.sub(r"\.koplugin-[0-9a-f]{5,}$", "", base)
    return f"{base}.koplugin"
