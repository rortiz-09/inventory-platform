"""
Server Governance Platform - Data Table Component
Interactive server data display with sorting and actions.
"""

import streamlit as st
import pandas as pd
from typing import Optional, Callable, List
from src.components.ui import status_badge


def render_server_table(
    data: pd.DataFrame,
    on_edit: Optional[Callable] = None,
    on_delete: Optional[Callable] = None,
    show_actions: bool = True,
    page_size: int = 20
) -> None:
    """
    Render an interactive server data table.
    
    Args:
        data: DataFrame with server data
        on_edit: Callback for edit action
        on_delete: Callback for delete action
        show_actions: Whether to show action buttons
        page_size: Number of rows per page
    """
    if data.empty:
        st.markdown("""
            <div style="text-align: center; padding: 3rem; color: #64748b;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">📭</div>
                <div>No hay servidores para mostrar</div>
            </div>
        """, unsafe_allow_html=True)
        return
    
    # Pagination
    total_rows = len(data)
    total_pages = (total_rows + page_size - 1) // page_size
    
    if 'table_page' not in st.session_state:
        st.session_state.table_page = 1
        
    # Ensure current page is valid for the current dataset size
    # This prevents StreamlitValueAboveMaxError when filters reduce total pages
    if total_pages > 0 and st.session_state.table_page > total_pages:
        st.session_state.table_page = total_pages
    elif total_pages == 0:
        st.session_state.table_page = 1
    
    # Pagination controls
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        page = st.number_input(
            f"Página (de {total_pages})",
            min_value=1,
            max_value=max(1, total_pages),
            value=st.session_state.table_page,
            key="page_selector"
        )
        st.session_state.table_page = page
    
    # Slice data for current page
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_rows)
    page_data = data.iloc[start_idx:end_idx]
    
    # Display info
    st.caption(f"Mostrando {start_idx + 1}-{end_idx} de {total_rows} servidores")
    
    # Column selection
    display_columns = [
        'hostname_original',
        'ip_address',
        'server_type',
        'os_product_key',
        'os_version',
        'environment',
        'city',
        'health_score',
        'owner',
    ]
    
    # Filter to available columns
    available_cols = [c for c in display_columns if c in page_data.columns]
    
    # Render table header
    st.markdown("""
        <style>
        .server-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }
        .server-table th {
            background: #1e293b;
            color: #94a3b8;
            padding: 0.75rem;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.5px;
            border-bottom: 2px solid #334155;
        }
        .server-table td {
            padding: 0.75rem;
            border-bottom: 1px solid #1e293b;
            color: #e2e8f0;
        }
        .server-table tr:hover td {
            background: rgba(59, 130, 246, 0.1);
        }
        .server-table .hostname {
            font-weight: 600;
            color: #3b82f6;
        }
        .server-table .ip {
            font-family: monospace;
            color: #94a3b8;
        }
        .server-table .score {
            font-weight: 700;
        }
        .server-table .score.critical { color: #ef4444; }
        .server-table .score.high { color: #f97316; }
        .server-table .score.medium { color: #eab308; }
        .server-table .score.low { color: #22c55e; }
        </style>
    """, unsafe_allow_html=True)
    
    # Build table HTML
    header_labels = {
        'hostname_original': 'Hostname',
        'ip_address': 'IP',
        'server_type': 'Tipo',
        'os_product_key': 'OS',
        'os_version': 'Versión',
        'environment': 'Ambiente',
        'city': 'Ciudad',
        'health_score': 'Score',
        'owner': 'Responsable',
    }
    
    headers = ''.join([f'<th>{header_labels.get(c, c)}</th>' for c in available_cols])
    if show_actions:
        headers += '<th style="width: 100px;">Acciones</th>'
    
    rows_html = []
    for idx, row in page_data.iterrows():
        cells = []
        for col in available_cols:
            value = row.get(col, '')
            
            if col == 'hostname_original':
                cells.append(f'<td class="hostname">{value}</td>')
            elif col == 'ip_address':
                cells.append(f'<td class="ip">{value or "-"}</td>')
            elif col == 'health_score':
                score = int(value) if pd.notna(value) else 0
                score_class = 'critical' if score < 40 else 'high' if score < 60 else 'medium' if score < 80 else 'low'
                cells.append(f'<td class="score {score_class}">{score}</td>')
            elif col == 'environment':
                env_colors = {'prod': 'danger', 'dev': 'info', 'test': 'warning', 'unknown': 'unknown'}
                badge = status_badge(str(value).upper() if value else 'N/A', env_colors.get(str(value).lower(), 'unknown'))
                cells.append(f'<td>{badge}</td>')
            else:
                cells.append(f'<td>{value if pd.notna(value) else "-"}</td>')
        
        row_html = ''.join(cells)
        
        if show_actions:
            row_html += '<td>-</td>'  # Placeholder for button actions
        
        rows_html.append(f'<tr data-id="{idx}">{row_html}</tr>')
    
    table_html = f"""
        <div class="data-table-container">
            <table class="server-table">
                <thead><tr>{headers}</tr></thead>
                <tbody>{''.join(rows_html)}</tbody>
            </table>
        </div>
    """
    
    st.markdown(table_html, unsafe_allow_html=True)
    
    # Action buttons (using Streamlit native for interactivity)
    if show_actions and (on_edit or on_delete):
        st.markdown("---")
        st.markdown("**Acciones Rápidas:**")
        
        cols = st.columns(4)
        for i, (idx, row) in enumerate(page_data.iterrows()):
            col_idx = i % 4
            with cols[col_idx]:
                with st.expander(f"📋 {row.get('hostname_original', 'Server')[:15]}"):
                    if on_edit:
                        if st.button("✏️ Editar", key=f"edit_{idx}"):
                            on_edit(idx, row)
                    if on_delete:
                        if st.button("🗑️ Eliminar", key=f"del_{idx}", type="secondary"):
                            on_delete(idx, row)


