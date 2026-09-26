import streamlit as st
import pandas as pd
import sqlite3
import datetime
from datetime import date

# Configuración de página
st.set_page_config(page_title="Sistema Flota & Mantenimiento", layout="wide", page_icon="🚜")

# --- CONEXIÓN Y CREACIÓN DE BASE DE DATOS SQLITE ---
def get_connection():
    conn = sqlite3.connect("flota_integrada.db")
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Tabla Arreglos / Mantenimientos
    c.execute('''
        CREATE TABLE IF NOT EXISTS arreglos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE,
            interno TEXT,
            detalle TEXT,
            lugar_compra TEXT,
            costo REAL,
            km_horas REAL
        )
    ''')
    # Tabla Programación de Mantenimiento con Alarmas
    c.execute('''
        CREATE TABLE IF NOT EXISTS reprogramaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interno TEXT,
            servicio_programado TEXT,
            fecha_programada DATE,
            km_hora_objetivo REAL,
            km_hora_actual REAL,
            dias_aviso_previo INTEGER,
            estado TEXT DEFAULT 'PENDIENTE'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- PANEL DE NOTIFICACIONES Y ALARMAS EN BARRA LATERAL ---
st.sidebar.title("🚨 Panel de Alarmas y Alertas")

def verificar_alarmas():
    conn = get_connection()
    df_prog = pd.read_sql_query("SELECT * FROM reprogramaciones WHERE estado = 'PENDIENTE'", conn)
    conn.close()
    
    if df_prog.empty:
        st.sidebar.success("No hay alarmas pendientes.")
        return

    hoy = date.today()
    alertas_count = 0
    
    for _, row in df_prog.iterrows():
        alerta_fecha = False
        alerta_km = False
        
        # Alarma por Fecha
        if pd.notnull(row['fecha_programada']):
            fecha_prog = datetime.datetime.strptime(str(row['fecha_programada']), "%Y-%m-%d").date()
            dias_restantes = (fecha_prog - hoy).days
            if dias_restantes <= row['dias_aviso_previo']:
                alerta_fecha = True
        
        # Alarma por KM / Horas
        if pd.notnull(row['km_hora_objetivo']) and pd.notnull(row['km_hora_actual']):
            diferencia_km = row['km_hora_objetivo'] - row['km_hora_actual']
            if diferencia_km <= 500: # Rango de aviso de 500 km / horas
                alerta_km = True

        if alerta_fecha or alerta_km:
            alertas_count += 1
            st.sidebar.error(f"""
            **🚨 INTERNO {row['interno']}**
            - **Servicio:** {row['servicio_programado']}
            - **Fecha Límite:** {row['fecha_programada']}
            - **Objetivo KM/Hs:** {row['km_hora_objetivo']} (Actual: {row['km_hora_actual']})
            """)

verificar_alarmas()

# --- NAVEGACIÓN Y PESTAÑAS PRINCIPALES ---
st.title("🚜 Control Integrado de Flota, Mantenimiento y Alarmas")

tab_alertas, tab_crud, tab_stats, tab_busqueda = st.tabs([
    "⏰ Programación & Alarmas",
    "📝 Registrar / Modificar Datos",
    "📊 Estadísticas Mensuales y Anuales",
    "🔍 Consulta e Histórico Completo"
])

# --- PESTAÑA 1: PROGRAMACIÓN DE MANTENIMIENTO Y ALARMAS ---
with tab_alertas:
    st.header("⚙️ Programar Servicio Preventivo por Fecha o Kilometraje")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Nuevo Mantenimiento Programado")
        with st.form("form_programar"):
            p_interno = st.text_input("Interno / Vehículo (Ej. INT.24):")
            p_servicio = st.text_input("Detalle del Servicio (Ej. Cambio Aceite 15W40 y Filtros):")
            p_fecha = st.date_input("Fecha Programada / Estimada:", date.today())
            p_km_obj = st.number_input("Kilometraje / Horas Límite Objetivo:", min_value=0.0, step=100.0)
            p_km_act = st.number_input("Kilometraje / Horas Actuales:", min_value=0.0, step=100.0)
            p_dias_aviso = st.slider("Días Previos de Aviso (Alarma):", 1, 30, 7)
            
            submit_prog = st.form_submit_button("🔔 Programar y Activar Alarma")
            
            if submit_prog and p_interno:
                conn = get_connection()
                c = conn.cursor()
                c.execute('''
                    INSERT INTO reprogramaciones (interno, servicio_programado, fecha_programada, km_hora_objetivo, km_hora_actual, dias_aviso_previo)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (p_interno, p_servicio, p_fecha, p_km_obj, p_km_act, p_dias_aviso))
                conn.commit()
                conn.close()
                st.success("Mantenimiento programado exitosamente con alarma activa.")
                st.rerun()

    with col2:
        st.subheader("📋 Mantenimientos Programados Activos")
        conn = get_connection()
        df_mantenimientos = pd.read_sql_query("SELECT * FROM reprogramaciones WHERE estado = 'PENDIENTE'", conn)
        conn.close()
        st.dataframe(df_mantenimientos, use_container_width=True)

