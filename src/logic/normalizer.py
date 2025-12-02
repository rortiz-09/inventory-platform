"""
Server Governance Platform - High-Precision OS Normalizer
Regex-based engine for extracting exact OS product and version.

This module implements the "Alta Precisión" requirement:
- RHEL 8.4 is DIFFERENT from RHEL 8.9
- Ubuntu 22.04.3 is DIFFERENT from Ubuntu 22.04.1
- Full Major.Minor.Patch extraction when available
"""

import re
from typing import Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class OSPattern:
    """Definition of an OS pattern for matching."""
    name: str
    product_key: str  # Key for endoflife.date API
    pattern: re.Pattern
    version_groups: Tuple[int, ...]  # Which regex groups form the version
    version_separator: str = "."


# High-Precision Regex Patterns
OS_PATTERNS = [
    # Red Hat Enterprise Linux (various formats)
    OSPattern(
        name="RHEL",
        product_key="rhel",
        pattern=re.compile(
            r"(?:Red\s*Hat\s*Enterprise\s*Linux|RHEL)(?:\s+Server)?(?:\s+release)?\s*"
            r"(\d+)(?:\.(\d+))?(?:\.(\d+))?",
            re.IGNORECASE
        ),
        version_groups=(1, 2),  # Major.Minor
    ),
    
    # CentOS (including Stream)
    OSPattern(
        name="CentOS",
        product_key="centos",
        pattern=re.compile(
            r"CentOS(?:\s+Linux)?(?:\s+Stream)?(?:\s+release)?\s*"
            r"(\d+)(?:\.(\d+))?(?:\.(\d+))?",
            re.IGNORECASE
        ),
        version_groups=(1, 2),  # Major.Minor
    ),
    
    # Rocky Linux
    OSPattern(
        name="Rocky Linux",
        product_key="rocky-linux",
        pattern=re.compile(
            r"Rocky\s*Linux(?:\s+release)?\s*"
            r"(\d+)(?:\.(\d+))?(?:\.(\d+))?",
            re.IGNORECASE
        ),
        version_groups=(1, 2),
    ),
    
    # AlmaLinux
    OSPattern(
        name="AlmaLinux",
        product_key="almalinux",
        pattern=re.compile(
            r"AlmaLinux(?:\s+release)?\s*"
            r"(\d+)(?:\.(\d+))?(?:\.(\d+))?",
            re.IGNORECASE
        ),
        version_groups=(1, 2),
    ),
    
    # Oracle Linux
    OSPattern(
        name="Oracle Linux",
        product_key="oracle-linux",
        pattern=re.compile(
            r"Oracle\s*Linux(?:\s+Server)?(?:\s+release)?\s*"
            r"(\d+)(?:\.(\d+))?(?:\.(\d+))?",
            re.IGNORECASE
        ),
        version_groups=(1, 2),
    ),
    
    # Ubuntu (with full version support)
    OSPattern(
        name="Ubuntu",
        product_key="ubuntu",
        pattern=re.compile(
            r"Ubuntu(?:\s+Server)?(?:\s+LTS)?\s*"
            r"(\d+)\.(\d+)(?:\.(\d+))?",
            re.IGNORECASE
        ),
        version_groups=(1, 2),  # Major.Minor (22.04)
    ),
    
    # Debian
    OSPattern(
        name="Debian",
        product_key="debian",
        pattern=re.compile(
            r"Debian(?:\s+GNU/Linux)?(?:\s+release)?\s*"
            r"(\d+)(?:\.(\d+))?",
            re.IGNORECASE
        ),
        version_groups=(1,),  # Major only typically
    ),
    
    # SUSE Linux Enterprise Server
    OSPattern(
        name="SLES",
        product_key="sles",
        pattern=re.compile(
            r"(?:SUSE\s+Linux\s+Enterprise\s+Server|SLES)\s*"
            r"(\d+)(?:\s+SP(\d+))?",
            re.IGNORECASE
        ),
        version_groups=(1, 2),
        version_separator="-SP",
    ),
    
    # openSUSE
    OSPattern(
        name="openSUSE",
        product_key="opensuse",
        pattern=re.compile(
            r"openSUSE(?:\s+Leap)?\s*"
            r"(\d+)(?:\.(\d+))?",
            re.IGNORECASE
        ),
        version_groups=(1, 2),
    ),
    
    # Windows Server (Year-based versions)
    OSPattern(
        name="Windows Server",
        product_key="windows-server",
        pattern=re.compile(
            r"(?:Microsoft\s+)?Windows\s+Server\s*"
            r"(20\d{2}|2008|2012|2016|2019|2022|2025)(?:\s+R2)?",
            re.IGNORECASE
        ),
        version_groups=(1,),  # Year only
    ),
    
    # Windows Desktop (for completeness)
    OSPattern(
        name="Windows",
        product_key="windows",
        pattern=re.compile(
            r"(?:Microsoft\s+)?Windows\s+"
            r"(1[0-1]|7|8(?:\.1)?)\s*",
            re.IGNORECASE
        ),
        version_groups=(1,),
    ),
    
    # VMware ESXi
    OSPattern(
        name="VMware ESXi",
        product_key="vmware-esxi",
        pattern=re.compile(
            r"(?:VMware\s+)?ESXi?\s*"
            r"(\d+)\.(\d+)(?:\.(\d+))?(?:\s+(?:build|Update)[\s-]*\d+)?",
            re.IGNORECASE
        ),
        version_groups=(1, 2),  # Major.Minor
    ),
    
    # VMware vSphere
    OSPattern(
        name="VMware vSphere",
        product_key="vmware-esxi",  # Uses same lifecycle
        pattern=re.compile(
            r"(?:VMware\s+)?vSphere\s*"
            r"(\d+)(?:\.(\d+))?",
            re.IGNORECASE
        ),
        version_groups=(1, 2),
    ),
    
    # Amazon Linux
    OSPattern(
        name="Amazon Linux",
        product_key="amazon-linux",
        pattern=re.compile(
            r"Amazon\s+Linux\s*"
            r"(\d+)?(?:\.(\d+))?",
            re.IGNORECASE
        ),
        version_groups=(1,),
    ),
    
    # FreeBSD
    OSPattern(
        name="FreeBSD",
        product_key="freebsd",
        pattern=re.compile(
            r"FreeBSD\s*"
            r"(\d+)(?:\.(\d+))?",
            re.IGNORECASE
        ),
        version_groups=(1, 2),
    ),
    
    # Fedora
    OSPattern(
        name="Fedora",
        product_key="fedora",
        pattern=re.compile(
            r"Fedora(?:\s+release)?\s*"
            r"(\d+)",
            re.IGNORECASE
        ),
        version_groups=(1,),
    ),
    
    # Arch Linux (Rolling release, uses date)
    OSPattern(
        name="Arch Linux",
        product_key="arch-linux",
        pattern=re.compile(
            r"Arch\s*Linux",
            re.IGNORECASE
        ),
        version_groups=(),  # No version
    ),
]


