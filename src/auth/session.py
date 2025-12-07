"""
Server Governance Platform - Session Management
Streamlit session state management for authentication.
"""

import streamlit as st
from typing import Optional, Callable
from functools import wraps
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# Session state keys
SESSION_USER = "auth_user"
SESSION_LOGGED_IN = "auth_logged_in"
SESSION_LOGIN_TIME = "auth_login_time"


def init_session() -> None:
    """Initialize session state variables."""
    if SESSION_USER not in st.session_state:
        st.session_state[SESSION_USER] = None
    if SESSION_LOGGED_IN not in st.session_state:
        st.session_state[SESSION_LOGGED_IN] = False
    if SESSION_LOGIN_TIME not in st.session_state:
        st.session_state[SESSION_LOGIN_TIME] = None


def login(user: dict) -> None:
    """
    Set user as logged in.
    
    Args:
        user: User dict from authentication
    """
    st.session_state[SESSION_USER] = user
    st.session_state[SESSION_LOGGED_IN] = True
    st.session_state[SESSION_LOGIN_TIME] = datetime.now()
    logger.info(f"User logged in: {user.get('username')}")


def logout() -> None:
    """Log out current user."""
    username = get_current_user().get('username', 'unknown') if is_logged_in() else 'unknown'
    st.session_state[SESSION_USER] = None
    st.session_state[SESSION_LOGGED_IN] = False
    st.session_state[SESSION_LOGIN_TIME] = None
    logger.info(f"User logged out: {username}")


def is_logged_in() -> bool:
    """Check if user is logged in."""
    init_session()
    return st.session_state.get(SESSION_LOGGED_IN, False)


def get_current_user() -> Optional[dict]:
    """Get current logged-in user."""
    init_session()
    return st.session_state.get(SESSION_USER)


def get_user_role() -> Optional[str]:
    """Get current user's role."""
    user = get_current_user()
    return user.get('role') if user else None


def check_role(required_role: str) -> bool:
    """
    Check if current user has required role.
    
    Role hierarchy: admin > platform_lead > viewer
    """
    user = get_current_user()
    if not user:
        return False
    
    user_role = user.get('role', 'viewer')
    
    role_hierarchy = {
        'admin': 3,
        'platform_lead': 2,
        'viewer': 1,
    }
    
    user_level = role_hierarchy.get(user_role, 0)
    required_level = role_hierarchy.get(required_role, 0)
    
    return user_level >= required_level


def can_edit() -> bool:
    """Check if current user can edit data."""
    return check_role('platform_lead')


def can_delete() -> bool:
    """Check if current user can delete data."""
    return check_role('admin')


def can_import() -> bool:
    """Check if current user can import data."""
    return check_role('platform_lead')


def can_manage_users() -> bool:
    """Check if current user can manage users."""
    return check_role('admin')


def is_admin() -> bool:
    """Check if current user is admin."""
    user = get_current_user()
    return user and user.get('role') == 'admin'


def login_required(func: Callable) -> Callable:
    """
    Decorator to require login for a function.
    
    Usage:
        @login_required
        def my_protected_page():
            st.write("Only visible when logged in")
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_logged_in():
            st.warning("🔒 Por favor, inicie sesión para acceder a esta página.")
            return None
        return func(*args, **kwargs)
    return wrapper


def role_required(role: str) -> Callable:
    """
    Decorator factory to require specific role.
    
    Usage:
        @role_required('admin')
        def admin_only_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not is_logged_in():
                st.warning("🔒 Por favor, inicie sesión.")
                return None
            if not check_role(role):
                st.error(f"⛔ Acceso denegado. Se requiere rol: {role}")
                return None
            return func(*args, **kwargs)
        return wrapper
    return decorator


def render_login_form() -> Optional[dict]:
    """
    Render login form and handle authentication.
    
    Returns:
        User dict if login successful, None otherwise
    """
    from src.auth.security import authenticate_user
    
    st.markdown("""
        <style>
        .login-container {
            max-width: 400px;
            margin: 2rem auto;
            padding: 2rem;
            background: linear-gradient(145deg, #1a1a2e, #16213e);
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        .login-title {
            text-align: center;
            color: #fff;
            margin-bottom: 1.5rem;
            font-size: 1.5rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("## 🔐 Iniciar Sesión")
        st.markdown("---")
        
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input(
                "Usuario",
                placeholder="Ingrese su usuario",
                key="login_username"
            )
            password = st.text_input(
                "Contraseña",
                type="password",
                placeholder="Ingrese su contraseña",
                key="login_password"
            )
            
            col_a, col_b = st.columns(2)
            with col_b:
                submitted = st.form_submit_button(
                    "Ingresar",
                    use_container_width=True,
                    type="primary"
                )
            
            if submitted:
                if not username or not password:
                    st.error("Por favor, complete todos los campos")
                    return None
                
                user = authenticate_user(username, password)
                
                if user:
                    login(user)
                    st.success(f"✅ Bienvenido, {user['username']}!")
                    st.rerun()
                    return user
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
                    return None
        
        st.markdown("---")
        st.markdown("""
            <div style="text-align: center; color: #888; font-size: 0.85rem;">
                <strong>Usuarios por defecto:</strong><br>
                admin / admin123<br>
                platform_lead / platform123<br>
                viewer / viewer123
            </div>
        """, unsafe_allow_html=True)
    
    return None


def render_user_menu() -> None:
    """Render user menu in sidebar."""
    user = get_current_user()
    
    if not user:
        return
    
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"👤 **{user['username']}**")
        st.markdown(f"🏷️ Rol: `{user['role']}`")
        
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            logout()
            st.rerun()
