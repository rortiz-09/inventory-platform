"""
Server Governance Platform - Network Classifier
IP-based environment and location classification.

Hardcoded subnet mappings as per business requirements:
- 192.168.59.0/24 → prod / gye
- 192.168.21.0/24 → prod / uio
- 192.168.77.0/24 → dev / shared
- 192.168.76.0/24 → test / shared
"""

import ipaddress
from typing import Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class NetworkInfo:
    """Network classification result."""
    ip_address: str
    environment: str  # prod, dev, test, unknown
    city: str  # gye, uio, shared, unknown
    subnet: str  # The matched subnet CIDR
    is_valid: bool  # Whether IP was valid and classified


# Hardcoded subnet mappings
NETWORK_MAP = {
    # Production networks
    "192.168.59.0/24": ("prod", "gye"),
    "192.168.21.0/24": ("prod", "uio"),
    
    # Development network
    "192.168.77.0/24": ("dev", "shared"),
    
    # Test network
    "192.168.76.0/24": ("test", "shared"),
    
    # Additional common ranges (extend as needed)
    "10.0.0.0/8": ("unknown", "unknown"),  # Broad internal range
    "172.16.0.0/12": ("unknown", "unknown"),  # Broad internal range
}


class NetworkClassifier:
    """
    Network classifier for IP addresses.
    
    Maps IP addresses to environment (prod/dev/test) and 
    location (gye/uio/shared) based on subnet.
    """
    
    def __init__(self):
        # Pre-compile network objects for faster matching
        self.networks = {}
        for cidr, (env, city) in NETWORK_MAP.items():
            try:
                self.networks[ipaddress.ip_network(cidr)] = (env, city)
            except ValueError as e:
                logger.error(f"Invalid network in config: {cidr} - {e}")
    
    def classify(self, ip_address: Optional[str]) -> NetworkInfo:
        """
        Classify an IP address into environment and location.
        
        Args:
            ip_address: IP address string (e.g., "192.168.59.100")
            
        Returns:
            NetworkInfo with classification result
        """
        if not ip_address or not ip_address.strip():
            return NetworkInfo(
                ip_address=ip_address or "",
                environment="unknown",
                city="unknown",
                subnet="",
                is_valid=False
            )
        
        ip_address = ip_address.strip()
        
        # Validate and parse IP
        try:
            ip = ipaddress.ip_address(ip_address)
        except ValueError:
            logger.warning(f"Invalid IP address: {ip_address}")
            return NetworkInfo(
                ip_address=ip_address,
                environment="unknown",
                city="unknown",
                subnet="",
                is_valid=False
            )
        
        # Check against known networks
        for network, (env, city) in self.networks.items():
            if ip in network:
                return NetworkInfo(
                    ip_address=ip_address,
                    environment=env,
                    city=city,
                    subnet=str(network),
                    is_valid=True
                )
        
        # Check if it's a private IP at all
        if ip.is_private:
            return NetworkInfo(
                ip_address=ip_address,
                environment="unknown",
                city="unknown",
                subnet="private",
                is_valid=True
            )
        
        # Public IP or unclassified
        return NetworkInfo(
            ip_address=ip_address,
            environment="unknown",
            city="unknown",
            subnet="public" if not ip.is_private else "",
            is_valid=True
        )
    
    def get_canonical_hostname(
        self,
        original_hostname: str,
        environment: str,
        city: str,
        role: Optional[str] = None
    ) -> str:
        """
        Generate canonical hostname based on naming convention.
        
        Format: srv-<ambiente>-<ciudad>-<rol>
        
        Args:
            original_hostname: Original hostname
            environment: Environment (prod/dev/test)
            city: City code (gye/uio/shared)
            role: Server role (optional)
            
        Returns:
            Canonical hostname string
        """
        if environment == "unknown" or city == "unknown":
            return original_hostname  # Keep original if can't classify
        
        # Build canonical name
        parts = ["srv", environment[:4], city[:3]]
        
        if role:
            # Clean role name
            role_clean = role.lower().replace(" ", "-")[:10]
            parts.append(role_clean)
        else:
            # Extract role from original hostname if possible
            role_guess = self._extract_role(original_hostname)
            if role_guess:
                parts.append(role_guess)
        
        return "-".join(parts)
    
    def _extract_role(self, hostname: str) -> Optional[str]:
        """
        Try to extract server role from hostname.
        
        Examples:
            XTR-SRV-PASMGYE -> pam
            TVC-SRV-PRIMARYGYE -> primary
            SRVCLIENTUIO -> client
        """
        hostname_lower = hostname.lower()
        
        # Remove common prefixes and city suffixes
        prefixes_to_remove = ['xtr-', 'tvc-', 'srv-', 'svr-', 'srv', 'server-', 'server']
        city_suffixes = ['gye', 'uio', 'quito', 'guayaquil', '-gye', '-uio']
        
        cleaned = hostname_lower
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
        
        for suffix in city_suffixes:
            if cleaned.endswith(suffix):
                cleaned = cleaned[:-len(suffix)]
        
        # Remove trailing numbers and dashes
        import re
        cleaned = re.sub(r'[-_]?\d+$', '', cleaned)
        cleaned = cleaned.strip('-_')
        
        # If we extracted something meaningful (2-15 chars), use it
        if 2 <= len(cleaned) <= 15 and cleaned.isalpha():
            return cleaned[:10]  # Max 10 chars
        
        # Common role patterns fallback
        role_patterns = {
            "pam": ["pasm", "pam", "privileged"],
            "db": ["db", "database", "sql", "mysql", "postgres", "oracle", "mongo"],
            "web": ["web", "www", "http", "nginx", "apache", "iis"],
            "app": ["app", "application", "api", "backend"],
            "mail": ["mail", "smtp", "exchange", "mx"],
            "file": ["file", "nas", "storage", "share"],
            "dc": ["dc", "domain", "ad", "ldap", "primary", "secondary"],
            "dns": ["dns", "bind", "ns"],
            "proxy": ["proxy", "haproxy", "lb", "loadbalancer"],
            "monitor": ["monitor", "nagios", "zabbix", "prometheus"],
            "backup": ["backup", "bkp", "veeam"],
            "vcenter": ["vcenter", "vmware", "esxi", "vsphere"],
            "citrix": ["citrix", "xenapp", "xendesktop"],
            "sap": ["sap", "hana", "abap"],
        }
        
        for role, patterns in role_patterns.items():
            for pattern in patterns:
                if pattern in hostname_lower:
                    return role
        
        return None
    
    def get_all_subnets(self) -> list:
        """Get list of all configured subnets with their mappings."""
        return [
            {
                "subnet": str(network),
                "environment": env,
                "city": city
            }
            for network, (env, city) in self.networks.items()
        ]