# --- PESTAÑA 2: REGISTRAR / MODIFICAR DATOS (CRUD) ---
with tab_crud:
    st.header("📝 Gestión de Arreglos y Mantenimientos")
    
    accion = st.radio("Seleccione Acción:", ["➕ Registrar Nuevo", "✏️ Modificar / Eliminar Existente"], horizontal=True)
    
    if accion == "➕ Registrar Nuevo":
        with st.form("form_nuevo_arreglo"):
            st.subheader("Nuevo Arreglo o Servicio Realizado")
            f_fecha = st.date_input("Fecha:", date.today())
            f_interno = st.text_input("Interno / Unidad:")
            f_detalle = st.text_area("Detalle del Trabajo Realizado:")
            f_lugar = st.text_input("Lugar de Compra / Taller:")
            f_costo = st.number_input("Costo / Importe ($):", min_value=0.0, step=100.0)
            f_km = st.number_input("Kilometraje / Horas en la Fecha:", min_value=0.0, step=10.0)
            
            guardar = st.form_submit_button("💾 Guardar Registro")
            if guardar and f_interno:
                conn = get_connection()
                c = conn.cursor()
                c.execute('''
                    INSERT INTO arreglos (fecha, interno, detalle, lugar_compra, costo, km_horas)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (f_fecha, f_interno, f_detalle, f_lugar, f_costo, f_km))
                conn.commit()
                conn.close()
                st.success("Registro guardado con éxito.")
                st.rerun()

    elif accion == "✏️ Modificar / Eliminar Existente":
        conn = get_connection()
        df_datos = pd.read_sql_query("SELECT * FROM arreglos ORDER BY id DESC", conn)
        conn.close()
        
        if not df_datos.empty:
            st.subheader("Listado de Registros Modificables")
            sel_id = st.selectbox("Seleccione el ID del Registro a Editar:", df_datos['id'])
            
            row_edit = df_datos[df_datos['id'] == sel_id].iloc[0]
            
            with st.form("form_editar"):
                e_fecha = st.date_input("Fecha:", datetime.datetime.strptime(str(row_edit['fecha']), "%Y-%m-%d").date() if row_edit['fecha'] else date.today())
                e_interno = st.text_input("Interno:", value=str(row_edit['interno']))
                e_detalle = st.text_area("Detalle:", value=str(row_edit['detalle']))
                e_lugar = st.text_input("Lugar de Compra:", value=str(row_edit['lugar_compra'] or ''))
                e_costo = st.number_input("Costo ($):", value=float(row_edit['costo'] or 0.0))
                e_km = st.number_input("KM / Horas:", value=float(row_edit['km_horas'] or 0.0))
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    actualizar = st.form_submit_button("✏️ Guardar Cambios")
                with col_btn2:
                    eliminar = st.form_submit_button("🗑️ Eliminar Registro")

                if actualizar:
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute('''
                        UPDATE arreglos SET fecha=?, interno=?, detalle=?, lugar_compra=?, costo=?, km_horas=?
                        WHERE id=?
                    ''', (e_fecha, e_interno, e_detalle, e_lugar, e_costo, e_km, sel_id))
                    conn.commit()
                    conn.close()
                    st.success("Registro actualizado correctamente.")
                    st.rerun()
                    
                if eliminar:
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("DELETE FROM arreglos WHERE id=?", (sel_id,))
                    conn.commit()
                    conn.close()
                    st.warning("Registro eliminado.")
                    st.rerun()

# --- PESTAÑA 3: ESTADÍSTICAS MENSUALES Y ANUALES ---
with tab_stats:
    st.header("📊 Estadísticas de Mantenimiento y Costos")
    
    conn = get_connection()
    df_all = pd.read_sql_query("SELECT * FROM arreglos", conn)
    conn.close()
    
    if not df_all.empty:
        df_all['fecha'] = pd.to_datetime(df_all['fecha'])
        df_all['Año'] = df_all['fecha'].dt.year
        df_all['Mes'] = df_all['fecha'].dt.month
        df_all['Año_Mes'] = df_all['fecha'].dt.to_period('M').astype(str)

        st.subheader("Filtros de Análisis")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            anios = ["Todos"] + list(df_all['Año'].dropna().unique())
            sel_anio = st.selectbox("Filtrar por Año:", anios)
        
        df_filtered = df_all.copy()
        if sel_anio != "Todos":
            df_filtered = df_filtered[df_filtered['Año'] == sel_anio]

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Total de Arreglos/Servicios", len(df_filtered))
        with col_m2:
            st.metric("Inversión / Costo Total", f"${df_filtered['costo'].sum():,.2f}")

        st.subheader("Evolución Mensual de Mantenimientos")
        chart_data = df_filtered.groupby('Año_Mes').size().reset_index(name='Cantidad')
        st.bar_chart(chart_data, x='Año_Mes', y='Cantidad')

        st.subheader("Top Internos con Mayor Cantidad de Mantenimientos")
        top_internos = df_filtered.groupby('interno').size().reset_index(name='Cantidad').sort_values(by='Cantidad', ascending=False).head(10)
        st.dataframe(top_internos, use_container_width=True)
    else:
        st.info("No existen registros cargados en la base de datos para generar estadísticas.")

# --- PESTAÑA 4: BÚSQUEDA Y CONSULTA GENERAL ---
with tab_busqueda:
    st.header("🔍 Consultar Registros")
    conn = get_connection()
    df_consulta = pd.read_sql_query("SELECT * FROM arreglos ORDER BY fecha DESC", conn)
    conn.close()
    
    filtro_txt = st.text_input("Buscar por Interno, Trabajo o Taller:")
    if filtro_txt:
        df_consulta = df_consulta[df_consulta.astype(str).apply(lambda x: x.str.contains(filtro_txt, case=False)).any(axis=1)]
    
    st.dataframe(df_consulta, use_container_width=True)
