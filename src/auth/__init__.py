"""
Server Governance Platform - Auth Package
"""

from .security import (
    hash_password,
    verify_password,
    authenticate_user,
    create_user,
    update_user_password,
    deactivate_user,
    get_all_users,
)
from .session import (
    init_session,
    login,
    logout,
    is_logged_in,
    get_current_user,
    get_user_role,
    check_role,
    can_edit,
    can_delete,
    can_import,
    can_manage_users,
    is_admin,
    login_required,
    role_required,
    render_login_form,
    render_user_menu,
)

__all__ = [
    # Security
    "hash_password",
    "verify_password",
    "authenticate_user",
    "create_user",
    "update_user_password",
    "deactivate_user",
    "get_all_users",
    # Session
    "init_session",
    "login",
    "logout",
    "is_logged_in",
    "get_current_user",
    "get_user_role",
    "check_role",
    "can_edit",
    "can_delete",
    "can_import",
    "can_manage_users",
    "is_admin",
    "login_required",
    "role_required",
    "render_login_form",
    "render_user_menu",
]
