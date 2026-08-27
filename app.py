import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from streamlit_lottie import st_lottie
from sqlalchemy import create_engine
import numpy as np
import datetime

# ==========================================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==========================================================
st.set_page_config(
    page_title="Gestión de Cumplimiento HSEQ",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Columnas oficiales requeridas
COLUMNAS_HSEQ = [
    "ITEM", "Empresa", "Nombre y Apellidos", "DNI", "CARGO", "CELULAR", 
    "CORREO", "EMO", "FECHA", "LUGAR", "SCTR", "OC2", "personel", 
    "Induccion y orientacion basica", "Trabajos en ALTURA", "BLOQUEO de energia", 
    "Herramientas manuales y poder", "Herramientas criticas", "IPERC", "OBSERVACIONES"
]

# ==========================================================
# 2. CARGA DE ANIMACIONES (LOTTIE)
# ==========================================================
def load_lottie_url(url: str):
    """Descarga de forma segura animaciones Lottie con control de errores."""
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None

# Animación representativa de ingeniería, procesos y seguridad
LOTTIE_SECURITY_URL = "https://assets2.lottiefiles.com/packages/lf20_jbrw3hcz.json"
lottie_header = load_lottie_url(LOTTIE_SECURITY_URL)

# ==========================================================
# 3. CONEXIÓN A BASE DE DATOS (SUPABASE / POSTGRESQL)
# ==========================================================
@st.cache_resource
def get_database_engine():
    """Inicializa y reutiliza el pool de conexiones a la base de datos."""
    try:
        if "connections" in st.secrets and "supabase" in st.secrets["connections"]:
            db_url = st.secrets["connections"]["supabase"]["url"]
        elif "DATABASE_URL" in st.secrets:
            db_url = st.secrets["DATABASE_URL"]
        else:
            st.error("No se encontró la cadena de conexión en st.secrets.")
            st.stop()
            
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+psycopg2://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

        return create_engine(db_url, pool_pre_ping=True)
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        st.stop()

engine = get_database_engine()

# ==========================================================
# 4. LECTURA Y CACHÉ DE DATOS
# ==========================================================
@st.cache_data(ttl=10)
def load_data():
    """Carga los registros de la tabla 'personal' de Supabase."""
    try:
        query = "SELECT * FROM personal ORDER BY \"ITEM\" ASC"
        df = pd.read_sql(query, con=engine)
        
        for col in COLUMNAS_HSEQ:
            if col not in df.columns:
                df[col] = ""
        return df[COLUMNAS_HSEQ]
    except Exception:
        return pd.DataFrame(columns=COLUMNAS_HSEQ)

df_personal = load_data()

# ==========================================================
# 5. ENCABEZADO Y DASHBOARD INTERACTIVO
# ==========================================================
col_title, col_anim = st.columns([4, 1])

with col_title:
    st.title("🛡️ Sistema de Gestión y Cumplimiento HSEQ")
    st.caption("Control de Seguridad, Salud Ocupacional, Medio Ambiente y Calidad del Personal")

with col_anim:
    if lottie_header:
        st_lottie(lottie_header, height=80, key="header_anim")
    if st.button("🔄 Actualizar", use_container_width=True):
        load_data.clear()
        st.rerun()

st.markdown("---")

total_personal = len(df_personal)

if total_personal > 0:
    columnas_graficos = [
        "EMO", 
        "Induccion y orientacion basica", 
        "Trabajos en ALTURA", 
        "BLOQUEO de energia", 
        "Herramientas manuales y poder", 
        "Herramientas criticas", 
        "IPERC"
    ]
    
    # 1. CÁLCULO DE KPIs GLOBALES (6 MÉTRICAS CLAVE)
    total_requerimientos = total_personal * len(columnas_graficos)
    total_aprobados = 0
    tasas_aprobacion = {}
    
    df_aprobados = pd.DataFrame(index=df_personal.index)
    
    for col in columnas_graficos:
        s = df_personal[col].fillna('FALTANTE').astype(str).str.strip().str.upper()
        aprobados_mask = s.isin(['APROBADO', 'APTO', 'VIGENTE', 'SI', 'SÍ'])
        cant_aprobados = aprobados_mask.sum()
        total_aprobados += cant_aprobados
        tasas_aprobacion[col] = cant_aprobados / total_personal if total_personal > 0 else 0
        df_aprobados[col] = aprobados_mask
        
    cumplimiento_global = (total_aprobados / total_requerimientos) * 100 if total_requerimientos > 0 else 0
    
    punto_critico = min(tasas_aprobacion, key=tasas_aprobacion.get)
    tasa_critica = tasas_aprobacion[punto_critico] * 100
    
    fortaleza_principal = max(tasas_aprobacion, key=tasas_aprobacion.get)
    tasa_fortaleza = tasas_aprobacion[fortaleza_principal] * 100
    
    personal_100_pct = df_aprobados.all(axis=1).sum()
    brecha_total = total_requerimientos - total_aprobados
    
    st.markdown("#### 📊 Resumen Global de Rendimiento (6 KPIs Clave)")
    m1, m2, m3 = st.columns(3)
    m1.metric("👥 Total Personal", f"{total_personal}")
    m2.metric("🏆 Cumplimiento Global", f"{cumplimiento_global:.1f}%")
    m3.metric("⚠️ Punto Crítico", f"{punto_critico}", f"{tasa_critica:.1f}%", delta_color="inverse")
    
    st.write("") # Espacio visual
    m4, m5, m6 = st.columns(3)
    m4.metric("🌟 Personal al 100%", f"{personal_100_pct} personas", f"{(personal_100_pct/total_personal)*100 if total_personal > 0 else 0:.1f}% del total")
    m5.metric("🚨 Brecha Total", f"{brecha_total} faltas", "Certificaciones pendientes", delta_color="inverse")
    m6.metric("💪 Fortaleza Principal", f"{fortaleza_principal}", f"{tasa_fortaleza:.1f}%", delta_color="normal")
    
    st.markdown("---")
    
    # 2. ANÁLISIS DE TENDENCIA Y PROYECCIÓN AL 100%
    st.markdown("#### 🚀 Proyección Matemática al 100%")
    try:
        df_fechas = df_personal.copy()
        # Intentar convertir FECHA asumiendo día primero (ej. 24/08/2026)
        df_fechas['FECHA_PARSEADA'] = pd.to_datetime(df_fechas['FECHA'], errors='coerce', dayfirst=True)
        df_validas = df_fechas.dropna(subset=['FECHA_PARSEADA']).sort_values('FECHA_PARSEADA')
        
        if len(df_validas) > 2:
            df_validas['Contador'] = range(1, len(df_validas) + 1)
            df_validas['Porcentaje_Avance'] = (df_validas['Contador'] / total_personal) * 100
            
            # --- CALIBRACIÓN DE ESTANCAMIENTO ---
            # Inyectar el día de hoy si ya pasaron días sin nuevos registros
            hoy = pd.Timestamp(datetime.date.today())
            ultima_fecha = df_validas['FECHA_PARSEADA'].iloc[-1]
            ultimo_porcentaje = df_validas['Porcentaje_Avance'].iloc[-1]
            
            if hoy > ultima_fecha and ultimo_porcentaje < 100:
                nuevo_row = pd.DataFrame({
                    'FECHA_PARSEADA': [hoy],
                    'Porcentaje_Avance': [ultimo_porcentaje]
                })
                df_validas = pd.concat([df_validas, nuevo_row], ignore_index=True)
            
            fechas_ord = df_validas['FECHA_PARSEADA'].map(datetime.datetime.toordinal)
            z = np.polyfit(fechas_ord, df_validas['Porcentaje_Avance'], 1)
            p = np.poly1d(z)
            
            pendiente = z[0]
            if pendiente > 0:
                dias_para_100 = (100 - p(fechas_ord.iloc[-1])) / pendiente
                if dias_para_100 > 0:
                    fecha_100_ord = fechas_ord.iloc[-1] + dias_para_100
                    fecha_100 = datetime.datetime.fromordinal(int(fecha_100_ord))
                    st.info(f"🔮 Basado en la velocidad de ingresos históricos **(calibrado con el estancamiento al día de hoy)**, se estima alcanzar el **100% del personal registrado** el **{fecha_100.strftime('%d/%m/%Y')}**.")
                    
                    fechas_futuras = [df_validas['FECHA_PARSEADA'].iloc[-1], fecha_100]
                    porcentajes_futuros = [df_validas['Porcentaje_Avance'].iloc[-1], 100]
                    
                    fig_trend = px.line(
                        df_validas, 
                        x='FECHA_PARSEADA', 
                        y='Porcentaje_Avance',
                        markers=True,
                        title="Velocidad Histórica vs Proyección",
                        color_discrete_sequence=['#1f77b4']
                    )
                    
                    fig_trend.add_scatter(
                        x=fechas_futuras, 
                        y=porcentajes_futuros, 
                        mode='lines', 
                        line=dict(dash='dash', color='red'),
                        name='Tendencia al 100%'
                    )
                    
                    fig_trend.update_layout(yaxis_title="Personal Ingresado (%)", xaxis_title="Fechas Registradas", margin=dict(t=40, b=20, l=10, r=10), yaxis_range=[0, 105])
                    st.plotly_chart(fig_trend, use_container_width=True)
                else:
                    st.success("🎉 ¡El gráfico de avance ya alcanzó el 100% o la meta proyectada!")
            else:
                st.warning("📉 La tendencia matemática actual indica estancamiento. Faltan datos recientes con nuevas fechas para proyectar mejoras.")
        else:
            st.info("ℹ️ Para calcular la proyección matemática, necesitas registrar fechas válidas (ej. 24/08/2026) en al menos 3 filas de la tabla inferior.")
    except Exception as e:
        st.warning(f"No se pudo calcular la tendencia. Revisa que la columna 'FECHA' tenga fechas reales. Error técnico: {e}")

    st.markdown("#### 📈 Desglose Visual de Cumplimiento por Capacitación")
    
    # Crear un grid de 3 columnas para organizar los gráficos de forma ordenada
    cols = st.columns(3)
    
    for i, col_name in enumerate(columnas_graficos):
        with cols[i % 3]:
            # Limpiar datos: rellenar nulos reales, quitar espacios, convertir a mayúsculas y etiquetar
            cleaned_series = df_personal[col_name].fillna('FALTANTE').astype(str).str.strip().str.upper()
            cleaned_series = cleaned_series.replace(['', 'NAN', 'NONE'], 'FALTANTE')
            
            df_chart = cleaned_series.value_counts().reset_index()
            df_chart.columns = ['Estado', 'Cantidad']
            
            # Mapear colores específicos (Verde para APROBADO, Rojo para FALTANTE)
            color_map = {
                'APROBADO': '#28a745',
                'APTO': '#28a745',
                'VIGENTE': '#28a745',
                'SI': '#28a745',
                'SÍ': '#28a745',
                'FALTANTE': '#dc3545',
                'PENDIENTE': '#ffc107',
                'PROG': '#17a2b8'
            }
            
            fig = px.pie(
                df_chart,
                names='Estado',
                values='Cantidad',
                hole=0.45,
                title=f"<b>{col_name}</b>",
                color='Estado',
                color_discrete_map=color_map
            )
            # Agregar porcentajes y etiquetas dentro del gráfico para fácil lectura
            fig.update_traces(textposition='inside', textinfo='percent+label')
            # Ajustar los márgenes y ocultar la leyenda para que no ocupe tanto espacio
            fig.update_layout(margin=dict(t=40, b=20, l=10, r=10), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 🚨 Alertas de Personal Pendiente")
    alertas = []
    
    for index, row in df_personal.iterrows():
        nombre = row.get("Nombre y Apellidos", "Desconocido")
        if pd.isna(nombre) or str(nombre).strip() == "":
            nombre = "Colaborador sin nombre"
            
        faltas = []
        for col in columnas_graficos:
            val = str(row.get(col, '')).strip().upper()
            if val in ['', 'NAN', 'NONE', 'FALTANTE', 'PENDIENTE']:
                faltas.append(col)
                
        if faltas:
            alertas.append(f"**{nombre}** tiene pendiente: {', '.join(faltas)}")
            
    if alertas:
        with st.expander(f"⚠️ Ver lista de personal con capacitaciones pendientes ({len(alertas)} alertas)", expanded=True):
            for alerta in alertas:
                st.warning(alerta)
    else:
        st.success("✅ Todo el personal está al día con sus capacitaciones y exámenes.")

else:
    st.info("ℹ️ No hay registros cargados aún. Agrega nuevos colaboradores en la tabla inferior.")

# ==========================================================
# 6. EDITOR DE DATOS Y REGLA ESTRICTA ANTI-BORRADO
# ==========================================================
st.markdown("---")
st.subheader("📋 Matriz de Cumplimiento HSEQ (Edición en Tiempo Real)")
st.caption("💡 Puedes editar celdas o agregar nuevas filas al final. **Está estrictamente prohibido eliminar registros existentes.**")

dnis_originales = set(
    df_personal['DNI']
    .dropna()
    .astype(str)
    .str.strip()
)
dnis_originales = {dni for dni in dnis_originales if dni and dni.lower() != 'nan'}

edited_df = st.data_editor(
    df_personal,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    key="hseq_data_editor"
)

btn_col1, btn_col2 = st.columns([1, 1])

with btn_col1:
    if st.button("💾 Guardar Cambios en la Base de Datos", type="primary", use_container_width=True):
        dnis_editados = set(
            edited_df['DNI']
            .dropna()
            .astype(str)
            .str.strip()
        )
        dnis_editados = {dni for dni in dnis_editados if dni and dni.lower() != 'nan'}

        dnis_faltantes = dnis_originales - dnis_editados

        if len(dnis_faltantes) > 0:
            st.error(
                f"🚫 **ACCESO DENEGADO / ACCIÓN BLOQUEADA:** Se ha detectado la eliminación de {len(dnis_faltantes)} registro(s) "
                f"(DNI: {', '.join(list(dnis_faltantes)[:5])}{'...' if len(dnis_faltantes) > 5 else ''}).\n\n"
                f"Por política estricta de seguridad HSEQ, **no está permitido eliminar personal de la base de datos**. "
                f"Por favor, presiona **F5** o recarga la página para restaurar los datos."
            )
        else:
            try:
                with st.spinner("Guardando registros en Supabase..."):
                    df_to_save = edited_df.copy()
                    df_to_save.to_sql("personal", con=engine, if_exists="replace", index=False)
                    st.cache_data.clear()
                    st.success("✅ ¡Base de datos actualizada con éxito!")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Error al guardar en Supabase: {str(e)}")

with btn_col2:
    csv_data = edited_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Descargar CSV (Compatible con Google Sheets)",
        data=csv_data,
        file_name="Cumplimiento_HSEQ_Personal.csv",
        mime="text/csv",
        use_container_width=True
    )
