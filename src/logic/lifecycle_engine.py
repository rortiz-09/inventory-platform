"""
Server Governance Platform - Lifecycle Engine
Intelligent EOL lookup with API integration and smart caching.

This module implements the "Auto-Didacta" requirement:
- Fetches lifecycle data from endoflife.date API
- Intelligent cycle matching (8.4 -> cycle 8 if no exact match)
- Persistent caching in DuckDB
"""

import httpx
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
import asyncio

logger = logging.getLogger(__name__)

# API Configuration
ENDOFLIFE_API_BASE = "https://endoflife.date/api"
CACHE_TTL_DAYS = 7  # Refresh cache after 7 days


class LifecycleEngine:
    """
    Intelligent Lifecycle Engine for OS EOL lookup.
    
    Features:
    - API integration with endoflife.date
    - Smart cycle matching (minor version to major cycle)
    - Persistent caching in DuckDB
    - Async-ready for batch operations
    """
    
    def __init__(self, db_connection=None):
        """
        Initialize the lifecycle engine.
        
        Args:
            db_connection: DuckDB connection (optional, will use default if None)
        """
        self._db = db_connection
        self._http_client: Optional[httpx.Client] = None
    
    @property
    def db(self):
        """Lazy load database connection."""
        if self._db is None:
            from src.core.database import get_db
            self._db = get_db()
        return self._db
    
    @property
    def http_client(self) -> httpx.Client:
        """Lazy load HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.Client(
                base_url=ENDOFLIFE_API_BASE,
                timeout=30.0,
                headers={"Accept": "application/json"},
            )
        return self._http_client
    
    def get_lifecycle_info(
        self,
        product_key: str,
        version: str,
        force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get lifecycle information for a product/version pair.
        
        Args:
            product_key: Normalized product key (e.g., "rhel")
            version: Version string (e.g., "8.4")
            force_refresh: Skip cache and fetch from API
            
        Returns:
            Dict with lifecycle info or None if not found
        """
        if not product_key or product_key == "unknown":
            return None
        
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached = self._get_from_cache(product_key, version)
            if cached:
                logger.debug(f"Cache hit for {product_key} {version}")
                return cached
        
        # Fetch from API
        logger.info(f"Fetching lifecycle data for {product_key} from API")
        cycles = self._fetch_product_cycles(product_key)
        
        if not cycles:
            return None
        
        # Find matching cycle
        lifecycle = self._match_cycle(cycles, version)
        
        if lifecycle:
            # Persist to cache
            self._save_to_cache(product_key, lifecycle)
            return lifecycle
        
        return None
    
    def _get_from_cache(
        self,
        product_key: str,
        version: str
    ) -> Optional[Dict[str, Any]]:
        """Check cache for lifecycle data."""
        try:
            # First try exact version match
            result = self.db.execute("""
                SELECT cycle, eol_date, latest_version, support_ended, lts, last_updated
                FROM os_lifecycle_cache
                WHERE product_key = ?
                  AND cycle = ?
                  AND last_updated > ?
            """, [
                product_key,
                version,
                datetime.now() - timedelta(days=CACHE_TTL_DAYS)
            ]).fetchone()
            
            if result:
                return self._row_to_lifecycle(product_key, result)
            
            # Try major version match (8.4 -> 8)
            major_version = version.split('.')[0] if version else None
            if major_version and major_version != version:
                result = self.db.execute("""
                    SELECT cycle, eol_date, latest_version, support_ended, lts, last_updated
                    FROM os_lifecycle_cache
                    WHERE product_key = ?
                      AND cycle = ?
                      AND last_updated > ?
                """, [
                    product_key,
                    major_version,
                    datetime.now() - timedelta(days=CACHE_TTL_DAYS)
                ]).fetchone()
                
                if result:
                    return self._row_to_lifecycle(product_key, result)
            
            return None
            
        except Exception as e:
            logger.error(f"Cache lookup error: {e}")
            return None
    
    def _fetch_product_cycles(self, product_key: str) -> Optional[List[Dict]]:
        """Fetch all cycles for a product from API."""
        try:
            response = self.http_client.get(f"/{product_key}.json")
            
            if response.status_code == 404:
                logger.warning(f"Product not found in API: {product_key}")
                return None
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"API request failed for {product_key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {product_key}: {e}")
            return None
    
    def _match_cycle(
        self,
        cycles: List[Dict],
        version: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best matching cycle for a version.
        
        Strategy:
        1. Try exact match (version == cycle)
        2. Try major.minor match
        3. Fall back to major version match
        """
        if not cycles or not version:
            return None
        
        # Parse version components
        version_parts = version.replace('-', '.').split('.')
        major = version_parts[0] if version_parts else None
        minor = version_parts[1] if len(version_parts) > 1 else None
        
        # Build search strings
        search_versions = [version]  # Exact version first
        
        if major and minor:
            # Add Major.Minor format
            search_versions.append(f"{major}.{minor}")
        
        if major:
            # Add Major only as fallback
            search_versions.append(major)
        
        # Search for matching cycle
        for search in search_versions:
            for cycle in cycles:
                cycle_name = str(cycle.get('cycle', ''))
                if cycle_name.lower() == search.lower():
                    return self._parse_cycle(cycle)
        
        # No match found - return first cycle as fallback (usually latest)
        if cycles:
            logger.warning(f"No exact cycle match for {version}, using first available")
            return self._parse_cycle(cycles[0])
        
        return None
    
    def _parse_cycle(self, cycle: Dict) -> Dict[str, Any]:
        """Parse API cycle response into standard format."""
        eol = cycle.get('eol')
        eol_date = None
        is_eol = False
        days_until_eol = None
        
        if eol is True:
            is_eol = True
        elif eol is False:
            is_eol = False
        elif isinstance(eol, str):
            try:
                eol_date = date.fromisoformat(eol)
                is_eol = eol_date < date.today()
                days_until_eol = (eol_date - date.today()).days
            except ValueError:
                pass
        
        return {
            "cycle": str(cycle.get('cycle', '')),
            "eol_date": eol_date,
            "is_eol": is_eol,
            "days_until_eol": days_until_eol,
            "latest_version": cycle.get('latest'),
            "release_date": self._parse_date(cycle.get('releaseDate')),
            "lts": cycle.get('lts', False),
            "support_ended": cycle.get('support') is True or (
                isinstance(cycle.get('support'), str) and 
                date.fromisoformat(cycle.get('support')) < date.today()
            ),
        }
    
    def _parse_date(self, date_str: Any) -> Optional[date]:
        """Parse a date string safely."""
        if not date_str or date_str is True or date_str is False:
            return None
        try:
            return date.fromisoformat(str(date_str))
        except (ValueError, TypeError):
            return None
    
    def _save_to_cache(self, product_key: str, lifecycle: Dict[str, Any]) -> None:
        """Save lifecycle data to cache."""
        try:
            self.db.execute("""
                INSERT INTO os_lifecycle_cache (
                    product_key, cycle, eol_date, latest_version, 
                    release_date, support_ended, lts, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (product_key, cycle) 
                DO UPDATE SET
                    eol_date = EXCLUDED.eol_date,
                    latest_version = EXCLUDED.latest_version,
                    release_date = EXCLUDED.release_date,
                    support_ended = EXCLUDED.support_ended,
                    lts = EXCLUDED.lts,
                    last_updated = EXCLUDED.last_updated
            """, [
                product_key,
                lifecycle['cycle'],
                lifecycle.get('eol_date'),
                lifecycle.get('latest_version'),
                lifecycle.get('release_date'),
                lifecycle.get('support_ended', False),
                lifecycle.get('lts', False),
                datetime.now(),
            ])
            logger.debug(f"Cached lifecycle for {product_key} cycle {lifecycle['cycle']}")
        except Exception as e:
            logger.error(f"Cache save error: {e}")
    
    def _row_to_lifecycle(
        self,
        product_key: str,
        row: tuple
    ) -> Dict[str, Any]:
        """Convert database row to lifecycle dict."""
        cycle, eol_date, latest_version, support_ended, lts, last_updated = row
        
        is_eol = False
        days_until_eol = None
        
        if eol_date:
            if isinstance(eol_date, str):
                eol_date = date.fromisoformat(eol_date)
            is_eol = eol_date < date.today()
            days_until_eol = (eol_date - date.today()).days
        
        return {
            "product_key": product_key,
            "cycle": cycle,
            "eol_date": eol_date,
            "is_eol": is_eol,
            "days_until_eol": days_until_eol,
            "latest_version": latest_version,
            "support_ended": support_ended,
            "lts": lts,
            "last_updated": last_updated,
        }
    
    def refresh_cache(self, product_keys: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Refresh cache for specified products or all cached products.
        
        Returns:
            Dict with counts: {"updated": N, "failed": M}
        """
        stats = {"updated": 0, "failed": 0}
        
        if product_keys is None:
            # Get all cached products
            result = self.db.execute(
                "SELECT DISTINCT product_key FROM os_lifecycle_cache"
            ).fetchall()
            product_keys = [row[0] for row in result]
        
        for product_key in product_keys:
            cycles = self._fetch_product_cycles(product_key)
            if cycles:
                for cycle in cycles:
                    lifecycle = self._parse_cycle(cycle)
                    self._save_to_cache(product_key, lifecycle)
                    stats["updated"] += 1
            else:
                stats["failed"] += 1
        
        logger.info(f"Cache refresh complete: {stats}")
        return stats
    
    def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            self._http_client.close()
            self._http_client = None


# Singleton instance
_engine: Optional[LifecycleEngine] = None


def get_lifecycle_engine() -> LifecycleEngine:
    """Get or create the lifecycle engine singleton."""
    global _engine
    if _engine is None:
        _engine = LifecycleEngine()
    return _engine


def get_eol_info(product_key: str, version: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to get EOL info.
    
    Usage:
        info = get_eol_info("rhel", "8.4")
        if info and info['is_eol']:
            print(f"EOL since {info['eol_date']}")
    """
    return get_lifecycle_engine().get_lifecycle_info(product_key, version)


# Quick test
if __name__ == "__main__":
    import sys
    
    # Test the engine
    engine = LifecycleEngine()
    
    test_cases = [
        ("rhel", "8.4"),
        ("rhel", "9"),
        ("ubuntu", "22.04"),
        ("windows-server", "2019"),
        ("vmware-esxi", "7.0"),
        ("centos", "7"),
    ]
    
    print("\n" + "=" * 80)
    print("LIFECYCLE ENGINE TEST RESULTS")
    print("=" * 80 + "\n")
    
    for product, version in test_cases:
        print(f"\nLooking up: {product} {version}")
        try:
            info = engine.get_lifecycle_info(product, version)
            if info:
                print(f"  Cycle: {info['cycle']}")
                print(f"  EOL Date: {info['eol_date']}")
                print(f"  Is EOL: {info['is_eol']}")
                print(f"  Days until EOL: {info['days_until_eol']}")
            else:
                print("  No lifecycle info found")
        except Exception as e:
            print(f"  Error: {e}")
    
    engine.close()
