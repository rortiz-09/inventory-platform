"""
Server Governance Platform - User Models
Pydantic models for user authentication and authorization.
"""

from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import re


class UserRole(str, Enum):
    ADMIN = "admin"
    PLATFORM_LEAD = "platform_lead"
    VIEWER = "viewer"


class User(BaseModel):
    """User entity with role-based access."""
    id: Optional[int] = None
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = None
    password_hash: str = Field(..., description="bcrypt hashed password")
    role: UserRole = UserRole.VIEWER
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email format')
        return v.lower()
    
    def can_edit(self) -> bool:
        """Check if user can edit server data."""
        return self.role in (UserRole.ADMIN, UserRole.PLATFORM_LEAD)
    
    def can_import(self) -> bool:
        """Check if user can import data."""
        return self.role in (UserRole.ADMIN, UserRole.PLATFORM_LEAD)
    
    def can_delete(self) -> bool:
        """Check if user can delete data."""
        return self.role == UserRole.ADMIN
    
    def can_manage_users(self) -> bool:
        """Check if user can manage other users."""
        return self.role == UserRole.ADMIN


class UserCreate(BaseModel):
    """DTO for creating a new user."""
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = None
    password: str = Field(..., min_length=6, description="Plain text password")
    role: UserRole = UserRole.VIEWER
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v.lower()


class UserLogin(BaseModel):
    """DTO for user login."""
    username: str
    password: str


class UserSession(BaseModel):
    """Session data stored in Streamlit session state."""
    user_id: int
    username: str
    role: UserRole
    logged_in_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN
    
    @property
    def is_platform_lead(self) -> bool:
        return self.role == UserRole.PLATFORM_LEAD


class UserUpdate(BaseModel):
    """DTO for updating user information."""
    email: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)
