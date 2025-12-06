"""
Server Governance Platform - Logic Package
Intelligence engines for normalization, lifecycle, scoring, and classification.
"""

from .normalizer import normalize_os, OSNormalizer
from .lifecycle_engine import get_eol_info, get_lifecycle_engine, LifecycleEngine
from .health_score import calculate_health_score, calculate_server_health, HealthScoreResult
from .network_classifier import classify_ip, get_canonical_hostname, NetworkInfo

__all__ = [
    # Normalizer
    "normalize_os",
    "OSNormalizer",
    # Lifecycle
    "get_eol_info",
    "get_lifecycle_engine",
    "LifecycleEngine",
    # Health Score
    "calculate_health_score",
    "calculate_server_health",
    "HealthScoreResult",
    # Network
    "classify_ip",
    "get_canonical_hostname",
    "NetworkInfo",
]