def render_compact_table(
    data: pd.DataFrame,
    columns: List[str],
    title: Optional[str] = None
) -> None:
    """
    Render a compact read-only table.
    
    Args:
        data: DataFrame to display
        columns: Columns to show
        title: Optional table title
    """
    if title:
        st.markdown(f"**{title}**")
    
    if data.empty:
        st.caption("Sin datos")
        return
    
    available_cols = [c for c in columns if c in data.columns]
    st.dataframe(
        data[available_cols],
        use_container_width=True,
        hide_index=True,
    )


def render_import_preview(data: pd.DataFrame, max_rows: int = 10) -> None:
    """
    Render a preview of imported data.
    
    Args:
        data: DataFrame to preview
        max_rows: Maximum rows to show
    """
    st.markdown("### 👁️ Vista Previa")
    st.caption(f"Mostrando primeras {min(len(data), max_rows)} filas de {len(data)} total")
    
    preview = data.head(max_rows)
    
    # Highlight problematic rows
    def highlight_issues(row):
        styles = [''] * len(row)
        
        # Highlight missing hostnames
        if 'hostname_original' in row.index and (pd.isna(row['hostname_original']) or row['hostname_original'] == ''):
            idx = list(row.index).index('hostname_original')
            styles[idx] = 'background-color: rgba(239, 68, 68, 0.3)'
        
        # Highlight unknown OS
        if 'os_product_key' in row.index and row.get('os_product_key') == 'unknown':
            idx = list(row.index).index('os_product_key')
            styles[idx] = 'background-color: rgba(234, 179, 8, 0.3)'
        
        return styles
    
    styled = preview.style.apply(highlight_issues, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)
    
    # Show legend
    st.markdown("""
        <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.5rem;">
            <span style="background: rgba(239, 68, 68, 0.3); padding: 2px 6px; border-radius: 4px;">🔴 Hostname faltante</span>
            <span style="background: rgba(234, 179, 8, 0.3); padding: 2px 6px; border-radius: 4px; margin-left: 8px;">🟡 OS no reconocido</span>
        </div>
    """, unsafe_allow_html=True)