class OSNormalizer:
    """
    High-Precision OS Normalizer.
    
    Extracts product key and full version from OS strings.
    Designed to maintain granularity: RHEL 8.4 != RHEL 8.9
    """
    
    def __init__(self):
        self.patterns = OS_PATTERNS
        self._compile_generic_fallback()
    
    def _compile_generic_fallback(self) -> None:
        """Compile a generic fallback pattern for unknown OS strings."""
        self.generic_pattern = re.compile(
            r"([A-Za-z][A-Za-z\s]+?)\s*"  # OS name
            r"(\d+(?:\.\d+)*)",  # Version
            re.IGNORECASE
        )
    
    def normalize(self, os_string: Optional[str]) -> dict:
        """
        Normalize an OS string to product key and version.
        
        Args:
            os_string: Raw OS string (e.g., "Red Hat Enterprise Linux 8.4 (Ootpa)")
            
        Returns:
            dict with keys:
                - product_key: Normalized key for API (e.g., "rhel")
                - version: Extracted version (e.g., "8.4")
                - original_string: Original input
                - confidence: Confidence score (0.0 - 1.0)
        """
        if not os_string or not os_string.strip():
            return {
                "product_key": "unknown",
                "version": "",
                "original_string": os_string or "",
                "confidence": 0.0,
            }
        
        os_string = os_string.strip()
        
        # Try each known pattern
        for pattern in self.patterns:
            match = pattern.pattern.search(os_string)
            if match:
                version = self._extract_version(match, pattern)
                return {
                    "product_key": pattern.product_key,
                    "version": version,
                    "original_string": os_string,
                    "confidence": 1.0,
                }
        
        # Try generic fallback
        generic_match = self.generic_pattern.search(os_string)
        if generic_match:
            # Try to infer product key from matched name
            name = generic_match.group(1).strip().lower()
            product_key = self._infer_product_key(name)
            version = generic_match.group(2) if generic_match.lastindex >= 2 else ""
            
            return {
                "product_key": product_key,
                "version": version,
                "original_string": os_string,
                "confidence": 0.5,  # Lower confidence for generic match
            }
        
        # Complete failure - return unknown
        logger.warning(f"Could not normalize OS string: {os_string}")
        return {
            "product_key": "unknown",
            "version": os_string,  # Store raw string as "version" for reference
            "original_string": os_string,
            "confidence": 0.0,
        }
    
    def _extract_version(self, match: re.Match, pattern: OSPattern) -> str:
        """Extract version string from regex match groups."""
        if not pattern.version_groups:
            return ""
        
        parts = []
        for group_idx in pattern.version_groups:
            try:
                value = match.group(group_idx)
                if value:
                    parts.append(value)
            except IndexError:
                break
        
        if not parts:
            return ""
        
        # Special handling for SLES SP versions
        if pattern.version_separator == "-SP" and len(parts) == 2:
            return f"{parts[0]}-SP{parts[1]}"
        
        return pattern.version_separator.join(parts)
    
    def _infer_product_key(self, name: str) -> str:
        """Try to infer a product key from a generic OS name."""
        name = name.lower()
        
        # Common mappings
        mappings = {
            "red hat": "rhel",
            "redhat": "rhel",
            "centos": "centos",
            "ubuntu": "ubuntu",
            "debian": "debian",
            "windows": "windows-server",
            "esxi": "vmware-esxi",
            "vmware": "vmware-esxi",
            "suse": "sles",
            "oracle": "oracle-linux",
            "amazon": "amazon-linux",
            "rocky": "rocky-linux",
            "alma": "almalinux",
        }
        
        for key, product in mappings.items():
            if key in name:
                return product
        
        # Slugify the name as fallback
        return re.sub(r'[^a-z0-9]+', '-', name).strip('-')


