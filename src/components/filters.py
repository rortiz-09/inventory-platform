"""
Server Governance Platform - Filter Components
Sidebar filters for data exploration.
"""

import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any, List


def render_filters(data: pd.DataFrame) -> Dict[str, Any]:
    """
    Render filter sidebar and return filter values.
    
    Args:
        data: Full DataFrame to build filter options from
        
    Returns:
        Dict of filter values
    """
    filters = {}
    
    st.sidebar.markdown("## 🔍 Filtros")
    st.sidebar.markdown("---")
    
    # Environment filter
    if 'environment' in data.columns:
        envs = ['Todos'] + sorted(data['environment'].dropna().unique().tolist())
        selected_env = st.sidebar.selectbox(
            "Ambiente",
            options=envs,
            key="filter_env"
        )
        if selected_env != 'Todos':
            filters['environment'] = selected_env
    
    # Server type filter
    if 'server_type' in data.columns:
        types = ['Todos'] + sorted(data['server_type'].dropna().unique().tolist())
        selected_type = st.sidebar.selectbox(
            "Tipo de Servidor",
            options=types,
            key="filter_type"
        )
        if selected_type != 'Todos':
            filters['server_type'] = selected_type
    
    # City filter
    if 'city' in data.columns:
        cities = ['Todos'] + sorted(data['city'].dropna().unique().tolist())
        selected_city = st.sidebar.selectbox(
            "Ciudad",
            options=cities,
            key="filter_city"
        )
        if selected_city != 'Todos':
            filters['city'] = selected_city
    
    # OS filter
    if 'os_product_key' in data.columns:
        os_list = ['Todos'] + sorted(data['os_product_key'].dropna().unique().tolist())
        selected_os = st.sidebar.selectbox(
            "Sistema Operativo",
            options=os_list,
            key="filter_os"
        )
        if selected_os != 'Todos':
            filters['os_product_key'] = selected_os
    
    st.sidebar.markdown("---")
    
    # Health score range
    if 'health_score' in data.columns:
        st.sidebar.markdown("**Health Score**")
        score_range = st.sidebar.slider(
            "Rango de Score",
            min_value=0,
            max_value=100,
            value=(0, 100),
            key="filter_score"
        )
        if score_range != (0, 100):
            filters['health_score_min'] = score_range[0]
            filters['health_score_max'] = score_range[1]
        
        # Quick filters for risk levels
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("🔴 Críticos", use_container_width=True, key="filter_critical"):
                filters['health_score_min'] = 0
                filters['health_score_max'] = 40
        with col2:
            if st.button("🟢 Saludables", use_container_width=True, key="filter_healthy"):
                filters['health_score_min'] = 80
                filters['health_score_max'] = 100
    
    st.sidebar.markdown("---")
    
    # EOL Status filter
    st.sidebar.markdown("**Estado EOL**")
    eol_filter = st.sidebar.radio(
        "Filtrar por EOL",
        options=["Todos", "Solo EOL", "Solo Activos", "EOL Próximo (180d)"],
        key="filter_eol",
        label_visibility="collapsed"
    )
    if eol_filter != "Todos":
        filters['eol_status'] = eol_filter
    
    st.sidebar.markdown("---")
    
    # Search
    search_term = st.sidebar.text_input(
        "🔎 Buscar",
        placeholder="Hostname, IP, Owner...",
        key="filter_search"
    )
    if search_term:
        filters['search'] = search_term
    
    # Clear filters button
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Limpiar Filtros", use_container_width=True):
        # Clear session state for filters
        for key in list(st.session_state.keys()):
            if key.startswith('filter_'):
                del st.session_state[key]
        st.rerun()
    
    return filters


def apply_filters(data: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """
    Apply filters to DataFrame.
    
    Args:
        data: DataFrame to filter
        filters: Filter values from render_filters()
        
    Returns:
        Filtered DataFrame
    """
    filtered = data.copy()
    
    # Direct column filters
    for col in ['environment', 'server_type', 'city', 'os_product_key']:
        if col in filters and col in filtered.columns:
            filtered = filtered[filtered[col] == filters[col]]
    
    # Health score range
    if 'health_score_min' in filters and 'health_score' in filtered.columns:
        filtered = filtered[filtered['health_score'] >= filters['health_score_min']]
    if 'health_score_max' in filters and 'health_score' in filtered.columns:
        filtered = filtered[filtered['health_score'] <= filters['health_score_max']]
    
    # EOL status filter
    if 'eol_status' in filters and 'eol_days_remaining' in filtered.columns:
        eol_status = filters['eol_status']
        if eol_status == "Solo EOL":
            filtered = filtered[filtered['eol_days_remaining'] < 0]
        elif eol_status == "Solo Activos":
            filtered = filtered[
                (filtered['eol_days_remaining'].isna()) | 
                (filtered['eol_days_remaining'] >= 0)
            ]
        elif eol_status == "EOL Próximo (180d)":
            filtered = filtered[
                (filtered['eol_days_remaining'] >= 0) & 
                (filtered['eol_days_remaining'] <= 180)
            ]
    
    # Search filter
    if 'search' in filters:
        search_term = filters['search'].lower()
        search_cols = ['hostname_original', 'ip_address', 'owner', 'application', 'os_original']
        search_cols = [c for c in search_cols if c in filtered.columns]
        
        mask = pd.Series([False] * len(filtered), index=filtered.index)
        for col in search_cols:
            mask |= filtered[col].astype(str).str.lower().str.contains(search_term, na=False)
        
        filtered = filtered[mask]
    
    return filtered


def render_filter_summary(filters: Dict[str, Any]) -> None:
    """
    Render a summary of active filters.
    
    Args:
        filters: Active filter values
    """
    if not filters:
        return
    
    filter_labels = []
    
    label_map = {
        'environment': 'Ambiente',
        'server_type': 'Tipo',
        'city': 'Ciudad',
        'os_product_key': 'OS',
        'eol_status': 'EOL',
        'search': 'Búsqueda',
    }
    
    for key, value in filters.items():
        if key in label_map:
            filter_labels.append(f"{label_map[key]}: {value}")
        elif key == 'health_score_min':
            filter_labels.append(f"Score ≥ {value}")
        elif key == 'health_score_max':
            filter_labels.append(f"Score ≤ {value}")
    
    if filter_labels:
        badges = ' '.join([
            f'<span style="background: #1e293b; padding: 4px 8px; border-radius: 4px; margin-right: 4px; font-size: 0.8rem;">{label}</span>'
            for label in filter_labels
        ])
        st.markdown(f"""
            <div style="margin-bottom: 1rem;">
                <span style="color: #94a3b8; font-size: 0.85rem;">Filtros activos:</span>
                {badges}
            </div>
        """, unsafe_allow_html=True)


def get_filter_stats(
    original_data: pd.DataFrame,
    filtered_data: pd.DataFrame
) -> Dict[str, int]:
    """
    Get statistics about filtered data.
    
    Args:
        original_data: Original unfiltered DataFrame
        filtered_data: Filtered DataFrame
        
    Returns:
        Dict with counts
    """
    return {
        'total': len(original_data),
        'filtered': len(filtered_data),
        'removed': len(original_data) - len(filtered_data),
        'percentage': round(len(filtered_data) / max(len(original_data), 1) * 100, 1),
    }
