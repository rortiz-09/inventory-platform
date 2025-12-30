"""
Server Governance Platform - Custom UI Components
HTML/CSS injection for custom alerts, cards, and badges.
NO native Streamlit toasts - all custom styling.
"""

import streamlit as st
from typing import Optional, Literal


def inject_custom_css() -> None:
    """Inject global custom CSS for the application."""
    st.markdown("""
        <style>
        /* Custom Alert Styles */
        .custom-alert {
            padding: 1rem 1.25rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            font-size: 0.95rem;
            line-height: 1.5;
        }
        
        .alert-success {
            background: linear-gradient(135deg, rgba(34, 197, 94, 0.15), rgba(34, 197, 94, 0.05));
            border-left: 4px solid #22c55e;
            color: #86efac;
        }
        
        .alert-warning {
            background: linear-gradient(135deg, rgba(234, 179, 8, 0.15), rgba(234, 179, 8, 0.05));
            border-left: 4px solid #eab308;
            color: #fde047;
        }
        
        .alert-danger {
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(239, 68, 68, 0.05));
            border-left: 4px solid #ef4444;
            color: #fca5a5;
        }
        
        .alert-info {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(59, 130, 246, 0.05));
            border-left: 4px solid #3b82f6;
            color: #93c5fd;
        }
        
        .alert-icon {
            font-size: 1.25rem;
            flex-shrink: 0;
        }
        
        /* Metric Card Styles */
        .metric-card {
            background: linear-gradient(145deg, #1e293b, #0f172a);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #fff, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.25rem;
        }
        
        .metric-label {
            color: #94a3b8;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .metric-delta {
            font-size: 0.8rem;
            margin-top: 0.5rem;
        }
        
        .metric-delta.positive { color: #22c55e; }
        .metric-delta.negative { color: #ef4444; }
        .metric-delta.neutral { color: #94a3b8; }
        
        /* Status Badge Styles */
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.375rem;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .badge-critical {
            background: rgba(239, 68, 68, 0.2);
            color: #fca5a5;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        
        .badge-high {
            background: rgba(249, 115, 22, 0.2);
            color: #fdba74;
            border: 1px solid rgba(249, 115, 22, 0.3);
        }
        
        .badge-medium {
            background: rgba(234, 179, 8, 0.2);
            color: #fde047;
            border: 1px solid rgba(234, 179, 8, 0.3);
        }
        
        .badge-low {
            background: rgba(34, 197, 94, 0.2);
            color: #86efac;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }
        
        .badge-unknown {
            background: rgba(148, 163, 184, 0.2);
            color: #cbd5e1;
            border: 1px solid rgba(148, 163, 184, 0.3);
        }
        
        /* Health Score Gauge */
        .health-gauge {
            width: 100%;
            height: 8px;
            background: #1e293b;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 0.5rem;
        }
        
        .health-gauge-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.5s ease;
        }
        
        /* Data Table Enhancements */
        .data-table-container {
            background: #0f172a;
            border-radius: 12px;
            padding: 1rem;
            overflow-x: auto;
        }
        
        /* Page Header */
        .page-header {
            padding: 1.5rem 0;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .page-title {
            font-size: 1.75rem;
            font-weight: 700;
            color: #fff;
            margin-bottom: 0.25rem;
        }
        
        .page-subtitle {
            color: #94a3b8;
            font-size: 0.95rem;
        }
        
        /* Section Header */
        .section-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin: 1.5rem 0 1rem 0;
        }
        
        .section-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #e2e8f0;
        }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 3rem;
            color: #64748b;
        }
        
        .empty-state-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        
        /* Spinner Override */
        .stSpinner > div {
            border-color: #3b82f6 transparent transparent transparent !important;
        }
        </style>
    """, unsafe_allow_html=True)


def alert_success(message: str, icon: str = "✅") -> None:
    """Render a success alert."""
    st.markdown(f"""
        <div class="custom-alert alert-success">
            <span class="alert-icon">{icon}</span>
            <span>{message}</span>
        </div>
    """, unsafe_allow_html=True)


def alert_warning(message: str, icon: str = "⚠️") -> None:
    """Render a warning alert."""
    st.markdown(f"""
        <div class="custom-alert alert-warning">
            <span class="alert-icon">{icon}</span>
            <span>{message}</span>
        </div>
    """, unsafe_allow_html=True)


