import streamlit as st
import pandas as pd
from geopy.geocoders import GoogleV3
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError
import time
import traceback
import io
import numpy as np
import html
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide", page_title="Visor/Geocodificador Escolar")

COLOR_PALETTE = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5', '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5']
DEFAULT_COLOR = '#808080'

@st.cache_data(ttl=3600, show_spinner=False)
def load_process_data(_uploaded_file_obj, _attempt_geocoding, _street_col_name=None, _commune_col_name=None):
    file_name = _uploaded_file_obj.name
    _uploaded_file_obj.seek(0)
    try:
        df = pd.read_excel(_uploaded_file_obj)
        df.columns = [str(col).strip().upper() for col in df.columns]

        lat_col_geo, lon_col_geo = 'LATITUD_GEO', 'LONGITUD_GEO'
        lat_col_orig, lon_col_orig = 'LATITUD', 'LONGITUD'
        use_existing_coords = False
        existing_lat_col_used, existing_lon_col_used = None, None

        if lat_col_geo in df.columns and lon_col_geo in df.columns:
            df[lat_col_geo] = pd.to_numeric(df[lat_col_geo], errors='coerce')
            df[lon_col_geo] = pd.to_numeric(df[lon_col_geo], errors='coerce')
            if df[[lat_col_geo, lon_col_geo]].dropna().shape[0] > 0:
                existing_lat_col_used, existing_lon_col_used = lat_col_geo, lon_col_geo
                use_existing_coords = True
        elif lat_col_orig in df.columns and lon_col_orig in df.columns:
            df[lat_col_orig] = pd.to_numeric(df[lat_col_orig], errors='coerce')
            df[lon_col_orig] = pd.to_numeric(df[lon_col_orig], errors='coerce')
            if df[[lat_col_orig, lon_col_orig]].dropna().shape[0] > 0:
                existing_lat_col_used, existing_lon_col_used = lat_col_orig, lon_col_orig
                use_existing_coords = True

        df['LATITUD_GEO_FINAL'] = pd.NA
        df['LONGITUD_GEO_FINAL'] = pd.NA

        if use_existing_coords and not _attempt_geocoding:
            df['LATITUD_GEO_FINAL'] = df[existing_lat_col_used]
            df['LONGITUD_GEO_FINAL'] = df[existing_lon_col_used]
            df['GEOCODING_STATUS'] = np.where(df['LATITUD_GEO_FINAL'].notna() & df['LONGITUD_GEO_FINAL'].notna(), 'Coords Existentes Válidas', 'Coords Existentes Inválidas/Ausentes')
            valid_count = df['GEOCODING_STATUS'].eq('Coords Existentes Válidas').sum()
            invalid_count = len(df) - valid_count
            return df, valid_count, invalid_count, True
        elif _attempt_geocoding:
            _street_col_name_upper = str(_street_col_name).strip().upper() if _street_col_name else None
            _commune_col_name_upper = str(_commune_col_name).strip().upper() if _commune_col_name else None
            if not _street_col_name_upper or not _commune_col_name_upper: st.error("Faltan nombres de columna de dirección/comuna."); return None, 0, 0, False
            if _street_col_name_upper not in df.columns: st.error(f"Columna dirección '{_street_col_name}' no encontrada."); return None, 0, 0, False
            if _commune_col_name_upper not in df.columns: st.error(f"Columna comuna '{_commune_col_name}' no encontrada."); return None, 0, 0, False
            try: API_KEY_GOOGLE = st.secrets["GOOGLE_API_KEY"]
            except KeyError: st.error("GOOGLE_API_KEY no encontrada."); return None, 0, 0, False
            if not API_KEY_GOOGLE or API_KEY_GOOGLE == "TU_API_KEY_DE_GOOGLE_VA_AQUI": st.error("GOOGLE_API_KEY no configurada."); return None, 0, 0, False
            df['ADDRESS_USED_FOR_GEOCODING'] = ''; df['GEOCODING_STATUS'] = ''
            geolocator = GoogleV3(api_key=API_KEY_GOOGLE); total_rows = len(df); geocoded_count = 0; error_count = 0
            with st.status(f"Geocodificando {total_rows} direcciones...", expanded=True) as status_container:
                progress_bar = st.progress(0.0)
                for index, row in df.iterrows():
                    street_part=str(row[_street_col_name_upper]) if pd.notna(row[_street_col_name_upper]) else ''
                    commune_part=str(row[_commune_col_name_upper]) if pd.notna(row[_commune_col_name_upper]) else ''
                    full_address_parts=[part for part in [street_part.strip(),commune_part.strip(),"Chile"] if part]; address_to_find=", ".join(full_address_parts); df.loc[index,'ADDRESS_USED_FOR_GEOCODING']=address_to_find; current_progress_val=(index+1)/total_rows; progress_bar.progress(current_progress_val); status_container.update(label=f"Procesando {index+1}/{total_rows}: {address_to_find[:50]}...")
                    if not street_part and not commune_part: df.loc[index, 'GEOCODING_STATUS'] = 'Dir/Comuna vacías'; error_count+=1; continue
                    if not address_to_find or address_to_find.lower() == "chile": df.loc[index, 'GEOCODING_STATUS'] = 'Info insuficiente'; error_count+=1; continue
                    try:
                        location=geolocator.geocode(address_to_find,timeout=10)
                        if location: df.loc[index,'LATITUD_GEO_FINAL']=location.latitude; df.loc[index,'LONGITUD_GEO_FINAL']=location.longitude; df.loc[index,'GEOCODING_STATUS']='Éxito (Google)'; geocoded_count+=1
                        else: df.loc[index,'GEOCODING_STATUS']='No encontrado (Google)'; error_count+=1
                    except GeocoderTimedOut: df.loc[index,'GEOCODING_STATUS']='Error: Timeout'; error_count+=1
                    except(GeocoderUnavailable, GeocoderServiceError) as e: df.loc[index,'GEOCODING_STATUS']=f'Error servicio: {str(e)[:50]}'; error_count+=1
                    except Exception as e: df.loc[index,'GEOCODING_STATUS']=f'Error inesperado: {str(e)[:50]}'; error_count+=1
                status_container.update(label="¡Geocodificación completada!", state="complete", expanded=False)
            df['LATITUD_GEO_FINAL'] = pd.to_numeric(df['LATITUD_GEO_FINAL'], errors='coerce'); df['LONGITUD_GEO_FINAL'] = pd.to_numeric(df['LONGITUD_GEO_FINAL'], errors='coerce')
            return df, geocoded_count, error_count, False
        else:
            df['GEOCODING_STATUS'] = 'No procesado'
            return df, 0, len(df), False
    except Exception as e:
        st.error(f"Error crítico ({file_name}): {e}")
        return None, 0, 0, False

