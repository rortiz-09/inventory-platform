"""
Server Governance Platform - Security Module
Password hashing and user authentication with bcrypt.
"""

import bcrypt
from typing import Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password to verify
        password_hash: Stored password hash
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            password_hash.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Authenticate a user by username and password.
    
    Args:
        username: Username to authenticate
        password: Plain text password
        
    Returns:
        User dict if authenticated, None otherwise
    """
    from src.core.database import get_db
    
    conn = get_db()
    
    try:
        result = conn.execute("""
            SELECT id, username, email, password_hash, role, is_active
            FROM users
            WHERE username = ? AND is_active = TRUE
        """, [username.lower()]).fetchone()
        
        if not result:
            logger.warning(f"Authentication failed: user not found - {username}")
            return None
        
        user_id, db_username, email, password_hash, role, is_active = result
        
        if not verify_password(password, password_hash):
            logger.warning(f"Authentication failed: wrong password - {username}")
            return None
        
        # Update last login
        conn.execute("""
            UPDATE users SET last_login = ? WHERE id = ?
        """, [datetime.now(), user_id])
        
        logger.info(f"User authenticated successfully: {username}")
        
        return {
            "id": user_id,
            "username": db_username,
            "email": email,
            "role": role,
            "is_active": is_active,
        }
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None


def create_user(
    username: str,
    password: str,
    email: Optional[str] = None,
    role: str = "viewer"
) -> Tuple[bool, str]:
    """
    Create a new user.
    
    Args:
        username: Username (will be lowercased)
        password: Plain text password
        email: Optional email address
        role: User role (admin, platform_lead, viewer)
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    from src.core.database import get_db
    
    conn = get_db()
    
    # Validate role
    valid_roles = ["admin", "platform_lead", "viewer"]
    if role not in valid_roles:
        return False, f"Invalid role. Must be one of: {', '.join(valid_roles)}"
    
    # Check if username exists
    existing = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        [username.lower()]
    ).fetchone()
    
    if existing:
        return False, "Username already exists"
    
    try:
        password_hash = hash_password(password)
        
        conn.execute("""
            INSERT INTO users (username, email, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, [
            username.lower(),
            email.lower() if email else None,
            password_hash,
            role,
            datetime.now()
        ])
        
        logger.info(f"User created: {username} with role {role}")
        return True, "User created successfully"
        
    except Exception as e:
        logger.error(f"User creation error: {e}")
        return False, f"Error creating user: {str(e)}"


def update_user_password(user_id: int, new_password: str) -> Tuple[bool, str]:
    """
    Update a user's password.
    
    Args:
        user_id: User ID
        new_password: New plain text password
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    from src.core.database import get_db
    
    conn = get_db()
    
    try:
        password_hash = hash_password(new_password)
        
        conn.execute("""
            UPDATE users SET password_hash = ? WHERE id = ?
        """, [password_hash, user_id])
        
        logger.info(f"Password updated for user ID: {user_id}")
        return True, "Password updated successfully"
        
    except Exception as e:
        logger.error(f"Password update error: {e}")
        return False, f"Error updating password: {str(e)}"


def deactivate_user(user_id: int) -> Tuple[bool, str]:
    """Deactivate a user account."""
    from src.core.database import get_db
    
    conn = get_db()
    
    try:
        conn.execute("""
            UPDATE users SET is_active = FALSE WHERE id = ?
        """, [user_id])
        
        logger.info(f"User deactivated: ID {user_id}")
        return True, "User deactivated"
        
    except Exception as e:
        logger.error(f"User deactivation error: {e}")
        return False, f"Error: {str(e)}"


def get_all_users() -> list:
    """Get all users (for admin panel)."""
    from src.core.database import get_db
    
    conn = get_db()
    
    try:
        result = conn.execute("""
            SELECT id, username, email, role, is_active, created_at, last_login
            FROM users
            ORDER BY created_at DESC
        """).fetchall()
        
        return [
            {
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "role": row[3],
                "is_active": row[4],
                "created_at": row[5],
                "last_login": row[6],
            }
            for row in result
        ]
        
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return []