# Singleton instance
classifier = NetworkClassifier()


def classify_ip(ip_address: Optional[str]) -> NetworkInfo:
    """
    Convenience function to classify an IP address.
    
    Usage:
        info = classify_ip("192.168.59.100")
        print(f"Environment: {info.environment}, City: {info.city}")
    """
    return classifier.classify(ip_address)


def get_canonical_hostname(
    original: str,
    environment: str,
    city: str,
    role: Optional[str] = None
) -> str:
    """Generate canonical hostname."""
    return classifier.get_canonical_hostname(original, environment, city, role)


# Quick test
if __name__ == "__main__":
    test_ips = [
        "192.168.59.100",  # prod/gye
        "192.168.21.50",   # prod/uio
        "192.168.77.10",   # dev/shared
        "192.168.76.25",   # test/shared
        "192.168.1.1",     # unknown (home network)
        "10.0.0.50",       # unknown (broad range)
        "8.8.8.8",         # public (Google DNS)
        "invalid",         # invalid
        "",                # empty
        None,              # None
    ]
    
    print("\n" + "=" * 80)
    print("NETWORK CLASSIFIER TEST RESULTS")
    print("=" * 80 + "\n")
    
    for ip in test_ips:
        result = classify_ip(ip)
        print(f"IP: {ip!r}")
        print(f"  Environment: {result.environment}")
        print(f"  City: {result.city}")
        print(f"  Subnet: {result.subnet}")
        print(f"  Valid: {result.is_valid}")
        print("-" * 40)
    
    # Test canonical hostname generation
    print("\nCanonical Hostname Generation:")
    print(get_canonical_hostname("SERVER01", "prod", "gye", "database"))
    print(get_canonical_hostname("WEB-PROD-01", "prod", "uio"))
    print(get_canonical_hostname("DEV-DB-01", "dev", "shared"))