def get_course_color_map(courses):
    unique_courses = sorted(courses.astype(str).unique())
    color_map = {}
    for i, course in enumerate(unique_courses):
        color_map[course] = COLOR_PALETTE[i % len(COLOR_PALETTE)]
    return color_map

def sanitize_for_tooltip(text):
    if pd.isna(text): return ""
    text = str(text)
    return html.escape(text)

# --- Lógica Principal de tu App Streamlit ---
st.title("🗺️ Visor / Geocodificador Escolar por Curso")
st.markdown("Sube un archivo Excel. Visualiza por curso y filtra los datos.")

# --- Inicialización del Estado de Sesión ---
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None; st.session_state.geocoded_count = 0; st.session_state.error_count = 0
    st.session_state.file_name_processed = None; st.session_state.used_existing_coords = False
    st.session_state.show_geocoding_inputs = False; st.session_state.selected_grades = []
    st.session_state.course_color_map = {}; st.session_state.address_col_input = "Dirección"
    st.session_state.commune_col_input = "Comuna Residencia"

# --- Barra Lateral ---
with st.sidebar:
    st.header("1. Cargar Archivo")
    uploaded_file = st.file_uploader("Sube tu archivo Excel", type=["xlsx", "xls"], key="file_uploader", on_change=lambda: st.session_state.update(processed_data=None, selected_grades=[], course_color_map={}))
    attempt_geocode_button = False; process_existing_button = False

    if uploaded_file is not None and st.session_state.processed_data is None:
        try:
            df_headers = pd.read_excel(uploaded_file, nrows=0)
            df_headers.columns = [str(col).strip().upper() for col in df_headers.columns]
            has_lat_geo = 'LATITUD_GEO' in df_headers.columns; has_lon_geo = 'LONGITUD_GEO' in df_headers.columns
            has_lat_orig = 'LATITUD' in df_headers.columns; has_lon_orig = 'LONGITUD' in df_headers.columns
            if (has_lat_geo and has_lon_geo) or (has_lat_orig and has_lon_orig):
                st.session_state.show_geocoding_inputs = False; st.info("Detectadas columnas de coordenadas.")
            else:
                st.session_state.show_geocoding_inputs = True; st.info("No se detectaron coordenadas. Puedes geocodificar.")
        except Exception as e: st.warning(f"No se pudieron leer cabeceras: {e}"); st.session_state.show_geocoding_inputs = True

    if uploaded_file and st.session_state.show_geocoding_inputs:
        st.subheader("Opciones de Geocodificación");
        street_column_input = st.text_input("Col. Dirección:", value=st.session_state.address_col_input, key="street_col_widget")
        commune_column_input = st.text_input("Col. Comuna:", value=st.session_state.commune_col_input, key="commune_col_widget")
        st.session_state.address_col_input = street_column_input; st.session_state.commune_col_input = commune_column_input
        attempt_geocode_button = st.button("✨ Geocodificar", key="geocode_button", type="primary")
    elif uploaded_file:
        process_existing_button = st.button("📊 Procesar Archivo", key="process_button", type="primary", disabled=not uploaded_file)

    if (attempt_geocode_button or process_existing_button) and uploaded_file:
        attempt_geocoding = attempt_geocode_button
        df_processed, valid_count, invalid_count, used_existing = load_process_data(
            uploaded_file,
            _attempt_geocoding=attempt_geocoding,
            _street_col_name=st.session_state.address_col_input,
            _commune_col_name=st.session_state.commune_col_input
        )
        if df_processed is not None:
            st.session_state.processed_data = df_processed; st.session_state.geocoded_count = valid_count; st.session_state.error_count = invalid_count
            st.session_state.file_name_processed = uploaded_file.name; st.session_state.used_existing_coords = used_existing; st.success(f"Archivo procesado.")
            if not used_existing and attempt_geocoding:
                st.session_state.street_column_used = st.session_state.address_col_input
                st.session_state.commune_column_used = st.session_state.commune_col_input
            else: st.session_state.street_column_used = None; st.session_state.commune_column_used = None
            course_col_name = 'DESC GRADO' # Nombres de columna ahora en MAYÚSCULAS
            if course_col_name in df_processed.columns:
                st.session_state.course_color_map = get_course_color_map(df_processed[course_col_name])
                st.session_state.selected_grades = sorted(df_processed[course_col_name].astype(str).unique())
            else: st.warning(f"Columna de curso '{course_col_name}' no encontrada."); st.session_state.course_color_map = {}; st.session_state.selected_grades = []
        else: st.error("Error durante el procesamiento."); st.session_state.processed_data = None

    if st.session_state.processed_data is not None and st.session_state.course_color_map:
        st.header("2. Filtrar por Curso"); all_grades = sorted(st.session_state.course_color_map.keys())
        selected_grades_widget = st.multiselect("Selecciona Cursos:", options=all_grades, default=st.session_state.selected_grades, key="grade_filter_multiselect")
        if selected_grades_widget != st.session_state.selected_grades: st.session_state.selected_grades = selected_grades_widget; st.rerun()

    if st.session_state.course_color_map:
        st.header("3. Leyenda de Colores"); legend_html = ""
        for grade, color in sorted(st.session_state.course_color_map.items()):
            legend_html += f"<div style='margin-bottom: 5px;'><span style='background-color:{color}; border: 1px solid #ccc; border-radius: 4px; padding: 0px 8px; margin-right: 8px;'> </span>{html.escape(grade)}</div>"
        st.markdown(legend_html, unsafe_allow_html=True)

    if st.session_state.processed_data is not None:
        st.markdown("---"); st.header("4. Resumen"); st.write(f"Archivo: **{st.session_state.file_name_processed}**")
        if st.session_state.used_existing_coords: st.metric(label="Coords Válidas ✔️", value=st.session_state.geocoded_count); st.metric(label="Coords Inválidas/Ausentes ❌", value=st.session_state.error_count)
        else: st.metric(label="Geocod. Éxito ✔️", value=st.session_state.geocoded_count); st.metric(label="Geocod. Fallo/Error ❌", value=st.session_state.error_count)

