import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from streamlit_lottie import st_lottie
from sqlalchemy import create_engine

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
@st.cache_data(ttl=300)
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
        st_lottie(lottie_header, height=110, key="header_anim")

st.markdown("---")

total_personal = len(df_personal)

if total_personal > 0:
    emo_series = df_personal['EMO'].astype(str).str.strip().str.upper()
    emo_aprobados = df_personal[emo_series.isin(['APROBADO', 'APTO', 'VIGENTE', 'SI', 'SÍ'])].shape[0]
    porcentaje_emo = (emo_aprobados / total_personal) * 100

    altura_series = df_personal['Trabajos en ALTURA'].astype(str).str.strip().str.upper()
    altura_aprobados = df_personal[altura_series.isin(['APROBADO', 'APTO', 'SI', 'SÍ', 'VIGENTE'])].shape[0]
    pendientes_altura = total_personal - altura_aprobados

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("👥 Total Personal", f"{total_personal}")
    m2.metric("🩺 EMO Aprobados", f"{emo_aprobados}", f"{porcentaje_emo:.1f}% del total")
    m3.metric("🏗️ Aprobados en Altura", f"{altura_aprobados}")
    m4.metric("⚠️ Pendientes en Altura", f"{pendientes_altura}")

    st.markdown("#### 📈 Indicadores Visuales de Cumplimiento")
    g1, g2 = st.columns(2)

    with g1:
        df_emo_chart = df_personal['EMO'].replace('', 'SIN REGISTRO').fillna('SIN REGISTRO').value_counts().reset_index()
        df_emo_chart.columns = ['Estado EMO', 'Cantidad']
        fig_donut = px.pie(
            df_emo_chart,
            names='Estado EMO',
            values='Cantidad',
            hole=0.45,
            title="<b>Distribución de Exámenes Médicos Ocupacionales (EMO)</b>",
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig_donut.update_layout(margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig_donut, use_container_width=True)

    with g2:
        df_alt_chart = df_personal['Trabajos en ALTURA'].replace('', 'SIN REGISTRO').fillna('SIN REGISTRO').value_counts().reset_index()
        df_alt_chart.columns = ['Estado Curso', 'Cantidad']
        fig_bar = px.bar(
            df_alt_chart,
            x='Estado Curso',
            y='Cantidad',
            color='Estado Curso',
            text='Cantidad',
            title="<b>Avance de Capacitación: Trabajos en ALTURA</b>",
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig_bar.update_traces(textposition='outside')
        fig_bar.update_layout(showlegend=False, margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig_bar, use_container_width=True)

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
