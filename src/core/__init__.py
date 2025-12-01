"""
Server Governance Platform - Core Package
"""

from .database import db, get_db, init_default_admin, Database

__all__ = ["db", "get_db", "init_default_admin", "Database"]
