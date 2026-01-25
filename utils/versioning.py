"""
Version comparison utilities for KOReader Store
"""

import re
from typing import Tuple


def parse_version(version_str: str) -> Tuple[int, ...]:
    """
    Parse version string into a tuple of integers for comparison.
    
    Args:
        version_str: Version string like "1.2.3" or "v1.2.3"
        
    Returns:
        Tuple of integers representing the version
    """
    if not version_str:
        return (0, 0, 0)
    
    # Remove 'v' prefix if present
    version_str = version_str.lstrip('v')
    
    # Extract numeric parts
    numbers = re.findall(r'\d+', version_str)
    
    # Convert to integers and pad to at least 3 parts
    version_tuple = tuple(int(num) for num in numbers)
    
    # Pad with zeros to ensure consistent comparison
    while len(version_tuple) < 3:
        version_tuple = version_tuple + (0,)
    
    return version_tuple[:3]  # Limit to 3 parts (major.minor.patch)


def is_newer_version(current_version: str, new_version: str) -> bool:
    """
    Check if new_version is newer than current_version.
    
    Args:
        current_version: Current version string
        new_version: New version string to compare against
        
    Returns:
        True if new_version is newer, False otherwise
    """
    current = parse_version(current_version)
    new = parse_version(new_version)
    
    return new > current


def format_version_display(version_str: str) -> str:
    """
    Format version string for display.
    
    Args:
        version_str: Version string
        
    Returns:
        Formatted version string
    """
    if not version_str:
        return "Unknown"
    
    # Ensure version starts with 'v' for consistency
    if not version_str.startswith('v'):
        version_str = f"v{version_str}"
    
    return version_str
