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
    from src.logic.network_classifier import classify_ip, get_canonical_hostname
    from src.logic.lifecycle_engine import get_eol_info
    from src.logic.health_score import calculate_health_score
    
    # ================================================================
    # INICIALIZAR SESSION STATE
    # Necesario para evitar KeyError en Streamlit
    # ================================================================
    if 'import_ready' not in st.session_state:
        st.session_state['import_ready'] = False
    if 'processed_import' not in st.session_state:
        st.session_state['processed_import'] = None
    
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
        2. El sistema **leerá todas las hojas** del libro y detectará encabezados automáticamente
        3. Se aplicará normalización de SO y clasificación de red
        4. Revise la vista previa antes de confirmar la importación
        
        > **Nota:** El sistema busca columnas como "IP", "SERVIDOR", "SISTEMA OPERATIVO" para detectar el encabezado en cada hoja.
    """)
    
    # File upload
    uploaded_file = st.file_uploader(
        "Seleccione archivo Excel",
        type=['xlsx', 'xls'],
        key='excel_upload'
    )
    
    if uploaded_file:
        try:
            # ================================================================
            # MULTI-SHEET EXCEL SUPPORT
            # Lee todas las hojas del libro Excel y las combina en un solo
            # DataFrame, añadiendo una columna 'source_sheet' para trazabilidad
            # ================================================================
            
            # Read all sheet names from the workbook
            excel_file = pd.ExcelFile(uploaded_file, engine='openpyxl')
            all_sheet_names = excel_file.sheet_names
            
            # ================================================================
            # FILTRADO INTELIGENTE DE HOJAS
            # - Prioriza hojas con año actual (2025)
            # - Omite hojas legacy (sin año) si existe versión con año
            # - Omite hojas de configuración (Resumen, Licencias, Hoja1, etc.)
            # ================================================================
            
            # Sheets to skip (non-data sheets)
            skip_patterns = ['resumen', 'licencia', 'hoja1', 'config', 'plantilla', 'template']
            
            # Filter sheets: prefer "2025" versions, skip non-data sheets
            filtered_sheets = []
            locations_with_year = set()  # Track locations that have 2025 version
            
            # First pass: identify which locations have 2025 versions
            for sheet in all_sheet_names:
                sheet_lower = sheet.lower()
                if '2025' in sheet:
                    # Extract location name (e.g., "UIO 2025" -> "UIO")
                    location = sheet.replace('2025', '').strip()
                    locations_with_year.add(location.upper())
            
            # Second pass: filter sheets
            for sheet in all_sheet_names:
                sheet_lower = sheet.lower()
                
                # Skip non-data sheets
                if any(pattern in sheet_lower for pattern in skip_patterns):
                    logger.info(f"Omitiendo hoja '{sheet}' - hoja de configuración/resumen")
                    continue
                
                # Check if this is a legacy sheet (no year) and a 2025 version exists
                sheet_upper = sheet.upper().strip()
                if '2025' not in sheet:
                    # If there's a 2025 version of this location, skip the legacy one
                    if sheet_upper in locations_with_year:
                        logger.info(f"Omitiendo hoja '{sheet}' - existe versión 2025")
                        continue
                
                filtered_sheets.append(sheet)
            
            sheet_names = filtered_sheets if filtered_sheets else all_sheet_names
            
            # Show what sheets will be processed
            st.info(f"📚 **{len(all_sheet_names)} hojas en archivo** → **{len(sheet_names)} hojas a procesar:** {', '.join(sheet_names)}")
            
            if len(sheet_names) < len(all_sheet_names):
                skipped = set(all_sheet_names) - set(sheet_names)
                st.caption(f"⏭️ Omitidas: {', '.join(skipped)}")
            
            # Keywords that typically appear in header rows (more specific)
            header_keywords = [
                'IP INTERNA', 'IP PUBLICA', 'HOSTNAME', 'SERVIDOR', 
                'SISTEMA OPERATIVO', 'TIPO DE SERVIDOR', 'APLICACIÓN', 
                'BACKUP', 'RESPONSABLE', 'BASE DE DATOS', 'CIUDAD', 'ENCLOSURE'
            ]
            
            # Function to detect header row in a sheet
            def detect_header_row(df_raw):
                """
                Detecta la fila de encabezados buscando filas con:
                - Al menos 5 celdas no vacías
                - Al menos 3 keywords reconocidos
                - Longitud promedio de celda < 50 caracteres
                """
                best_match = 0
                best_row = None
                
                for idx, row in df_raw.iterrows():
                    # Count non-null values in the row
                    non_null_count = sum(1 for v in row.values if pd.notna(v) and str(v).strip())
                    
                    # Skip rows with very few values (likely title/metadata rows)
                    if non_null_count < 5:
                        continue
                    
                    # Count keyword matches
                    row_str = ' '.join([str(v).upper() for v in row.values if pd.notna(v)])
                    matches = sum(1 for kw in header_keywords if kw in row_str)
                    
                    # Check for column-like patterns (short text, no long sentences)
                    values = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip()]
                    avg_length = sum(len(v) for v in values) / max(len(values), 1)
                    
                    # Header rows typically have shorter cell values and more keyword matches
                    if matches >= 3 and avg_length < 50 and matches > best_match:
                        best_match = matches
                        best_row = idx
                
                return best_row, best_match
            
            # Process each sheet and combine
            all_dataframes = []
            sheets_processed = []
            
            for sheet_name in sheet_names:
                try:
                    # Read first 20 rows to detect header
                    df_raw = pd.read_excel(
                        excel_file, 
                        sheet_name=sheet_name, 
                        header=None, 
                        nrows=20
                    )
                    
                    header_row, match_count = detect_header_row(df_raw)
                    
                    # Skip sheets without valid header (e.g., "Resumen", "Licencia")
                    if header_row is None:
                        logger.info(f"Skipping sheet '{sheet_name}' - no valid header detected")
                        continue
                    
                    # Read the full sheet with detected header
                    df_sheet = pd.read_excel(
                        excel_file, 
                        sheet_name=sheet_name, 
                        header=header_row
                    )
                    
                    # Clean column names
                    df_sheet.columns = [str(col).strip() for col in df_sheet.columns]
                    
                    # Remove empty rows
                    df_sheet = df_sheet.dropna(how='all')
                    
                    # Add source sheet column for traceability
                    df_sheet['source_sheet'] = sheet_name
                    
                    all_dataframes.append(df_sheet)
                    sheets_processed.append(f"{sheet_name} ({len(df_sheet)} filas, header fila {header_row + 1})")
                    
                except Exception as e:
                    logger.warning(f"Error processing sheet '{sheet_name}': {e}")
                    continue
            
            # Combine all sheets
            if not all_dataframes:
                st.error("❌ No se encontraron hojas con datos válidos de servidores")
                return
            
            df = pd.concat(all_dataframes, ignore_index=True)
            
            # Show processing summary
            st.success(f"✅ **{len(df)} filas totales** de {len(sheets_processed)} hojas procesadas")
            
            with st.expander("📋 Detalle de hojas procesadas"):
                for sheet_info in sheets_processed:
                    st.caption(f"• {sheet_info}")
            
            # Show detected columns (excluding source_sheet and Unnamed)
            columns_display = [c for c in df.columns if not c.startswith('Unnamed') and c != 'source_sheet']
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
            # NOTA: Para servidores físicos, IP DEL BLADE es la columna IP alternativa
            detected_mappings = {
                'hostname': find_column(['SRV VIRTUAL', 'SERVIDOR', 'HOSTNAME', 'HOST', 'NOMBRE'], df.columns),
                'ip': find_column(['IP INTERNA', 'IP_INTERNA', 'IP ADDRESS', 'DIRECCION IP'], df.columns),
                'ip_blade': find_column(['IP DEL BLADE', 'IP BLADE', 'IP_BLADE', 'BLADE IP'], df.columns),  # Fallback para físicos
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
                    "Columna IP (Principal)", 
                    options=col_options,
                    index=col_options.index(detected_mappings['ip']) if detected_mappings['ip'] in col_options else 0,
                    key='map_ip',
                    help="IP INTERNA para servidores virtuales"
                )
                # IP DEL BLADE para servidores físicos
                ip_blade_col = st.selectbox(
                    "Columna IP Blade (Alternativa)", 
                    options=col_options,
                    index=col_options.index(detected_mappings['ip_blade']) if detected_mappings['ip_blade'] in col_options else 0,
                    key='map_ip_blade',
                    help="Se usa si IP Principal está vacía (común en servidores físicos)"
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
                            
                            # ====================================================
                            # LÓGICA DE IP CON FALLBACK
                            # 1. Intentar IP INTERNA (para virtuales)
                            # 2. Si está vacía, usar IP DEL BLADE (para físicos)
                            # ====================================================
                            ip = safe_get(ip_col)
                            if not ip and ip_blade_col:
                                ip = safe_get(ip_blade_col)  # Fallback para servidores físicos
                            
                            # ====================================================
                            # LÓGICA DE HOSTNAME CON FALLBACK
                            # Si no hay hostname pero sí IP, usar la IP como identificador
                            # ====================================================
                            hostname = safe_get(hostname_col)
                            if not hostname or hostname in ('', 'nan', 'None'):
                                if ip:
                                    hostname = ip  # Usar IP como hostname
                                else:
                                    hostname = f"unknown-{idx}"
                            
                            os_string = safe_get(os_col)
                            server_type = (safe_get(type_col) or '').upper()
                            owner = safe_get(owner_col)
                            app = safe_get(app_col)
                            backup_str = safe_get(backup_col) or ''
                            critical = safe_get(critical_col)
                            
                            # Get source sheet for traceability (from multi-sheet import)
                            source_sheet = safe_get('source_sheet') or 'default'
                            
                            # Skip truly empty rows (no hostname AND no IP)
                            if not hostname or hostname.startswith('unknown-'):
                                if not ip:
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
                            
                            # ====================================================
                            # NORMALIZACIÓN DE HOSTNAME
                            # Genera hostname canónico: srv-<ambiente>-<ciudad>-<rol>
                            # Ejemplo: XTR-SRV-PASMGYE -> srv-prod-gye-pasm
                            # ====================================================
                            hostname_canonical = get_canonical_hostname(
                                original=hostname,
                                environment=network_info.environment,
                                city=network_info.city
                            )
                            
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
                            
                            # Hostname canónico va primero para mejor visibilidad
                            processed_rows.append({
                                'hostname_canonical': hostname_canonical,  # Normalizado primero
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
                                'source_sheet': source_sheet,  # Trazabilidad de hoja de origen
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
                        st.session_state['import_ready'] = True
                        st.rerun()  # Rerun para mostrar el botón de confirmación
                    else:
                        st.warning("No se encontraron filas válidas para procesar")
            
            # ================================================================
            # BOTÓN DE CONFIRMACIÓN DE IMPORTACIÓN
            # Se muestra FUERA del bloque de procesamiento para evitar
            # que se pierda el estado cuando Streamlit hace rerun
            # ================================================================
            # Check import_ready AND that processed_import actually has data (is not None)
            if st.session_state.get('import_ready') and st.session_state.get('processed_import') is not None:
                processed_df = st.session_state['processed_import']
                
                st.success(f"✅ {len(processed_df)} servidores listos para importar")
                
                # Show preview
                render_import_preview(processed_df)
                
                col_btn1, col_btn2 = st.columns([1, 1])
                
                with col_btn1:
                    if st.button("💾 Confirmar Importación", type="primary", key="confirm_import"):
                        with st.spinner("Importando a base de datos..."):
                            import_to_database(processed_df)
                            st.session_state['import_ready'] = False
                            del st.session_state['processed_import']
                            st.rerun()
                
                with col_btn2:
                    if st.button("🗑️ Cancelar", key="cancel_import"):
                        st.session_state['import_ready'] = False
                        if 'processed_import' in st.session_state:
                            del st.session_state['processed_import']
                        st.rerun()
        
        except Exception as e:
            st.error(f"Error procesando archivo: {e}")
            logger.exception("Import error")


def import_to_database(df: pd.DataFrame):
    """
    Import processed DataFrame to database.
    Includes source_sheet for traceability when importing from multi-sheet Excel files.
    """
    conn = get_db()
    user = get_current_user()
    
    # Helper function to convert NaN to None for DuckDB compatibility
    def safe_value(val, default=None):
        """Convert NaN/None to default value for DuckDB."""
        if val is None:
            return default
        if isinstance(val, float) and pd.isna(val):
            return default
        return val
    
    try:
        imported = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                # Use source_sheet for traceability (format: "excel_import:SheetName")
                source_file = f"excel_import:{safe_value(row.get('source_sheet'), 'default')}"
                
                # Prepare values with NaN handling
                hostname_original = safe_value(row.get('hostname_original'), 'unknown')
                hostname_canonical = safe_value(row.get('hostname_canonical'), hostname_original)
                ip_address = safe_value(row.get('ip_address'))
                server_type = safe_value(row.get('server_type'), 'DESCONOCIDO')
                os_original = safe_value(row.get('os_original'))
                os_product_key = safe_value(row.get('os_product_key'), 'unknown')
                os_version = safe_value(row.get('os_version'))
                os_confidence = safe_value(row.get('os_confidence'), 1.0)
                environment = safe_value(row.get('environment'), 'unknown')
                city = safe_value(row.get('city'), 'unknown')
                eol_date = safe_value(row.get('eol_date'))
                eol_days_remaining = safe_value(row.get('eol_days_remaining'))
                # Convert to int if not None
                if eol_days_remaining is not None:
                    eol_days_remaining = int(eol_days_remaining)
                owner = safe_value(row.get('owner'))
                application = safe_value(row.get('application'))
                critical_system = safe_value(row.get('critical_system'))
                backup_enabled = bool(safe_value(row.get('backup_enabled'), False))
                health_score = safe_value(row.get('health_score'), 100)
                # Convert to int if not None
                if health_score is not None:
                    health_score = int(health_score)
                health_penalties = safe_value(row.get('health_penalties'), '')
                
                conn.execute("""
                    INSERT INTO servers (
                        hostname_original, hostname_canonical, ip_address, server_type,
                        os_original, os_product_key, os_version, os_confidence,
                        environment, city, eol_date, eol_days_remaining,
                        owner, application, critical_system,
                        backup_enabled, health_score, health_penalties,
                        created_at, updated_at, source_file
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    hostname_original,
                    hostname_canonical,
                    ip_address,
                    server_type,
                    os_original,
                    os_product_key,
                    os_version,
                    os_confidence,
                    environment,
                    city,
                    eol_date,
                    eol_days_remaining,
                    owner,
                    application,
                    critical_system,
                    backup_enabled,
                    health_score,
                    health_penalties,
                    datetime.now(),
                    datetime.now(),
                    source_file,
                ])
                imported += 1
            except Exception as e:
                errors.append(f"Fila {idx}: {str(e)}")
                logger.warning(f"Error importing row {idx}: {e}")
                continue
        
        if errors:
            st.warning(f"⚠️ {len(errors)} filas no se pudieron importar")
        
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