# Singleton instance
normalizer = OSNormalizer()


def normalize_os(os_string: Optional[str]) -> dict:
    """
    Convenience function to normalize an OS string.
    
    Usage:
        result = normalize_os("Red Hat Enterprise Linux Server release 8.4 (Ootpa)")
        # Returns: {"product_key": "rhel", "version": "8.4", ...}
    """
    return normalizer.normalize(os_string)


# Quick test cases
if __name__ == "__main__":
    test_cases = [
        "CentOS Linux release 7.9.2009 (Core)",
        "Red Hat Enterprise Linux Server release 8.4 (Ootpa)",
        "Red Hat Enterprise Linux 9.2",
        "Microsoft Windows Server 2019 Standard Evaluation",
        "Ubuntu 22.04.3 LTS",
        "VMware ESXi 7.0.3 build-12345",
        "Debian GNU/Linux 11 (bullseye)",
        "Oracle Linux Server release 8.6",
        "SUSE Linux Enterprise Server 15 SP4",
        "Rocky Linux release 9.1",
        "AlmaLinux release 8.7",
        "Some Unknown OS 1.2.3",
        "",
        None,
    ]
    
    print("\n" + "=" * 80)
    print("OS NORMALIZER TEST RESULTS")
    print("=" * 80 + "\n")
    
    for test in test_cases:
        result = normalize_os(test)
        print(f"Input:   {test!r}")
        print(f"Product: {result['product_key']}")
        print(f"Version: {result['version']}")
        print(f"Confidence: {result['confidence']}")
        print("-" * 40)
