"""
Server Governance Platform - Server Models
Pydantic models for server entities with validation.
"""

from datetime import date, datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import ipaddress


class ServerType(str, Enum):
    PHYSICAL = "FISICO"
    VIRTUAL = "VIRTUAL"
    UNKNOWN = "DESCONOCIDO"


class Environment(str, Enum):
    PROD = "prod"
    DEV = "dev"
    TEST = "test"
    UNKNOWN = "unknown"


class City(str, Enum):
    GYE = "gye"
    UIO = "uio"
    SHARED = "shared"
    UNKNOWN = "unknown"


class NormalizedOS(BaseModel):
    """Result from the normalization engine."""
    product_key: str = Field(..., description="Normalized product key for API (e.g., 'rhel', 'ubuntu')")
    version: str = Field(..., description="Extracted version (Major.Minor.Patch)")
    original_string: str = Field(..., description="Original OS string before normalization")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score of normalization")
    
    @property
    def is_unknown(self) -> bool:
        return self.product_key == "unknown"


class LifecycleInfo(BaseModel):
    """Lifecycle information from endoflife.date API or cache."""
    product_key: str
    cycle: str
    eol_date: Optional[date] = None
    latest_version: Optional[str] = None
    is_eol: bool = False
    days_until_eol: Optional[int] = None
    last_updated: datetime = Field(default_factory=datetime.now)
    
    @property
    def risk_level(self) -> str:
        """Determine risk level based on EOL date."""
        if self.is_eol:
            return "CRITICAL"
        if self.days_until_eol is not None:
            if self.days_until_eol <= 90:
                return "HIGH"
            if self.days_until_eol <= 180:
                return "MEDIUM"
        return "LOW"


class NetworkClassification(BaseModel):
    """Network classification based on IP address."""
    ip_address: Optional[str] = None
    environment: Environment = Environment.UNKNOWN
    city: City = City.UNKNOWN
    subnet: Optional[str] = None
    is_valid: bool = False


class Server(BaseModel):
    """Main server entity with all attributes."""
    id: Optional[int] = None
    
    # Identity
    hostname_original: str = Field(..., description="Original hostname from source")
    hostname_canonical: Optional[str] = Field(None, description="Canonical hostname (srv-<env>-<city>-<role>)")
    
    # Network
    ip_address: Optional[str] = None
    network_classification: Optional[NetworkClassification] = None
    
    # Hardware
    server_type: ServerType = ServerType.UNKNOWN
    cpu_cores: Optional[int] = None
    ram_gb: Optional[float] = None
    disk_gb: Optional[float] = None
    
    # Operating System (Normalized)
    os_original: Optional[str] = Field(None, description="Original OS string")
    os_normalized: Optional[NormalizedOS] = None
    lifecycle_info: Optional[LifecycleInfo] = None
    
    # Classification
    environment: Environment = Environment.UNKNOWN
    city: City = City.UNKNOWN
    role: Optional[str] = None
    application: Optional[str] = None
    critical_system: Optional[str] = Field(None, description="Associated critical system")
    
    # Ownership
    owner: Optional[str] = None
    team: Optional[str] = None
    cost_center: Optional[str] = None
    
    # Operations
    backup_enabled: bool = False
    monitoring_enabled: bool = False
    
    # Health
    health_score: int = Field(default=100, ge=0, le=100)
    health_penalties: list[str] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    source_file: Optional[str] = None
    source_row: Optional[int] = None
    
    @field_validator('ip_address')
    @classmethod
    def validate_ip(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v.strip() == '':
            return None
        try:
            # Validate IP address format
            ipaddress.ip_address(v.strip())
            return v.strip()
        except ValueError:
            return None  # Invalid IP, return None


class ServerCreate(BaseModel):
    """DTO for creating a new server."""
    hostname_original: str
    ip_address: Optional[str] = None
    server_type: ServerType = ServerType.UNKNOWN
    os_original: Optional[str] = None
    owner: Optional[str] = None
    application: Optional[str] = None
    critical_system: Optional[str] = None
    backup_enabled: bool = False


class ServerImportRow(BaseModel):
    """DTO for importing a server from Excel."""
    hostname: Optional[str] = None
    ip: Optional[str] = None
    server_type: Optional[str] = None
    os: Optional[str] = None
    owner: Optional[str] = None
    application: Optional[str] = None
    critical_system: Optional[str] = None
    backup: Optional[str] = None
    cpu: Optional[str] = None
    ram: Optional[str] = None
    disk: Optional[str] = None
    
    def to_server_create(self) -> ServerCreate:
        """Convert import row to ServerCreate model."""
        # Parse server type
        server_type = ServerType.UNKNOWN
        if self.server_type:
            type_upper = self.server_type.upper().strip()
            if 'FISICO' in type_upper or 'PHYSICAL' in type_upper or 'FÍSICO' in type_upper:
                server_type = ServerType.PHYSICAL
            elif 'VIRTUAL' in type_upper or 'VM' in type_upper:
                server_type = ServerType.VIRTUAL
        
        # Parse backup
        backup = False
        if self.backup:
            backup_str = str(self.backup).upper().strip()
            backup = backup_str in ('SI', 'SÍ', 'YES', 'TRUE', '1', 'X')
        
        return ServerCreate(
            hostname_original=self.hostname or 'UNKNOWN',
            ip_address=self.ip,
            server_type=server_type,
            os_original=self.os,
            owner=self.owner,
            application=self.application,
            critical_system=self.critical_system,
            backup_enabled=backup
        )