# --- Mostrar Resultados Principales ---
if st.session_state.processed_data is not None:
    st.header("📍 Visualización y Datos")
    df_display_full = st.session_state.processed_data.copy()
    course_col_name = 'DESC GRADO' # Nombres de columna ahora en MAYÚSCULAS
    df_filtered = df_display_full
    if course_col_name in df_filtered.columns and st.session_state.selected_grades:
        df_filtered = df_filtered[df_filtered[course_col_name].astype(str).isin(st.session_state.selected_grades)]
    df_map = df_filtered.dropna(subset=['LATITUD_GEO_FINAL', 'LONGITUD_GEO_FINAL']).copy()

    if not df_map.empty:
        st.subheader("Mapa de Ubicaciones Filtrado")
        map_center = [df_map['LATITUD_GEO_FINAL'].mean(), df_map['LONGITUD_GEO_FINAL'].mean()]
        m = folium.Map(location=map_center, zoom_start=12, tiles='CartoDB positron')

        for idx, row in df_map.iterrows():
            grade_val = str(row.get(course_col_name, 'N/A')) # Obtener valor del grado
            marker_color = st.session_state.course_color_map.get(grade_val, DEFAULT_COLOR)

            # Tooltip (label al pasar el mouse) mostrará solo el grado
            tooltip_text = sanitize_for_tooltip(grade_val)

            folium.CircleMarker(
                location=[row['LATITUD_GEO_FINAL'], row['LONGITUD_GEO_FINAL']],
                radius=5,
                color=marker_color,
                fill=True,
                fill_color=marker_color,
                fill_opacity=0.7,
                weight=1,
                tooltip=tooltip_text, # Solo tooltip
                # popup=None # Sin popup
            ).add_to(m)

        st_folium(m, width='100%', height=700, returned_objects=[])
    else: st.warning("No hay coordenadas válidas para los cursos seleccionados.")

    # --- Tabla de Datos ---
    st.subheader("📋 Tabla de Datos Filtrados")
    df_table_display = df_filtered.copy()
    # Asegurar tipos string antes de mostrar/descargar
    for col_name_str_tbl in ['D.V', 'RUN', 'CELULAR']: # Nombres de columna en MAYÚSCULAS
        if col_name_str_tbl in df_table_display.columns: df_table_display[col_name_str_tbl] = df_table_display[col_name_str_tbl].astype(str)

    # Ordenar columnas
    base_cols_tbl = [course_col_name] if course_col_name in df_table_display.columns else []
    base_cols_tbl.extend(['LATITUD_GEO_FINAL', 'LONGITUD_GEO_FINAL', 'GEOCODING_STATUS'])
    if st.session_state.used_existing_coords:
         orig_lat_col_name_tbl = next((col for col in df_table_display.columns if col == 'LATITUD'), None)
         orig_lon_col_name_tbl = next((col for col in df_table_display.columns if col == 'LONGITUD'), None)
         if orig_lat_col_name_tbl and orig_lat_col_name_tbl not in base_cols_tbl: base_cols_tbl.insert(1, orig_lat_col_name_tbl);
         if orig_lon_col_name_tbl and orig_lon_col_name_tbl not in base_cols_tbl: base_cols_tbl.insert(2, orig_lon_col_name_tbl)
    elif st.session_state.street_column_used and st.session_state.commune_column_used:
        # Nombres de columna de dirección y comuna también deben estar en mayúsculas
        street_col_upper_tbl = str(st.session_state.street_column_used).strip().upper() if st.session_state.street_column_used else None
        commune_col_upper_tbl = str(st.session_state.commune_column_used).strip().upper() if st.session_state.commune_column_used else None
        if 'ADDRESS_USED_FOR_GEOCODING' in df_table_display.columns: base_cols_tbl.insert(1, 'ADDRESS_USED_FOR_GEOCODING')
        if commune_col_upper_tbl and commune_col_upper_tbl in df_table_display.columns: base_cols_tbl.insert(1, commune_col_upper_tbl)
        if street_col_upper_tbl and street_col_upper_tbl in df_table_display.columns: base_cols_tbl.insert(1, street_col_upper_tbl)
    other_cols_tbl = [col for col in df_table_display.columns if col not in base_cols_tbl and col not in ['LATITUD_GEO', 'LONGITUD_GEO']];
    final_cols_order_tbl = base_cols_tbl + other_cols_tbl
    final_cols_to_display_tbl = [col for col in final_cols_order_tbl if col in df_table_display.columns]
    st.dataframe(df_table_display[final_cols_to_display_tbl])

    # --- Descarga ---
    @st.cache_data
    def convert_df_to_excel(_df_to_convert, _cols_to_include):
        output = io.BytesIO(); df_download = _df_to_convert[_cols_to_include].copy()
        for col_name_str_dl_tbl in ['D.V', 'RUN', 'CELULAR']: # Nombres en MAYÚSCULAS
             if col_name_str_dl_tbl in df_download.columns: df_download[col_name_str_dl_tbl] = df_download[col_name_str_dl_tbl].astype(str)
        with pd.ExcelWriter(output, engine='openpyxl') as writer: df_download.to_excel(writer, index=False, sheet_name='DatosFiltrados')
        return output.getvalue()
    excel_data = convert_df_to_excel(df_table_display, final_cols_to_display_tbl)
    base_name_dl = st.session_state.file_name_processed.split('.')[0] if st.session_state.file_name_processed and '.' in st.session_state.file_name_processed else (st.session_state.file_name_processed or "datos")
    st.download_button("📥 Descargar Excel Filtrado", excel_data, f"{base_name_dl}_filtrado.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

elif uploaded_file is None and not st.session_state.processed_data:
    st.info("👈 Sube un archivo Excel en la barra lateral para comenzar.")