def alert_danger(message: str, icon: str = "🚨") -> None:
    """Render a danger/error alert."""
    st.markdown(f"""
        <div class="custom-alert alert-danger">
            <span class="alert-icon">{icon}</span>
            <span>{message}</span>
        </div>
    """, unsafe_allow_html=True)


def alert_info(message: str, icon: str = "ℹ️") -> None:
    """Render an info alert."""
    st.markdown(f"""
        <div class="custom-alert alert-info">
            <span class="alert-icon">{icon}</span>
            <span>{message}</span>
        </div>
    """, unsafe_allow_html=True)


def metric_card(
    value: str,
    label: str,
    delta: Optional[str] = None,
    delta_type: Literal["positive", "negative", "neutral"] = "neutral",
    icon: Optional[str] = None
) -> None:
    """
    Render a styled metric card.
    
    Args:
        value: Main metric value
        label: Label/description
        delta: Optional change indicator
        delta_type: Type of delta for coloring
        icon: Optional icon to display
    """
    delta_html = ""
    if delta:
        delta_html = f'<div class="metric-delta {delta_type}">{delta}</div>'
    
    icon_html = f'<span style="font-size: 1.5rem; margin-bottom: 0.5rem; display: block;">{icon}</span>' if icon else ""
    
    st.markdown(f"""
        <div class="glass-card metric-card">
            {icon_html}
            <div class="metric-value">{value}</div>
            <div class="metric-label">{label}</div>
            {delta_html}
        </div>
    """, unsafe_allow_html=True)


def status_badge(
    text: str,
    status: Literal["critical", "high", "medium", "low", "unknown"] = "unknown"
) -> str:
    """
    Generate HTML for a status badge.
    
    Args:
        text: Badge text
        status: Status level for styling
        
    Returns:
        HTML string for the badge
    """
    return f'<span class="status-badge badge-{status}">{text}</span>'


def health_score_display(score: int, show_bar: bool = True) -> None:
    """
    Display a health score with visual gauge.
    
    Args:
        score: Health score (0-100)
        show_bar: Whether to show the progress bar
    """
    # Determine color based on score
    if score >= 80:
        color = "#22c55e"
        status = "low"
    elif score >= 60:
        color = "#eab308"
        status = "medium"
    elif score >= 40:
        color = "#f97316"
        status = "high"
    else:
        color = "#ef4444"
        status = "critical"
    
    bar_html = ""
    if show_bar:
        bar_html = f"""
            <div class="health-gauge">
                <div class="health-gauge-fill" style="width: {score}%; background: {color};"></div>
            </div>
        """
    
    st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <span style="font-size: 1.5rem; font-weight: 700; color: {color};">{score}</span>
            {status_badge(status.upper(), status)}
        </div>
        {bar_html}
    """, unsafe_allow_html=True)


def page_header(title: str, subtitle: Optional[str] = None, icon: Optional[str] = None) -> None:
    """
    Render a page header.
    
    Args:
        title: Page title
        subtitle: Optional subtitle/description
        icon: Optional icon
    """
    icon_html = f"{icon} " if icon else ""
    subtitle_html = f'<div class="page-subtitle">{subtitle}</div>' if subtitle else ""
    
    st.markdown(f"""
        <div class="page-header">
            <div class="page-title">{icon_html}{title}</div>
            {subtitle_html}
        </div>
    """, unsafe_allow_html=True)


def section_header(title: str, icon: Optional[str] = None) -> None:
    """Render a section header."""
    icon_html = f"{icon} " if icon else ""
    st.markdown(f"""
        <div class="section-header">
            <span class="section-title">{icon_html}{title}</span>
        </div>
    """, unsafe_allow_html=True)


def empty_state(message: str, icon: str = "📭") -> None:
    """Render an empty state message."""
    st.markdown(f"""
        <div class="empty-state">
            <div class="empty-state-icon">{icon}</div>
            <div>{message}</div>
        </div>
    """, unsafe_allow_html=True)


def loading_spinner(text: str = "Cargando...") -> None:
    """Display a loading message."""
    st.markdown(f"""
        <div style="text-align: center; padding: 2rem; color: #94a3b8;">
            <div class="stSpinner"></div>
            <div style="margin-top: 1rem;">{text}</div>
        </div>
    """, unsafe_allow_html=True)
