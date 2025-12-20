"""
Server Governance Platform - Database Core
DuckDB connection management and schema initialization.
"""

import duckdb
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Database path - persistent in /app/data volume
DB_PATH = Path("/app/data/inventory.duckdb")

# For local development, use relative path if /app/data doesn't exist
if not DB_PATH.parent.exists():
    DB_PATH = Path("data/inventory.duckdb")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class Database:
    """Singleton DuckDB connection manager."""
    
    _instance: Optional['Database'] = None
    _connection: Optional[duckdb.DuckDBPyConnection] = None
    
    def __new__(cls) -> 'Database':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        """Get or create database connection."""
        if self._connection is None:
            self._connection = duckdb.connect(str(DB_PATH))
            self._init_schema()
        return self._connection
    
    def _init_schema(self) -> None:
        """Initialize database schema."""
        logger.info(f"Initializing database schema at {DB_PATH}")
        
        # ================================================================
        # SEQUENCES FOR AUTO-INCREMENT IDs
        # DuckDB requires explicit sequences (unlike SQLite's AUTOINCREMENT)
        # ================================================================
        self.conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_users_id START 1")
        self.conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_servers_id START 1")
        self.conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_lifecycle_id START 1")
        self.conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_import_id START 1")
        
        # Users table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_users_id'),
                username VARCHAR UNIQUE NOT NULL,
                email VARCHAR,
                password_hash VARCHAR NOT NULL,
                role VARCHAR NOT NULL DEFAULT 'viewer',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        # Servers table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_servers_id'),
                hostname_original VARCHAR NOT NULL,
                hostname_canonical VARCHAR,
                ip_address VARCHAR,
                server_type VARCHAR DEFAULT 'DESCONOCIDO',
                cpu_cores INTEGER,
                ram_gb DOUBLE,
                disk_gb DOUBLE,
                os_original VARCHAR,
                os_product_key VARCHAR,
                os_version VARCHAR,
                os_confidence DOUBLE DEFAULT 1.0,
                eol_date DATE,
                eol_days_remaining INTEGER,
                environment VARCHAR DEFAULT 'unknown',
                city VARCHAR DEFAULT 'unknown',
                role VARCHAR,
                application VARCHAR,
                critical_system VARCHAR,
                owner VARCHAR,
                team VARCHAR,
                cost_center VARCHAR,
                backup_enabled BOOLEAN DEFAULT FALSE,
                monitoring_enabled BOOLEAN DEFAULT FALSE,
                health_score INTEGER DEFAULT 100,
                health_penalties VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_file VARCHAR,
                source_row INTEGER
            )
        """)
        
        # OS Lifecycle Cache table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS os_lifecycle_cache (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_lifecycle_id'),
                product_key VARCHAR NOT NULL,
                cycle VARCHAR NOT NULL,
                eol_date DATE,
                latest_version VARCHAR,
                release_date DATE,
                support_ended BOOLEAN DEFAULT FALSE,
                lts BOOLEAN DEFAULT FALSE,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(product_key, cycle)
            )
        """)
        
        # Import history table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS import_history (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_import_id'),
                filename VARCHAR NOT NULL,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                imported_by VARCHAR,
                total_rows INTEGER,
                successful_rows INTEGER,
                failed_rows INTEGER,
                status VARCHAR DEFAULT 'completed'
            )
        """)
        
        # Create indexes for performance
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_servers_environment ON servers(environment)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_servers_os_product ON servers(os_product_key)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_servers_health ON servers(health_score)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_lifecycle_product ON os_lifecycle_cache(product_key)")
        
        logger.info("Database schema initialized successfully")
    
    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


# Global database instance
db = Database()


def get_db() -> duckdb.DuckDBPyConnection:
    """Get database connection."""
    return db.conn


def init_default_admin() -> None:
    """Create default admin user if no users exist."""
    import bcrypt
    
    conn = get_db()
    result = conn.execute("SELECT COUNT(*) FROM users").fetchone()
    
    if result[0] == 0:
        # Create default admin
        password_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
        conn.execute("""
            INSERT INTO users (id, username, email, password_hash, role)
            VALUES (1, 'admin', 'admin@platform.local', ?, 'admin')
        """, [password_hash])
        
        # Create platform lead user
        password_hash = bcrypt.hashpw("platform123".encode(), bcrypt.gensalt()).decode()
        conn.execute("""
            INSERT INTO users (id, username, email, password_hash, role)
            VALUES (2, 'platform_lead', 'lead@platform.local', ?, 'platform_lead')
        """, [password_hash])
        
        # Create viewer user
        password_hash = bcrypt.hashpw("viewer123".encode(), bcrypt.gensalt()).decode()
        conn.execute("""
            INSERT INTO users (id, username, email, password_hash, role)
            VALUES (3, 'viewer', 'viewer@platform.local', ?, 'viewer')
        """, [password_hash])
        
        logger.info("Default users created: admin, platform_lead, viewer")
