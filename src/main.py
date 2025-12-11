"""
Server Governance Platform - Main Application
Entry point for the Streamlit application.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="Server Governance Platform",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Import after page config
from src.core.database import get_db, init_default_admin
from src.auth.session import (
    init_session, is_logged_in, render_login_form, 
    render_user_menu, get_current_user, can_import, can_edit
)
from src.components.ui import inject_custom_css, page_header, alert_info
from src.components.charts import (
    environment_distribution_chart, server_type_chart,
    top_os_chart, health_score_distribution, health_gauge,
    backup_coverage_chart
)
from src.components.data_table import render_server_table, render_import_preview
from src.components.filters import render_filters, apply_filters, render_filter_summary


def init_app():
    """Initialize application state."""
    init_session()
    inject_custom_css()
    
    # Initialize database and default users
    try:
        get_db()
        init_default_admin()
    except Exception as e:
        logger.error(f"Database initialization error: {e}")


def get_servers_data() -> pd.DataFrame:
    """Load servers data from database."""
    try:
        conn = get_db()
        result = conn.execute("""
            SELECT * FROM servers
            ORDER BY created_at DESC
        """).fetchdf()
        return result
    except Exception as e:
        logger.error(f"Error loading servers: {e}")
        return pd.DataFrame()


def render_dashboard():
    """Render the main dashboard."""
    page_header(
        "Dashboard",
        subtitle="Vista ejecutiva del inventario de servidores",
        icon="📊"
    )
    
    data = get_servers_data()
    
    if data.empty:
        alert_info("No hay servidores en el inventario. Use la opción 'Importar' para cargar datos.")
        return
    
    # KPI Row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_servers = len(data)
    virtual_pct = (data['server_type'] == 'VIRTUAL').sum() / max(total_servers, 1) * 100
    avg_health = data['health_score'].mean() if 'health_score' in data.columns else 0
    eol_count = (data['eol_days_remaining'] < 0).sum() if 'eol_days_remaining' in data.columns else 0
    prod_count = (data['environment'] == 'prod').sum() if 'environment' in data.columns else 0
    
    with col1:
        st.metric("Total Servidores", total_servers)
    with col2:
        st.metric("% Virtual", f"{virtual_pct:.1f}%")
    with col3:
        st.metric("Health Score Promedio", f"{avg_health:.0f}")
    with col4:
        st.metric("Servidores EOL", eol_count, delta=f"-{eol_count}" if eol_count > 0 else None, delta_color="inverse")
    with col5:
        st.metric("En Producción", prod_count)
    
    st.markdown("---")
    
    # Charts Row 1
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.plotly_chart(environment_distribution_chart(data), use_container_width=True)
    
    with col2:
        st.plotly_chart(server_type_chart(data), use_container_width=True)
    
    with col3:
        st.plotly_chart(health_gauge(int(avg_health)), use_container_width=True)
    
    # Charts Row 2
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(top_os_chart(data), use_container_width=True)
    
    with col2:
        st.plotly_chart(health_score_distribution(data), use_container_width=True)
    
    # Charts Row 3
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(backup_coverage_chart(data), use_container_width=True)


def render_inventory():
    """Render the server inventory page."""
    page_header(
        "Inventario de Servidores",
        subtitle="Lista completa de servidores con filtros",
        icon="🖥️"
    )
    
    data = get_servers_data()
    
    # Filters
    filters = render_filters(data)
    
    if filters:
        render_filter_summary(filters)
        filtered_data = apply_filters(data, filters)
        st.caption(f"Mostrando {len(filtered_data)} de {len(data)} servidores")
    else:
        filtered_data = data
    
    # Data table
    render_server_table(
        filtered_data,
        show_actions=can_edit()
    )


def render_import():
    """Render the Excel import page."""
    from src.logic.normalizer import normalize_os
    from src.logic.network_classifier import classify_ip
    from src.logic.lifecycle_engine import get_eol_info
    from src.logic.health_score import calculate_health_score
    
    page_header(
        "Importar Datos",
        subtitle="Carga de inventario desde Excel",
        icon="📥"
    )
    
    if not can_import():
        st.error("⛔ No tiene permisos para importar datos")
        return
    
    st.markdown("""
        ### Instrucciones
        1. Suba un archivo Excel (.xlsx) con los datos de servidores
        2. El sistema **detectará automáticamente** la fila de encabezados
        3. Se aplicará normalización de SO y clasificación de red
        4. Revise la vista previa antes de confirmar la importación
        
        > **Nota:** El sistema busca columnas como "IP", "SERVIDOR", "SISTEMA OPERATIVO" para detectar el encabezado.
    """)
    
    # File upload
    uploaded_file = st.file_uploader(
        "Seleccione archivo Excel",
        type=['xlsx', 'xls'],
        key='excel_upload'
    )
    
    if uploaded_file:
        try:
            # First, read without header to detect the header row
            df_raw = pd.read_excel(uploaded_file, engine='openpyxl', header=None, nrows=20)
            
            # Keywords to detect header row
            header_keywords = ['IP', 'SERVIDOR', 'SISTEMA OPERATIVO', 'HOSTNAME', 'OS', 'TIPO', 'APLICACIÓN', 'IP INTERNA']
            
            header_row = None
            for idx, row in df_raw.iterrows():
                row_str = ' '.join([str(v).upper() for v in row.values if pd.notna(v)])
                matches = sum(1 for kw in header_keywords if kw in row_str)
                if matches >= 2:  # At least 2 keywords found
                    header_row = idx
                    break
            
            if header_row is None:
                st.warning("⚠️ No se pudo detectar la fila de encabezados automáticamente. Usando fila 0.")
                header_row = 0
            else:
                st.info(f"📍 Encabezados detectados en fila {header_row + 1}")
            
            # Re-read with correct header
            uploaded_file.seek(0)  # Reset file pointer
            df = pd.read_excel(uploaded_file, engine='openpyxl', header=header_row)
            
            # Clean column names
            df.columns = [str(col).strip() for col in df.columns]
            
            # Remove completely empty rows
            df = df.dropna(how='all')
            
            st.success(f"✅ Archivo cargado: {len(df)} filas de datos encontradas")
            
            # Show detected columns
            columns_display = [c for c in df.columns if not c.startswith('Unnamed')]
            st.markdown("**Columnas detectadas:**")
            st.code(", ".join(columns_display[:15]) + ("..." if len(columns_display) > 15 else ""))
            
            # Auto-detect column mappings
            def find_column(keywords, columns):
                for col in columns:
                    col_upper = str(col).upper()
                    for kw in keywords:
                        if kw in col_upper:
                            return col
                return ''
            
            # Smart column detection
            detected_mappings = {
                'hostname': find_column(['SRV VIRTUAL', 'SERVIDOR', 'HOSTNAME', 'HOST', 'NOMBRE'], df.columns),
                'ip': find_column(['IP INTERNA', 'IP_INTERNA', 'IP ADDRESS', 'DIRECCION IP'], df.columns),
                'os': find_column(['SISTEMA OPERATIVO', 'OPERATING SYSTEM', 'SO', 'OS'], df.columns),
                'type': find_column(['TIPO DE SERVIDOR', 'TIPO', 'TYPE', 'VIRTUAL'], df.columns),
                'owner': find_column(['RESPONSABLE', 'OWNER', 'PERSONA', 'USUARIO', 'DUEÑO'], df.columns),
                'app': find_column(['APLICACIÓN', 'APPLICATION', 'APP', 'SISTEMA'], df.columns),
                'backup': find_column(['BACKUP', 'RESPALDO', 'BKP'], df.columns),
                'critical': find_column(['CRITICO', 'CRITICAL', 'CRITICIDAD', 'PRIORIDAD'], df.columns),
            }
            
            # Column mapping UI
            st.markdown("### 📋 Mapeo de Columnas")
            st.caption("El sistema ha detectado automáticamente las columnas. Ajuste si es necesario.")
            
            col1, col2 = st.columns(2)
            col_options = [''] + df.columns.tolist()
            
            with col1:
                hostname_col = st.selectbox(
                    "Columna Hostname/Servidor", 
                    options=col_options, 
                    index=col_options.index(detected_mappings['hostname']) if detected_mappings['hostname'] in col_options else 0,
                    key='map_hostname'
                )
                ip_col = st.selectbox(
                    "Columna IP", 
                    options=col_options,
                    index=col_options.index(detected_mappings['ip']) if detected_mappings['ip'] in col_options else 0,
                    key='map_ip'
                )
                os_col = st.selectbox(
                    "Columna Sistema Operativo", 
                    options=col_options,
                    index=col_options.index(detected_mappings['os']) if detected_mappings['os'] in col_options else 0,
                    key='map_os'
                )
                type_col = st.selectbox(
                    "Columna Tipo Servidor", 
                    options=col_options,
                    index=col_options.index(detected_mappings['type']) if detected_mappings['type'] in col_options else 0,
                    key='map_type'
                )
            
            with col2:
                owner_col = st.selectbox(
                    "Columna Responsable", 
                    options=col_options,
                    index=col_options.index(detected_mappings['owner']) if detected_mappings['owner'] in col_options else 0,
                    key='map_owner'
                )
                app_col = st.selectbox(
                    "Columna Aplicación", 
                    options=col_options,
                    index=col_options.index(detected_mappings['app']) if detected_mappings['app'] in col_options else 0,
                    key='map_app'
                )
                backup_col = st.selectbox(
                    "Columna Backup", 
                    options=col_options,
                    index=col_options.index(detected_mappings['backup']) if detected_mappings['backup'] in col_options else 0,
                    key='map_backup'
                )
                critical_col = st.selectbox(
                    "Columna Sistema Crítico", 
                    options=col_options,
                    index=col_options.index(detected_mappings['critical']) if detected_mappings['critical'] in col_options else 0,
                    key='map_critical'
                )
            
            # Show raw preview
            with st.expander("👁️ Vista previa de datos crudos"):
                st.dataframe(df.head(10), use_container_width=True)
            
            if st.button("🔄 Procesar y Previsualizar", type="primary"):
                with st.spinner("Procesando datos..."):
                    processed_rows = []
                    errors = []
                    
                    progress = st.progress(0)
                    
                    for idx, row in df.iterrows():
                        try:
                            progress.progress(min((idx + 1) / len(df), 1.0))
                            
                            # Extract values with safe handling
                            def safe_get(col):
                                if not col or col not in row.index:
                                    return None
                                val = row.get(col)
                                if pd.isna(val):
                                    return None
                                return str(val).strip()
                            
                            hostname = safe_get(hostname_col) or f"unknown-{idx}"
                            ip = safe_get(ip_col)
                            os_string = safe_get(os_col)
                            server_type = (safe_get(type_col) or '').upper()
                            owner = safe_get(owner_col)
                            app = safe_get(app_col)
                            backup_str = safe_get(backup_col) or ''
                            critical = safe_get(critical_col)
                            
                            # Skip empty rows
                            if not hostname or hostname in ('', 'nan', 'None', 'unknown-'):
                                continue
                            
                            # Skip if hostname looks like a header repeat
                            if any(kw in hostname.upper() for kw in ['SERVIDOR', 'HOSTNAME', 'SERVER']):
                                continue
                            
                            # Normalize OS
                            os_normalized = normalize_os(os_string)
                            
                            # Classify network
                            network_info = classify_ip(ip)
                            
                            # Get lifecycle info (with error handling)
                            lifecycle = None
                            if os_normalized['product_key'] != 'unknown':
                                try:
                                    lifecycle = get_eol_info(os_normalized['product_key'], os_normalized['version'])
                                except Exception as e:
                                    logger.warning(f"Lifecycle lookup failed for {os_normalized['product_key']}: {e}")
                            
                            # Parse server type
                            if 'FISICO' in server_type or 'PHYSICAL' in server_type or 'FÍSICO' in server_type:
                                server_type = 'FISICO'
                            elif 'VIRTUAL' in server_type or 'VM' in server_type:
                                server_type = 'VIRTUAL'
                            else:
                                server_type = 'DESCONOCIDO'
                            
                            # Parse backup
                            backup_enabled = backup_str.upper() in ('SI', 'SÍ', 'YES', 'TRUE', '1', 'X')
                            
                            # Calculate health score
                            eol_date = lifecycle.get('eol_date') if lifecycle else None
                            is_eol = lifecycle.get('is_eol', False) if lifecycle else False
                            
                            health_result = calculate_health_score(
                                eol_date=eol_date,
                                is_eol=is_eol,
                                os_product_key=os_normalized['product_key'],
                                environment=network_info.environment,
                                owner=owner,
                                ip_address=ip,
                                backup_enabled=backup_enabled
                            )
                            
                            processed_rows.append({
                                'hostname_original': hostname,
                                'ip_address': ip,
                                'server_type': server_type,
                                'os_original': os_string,
                                'os_product_key': os_normalized['product_key'],
                                'os_version': os_normalized['version'],
                                'os_confidence': os_normalized['confidence'],
                                'environment': network_info.environment,
                                'city': network_info.city,
                                'eol_date': eol_date,
                                'eol_days_remaining': lifecycle.get('days_until_eol') if lifecycle else None,
                                'owner': owner,
                                'application': app,
                                'critical_system': critical,
                                'backup_enabled': backup_enabled,
                                'health_score': health_result.score,
                                'health_penalties': '; '.join(health_result.penalties),
                            })
                        except Exception as e:
                            errors.append(f"Fila {idx}: {str(e)}")
                            logger.exception(f"Error processing row {idx}")
                    
                    progress.empty()
                    
                    if errors:
                        with st.expander(f"⚠️ {len(errors)} errores durante el procesamiento"):
                            for err in errors[:10]:
                                st.caption(err)
                    
                    if processed_rows:
                        processed_df = pd.DataFrame(processed_rows)
                        st.session_state['processed_import'] = processed_df
                        
                        st.success(f"✅ {len(processed_df)} servidores procesados correctamente")
                        
                        # Show preview
                        render_import_preview(processed_df)
                        
                        # Import button
                        if st.button("💾 Confirmar Importación", type="primary"):
                            import_to_database(processed_df)
                    else:
                        st.warning("No se encontraron filas válidas para procesar")
        
        except Exception as e:
            st.error(f"Error procesando archivo: {e}")
            logger.exception("Import error")


def import_to_database(df: pd.DataFrame):
    """Import processed DataFrame to database."""
    conn = get_db()
    user = get_current_user()
    
    try:
        imported = 0
        
        for _, row in df.iterrows():
            conn.execute("""
                INSERT INTO servers (
                    hostname_original, ip_address, server_type,
                    os_original, os_product_key, os_version, os_confidence,
                    environment, city, eol_date, eol_days_remaining,
                    owner, application, critical_system,
                    backup_enabled, health_score, health_penalties,
                    created_at, updated_at, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                row.get('hostname_original'),
                row.get('ip_address'),
                row.get('server_type'),
                row.get('os_original'),
                row.get('os_product_key'),
                row.get('os_version'),
                row.get('os_confidence'),
                row.get('environment'),
                row.get('city'),
                row.get('eol_date'),
                row.get('eol_days_remaining'),
                row.get('owner'),
                row.get('application'),
                row.get('critical_system'),
                row.get('backup_enabled', False),
                row.get('health_score', 100),
                row.get('health_penalties', ''),
                datetime.now(),
                datetime.now(),
                'excel_import',
            ])
            imported += 1
        
        # Log import
        conn.execute("""
            INSERT INTO import_history (filename, imported_at, imported_by, total_rows, successful_rows, failed_rows, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            'excel_import',
            datetime.now(),
            user.get('username') if user else 'system',
            len(df),
            imported,
            len(df) - imported,
            'completed'
        ])
        
        st.success(f"✅ {imported} servidores importados correctamente")
        st.balloons()
        
        # Clear processed data
        if 'processed_import' in st.session_state:
            del st.session_state['processed_import']
        
    except Exception as e:
        st.error(f"Error durante la importación: {e}")
        logger.exception("Database import error")


def render_settings():
    """Render settings page."""
    from src.auth.security import create_user, get_all_users, deactivate_user
    from src.auth.session import is_admin
    
    page_header(
        "Configuración",
        subtitle="Administración de usuarios y sistema",
        icon="⚙️"
    )
    
    if not is_admin():
        st.warning("Solo los administradores pueden acceder a esta sección")
        return
    
    # User management
    st.markdown("### 👥 Gestión de Usuarios")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        users = get_all_users()
        if users:
            users_df = pd.DataFrame(users)
            st.dataframe(
                users_df[['username', 'email', 'role', 'is_active', 'last_login']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No hay usuarios registrados")
    
    with col2:
        st.markdown("**Crear Usuario**")
        with st.form("create_user_form"):
            new_username = st.text_input("Usuario", key="new_username")
            new_email = st.text_input("Email", key="new_email")
            new_password = st.text_input("Contraseña", type="password", key="new_password")
            new_role = st.selectbox("Rol", options=['viewer', 'platform_lead', 'admin'], key="new_role")
            
            if st.form_submit_button("Crear Usuario"):
                if new_username and new_password:
                    success, message = create_user(new_username, new_password, new_email, new_role)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("Complete usuario y contraseña")
    
    st.markdown("---")
    
    # System info
    st.markdown("### 📊 Información del Sistema")
    
    col1, col2, col3 = st.columns(3)
    
    conn = get_db()
    
    with col1:
        server_count = conn.execute("SELECT COUNT(*) FROM servers").fetchone()[0]
        st.metric("Servidores Totales", server_count)
    
    with col2:
        cache_count = conn.execute("SELECT COUNT(*) FROM os_lifecycle_cache").fetchone()[0]
        st.metric("Entradas en Caché EOL", cache_count)
    
    with col3:
        import_count = conn.execute("SELECT COUNT(*) FROM import_history").fetchone()[0]
        st.metric("Importaciones Realizadas", import_count)
    
    # Cache management
    st.markdown("---")
    st.markdown("### 🔄 Gestión de Caché")
    
    if st.button("Refrescar Caché de Ciclos de Vida"):
        from src.logic.lifecycle_engine import get_lifecycle_engine
        
        with st.spinner("Actualizando caché..."):
            engine = get_lifecycle_engine()
            stats = engine.refresh_cache()
            st.success(f"Caché actualizado: {stats['updated']} entradas actualizadas, {stats['failed']} fallidas")


def main():
    """Main application entry point."""
    init_app()
    
    # Check authentication
    if not is_logged_in():
        render_login_form()
        return
    
    # Render user menu
    render_user_menu()
    
    # Navigation
    st.sidebar.markdown("## 🖥️ Server Governance")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "Navegación",
        options=["📊 Dashboard", "🖥️ Inventario", "📥 Importar", "⚙️ Configuración"],
        label_visibility="collapsed"
    )
    
    # Route to page
    if page == "📊 Dashboard":
        render_dashboard()
    elif page == "🖥️ Inventario":
        render_inventory()
    elif page == "📥 Importar":
        render_import()
    elif page == "⚙️ Configuración":
        render_settings()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption(f"v1.0.0 | {datetime.now().strftime('%Y-%m-%d')}")


if __name__ == "__main__":
    main()
