import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import plotly.express as px
import json  # <--- Esta es la clave para el nuevo truco

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Sistema Eclesial (Nube)",
    page_icon="☁️",
    layout="wide"
)

# ==========================================
# CONEXIÓN INTELIGENTE (Versión "Caja Fuerte")
# ==========================================
@st.cache_resource
def conectar_google_sheets():
    """Conecta con Google Sheets usando archivo local O JSON String en la nube."""
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    try:
        # 1. Intentamos leer el JSON completo desde los Secretos (Nuevo Método)
        # Esto busca una variable llamada 'google_json' en los secretos de Streamlit
        if "google_json" in st.secrets:
            # Leemos el texto y lo convertimos a diccionario automáticamente
            json_str = st.secrets["google_json"]
            creds_dict = json.loads(json_str)
            
            # --- PARCHE DE SEGURIDAD (SOLUCIÓN AL ERROR DE LA LLAVE) ---
            # A veces al copiar, los saltos de línea (\n) se quedan como texto literal
            # y rompen la clave. Esta línea fuerza a que sean saltos reales.
            if 'private_key' in creds_dict:
                creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
            # -----------------------------------------------------------

            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        
        # 2. Si no, buscamos el archivo local (Tu PC)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name('credenciales.json', scope)
            
        client = gspread.authorize(creds)
        sheet = client.open("Sistema_Iglesia_DB")
        return sheet
        
    except FileNotFoundError:
        st.error("🚨 ERROR: No encuentro el archivo 'credenciales.json' local.")
        return None
    except Exception as e:
        st.error(f"🚨 Error de conexión: {e}")
        return None

# ==========================================
# FUNCIONES DE BASE DE DATOS
# ==========================================
def obtener_datos(hoja_nombre):
    sh = conectar_google_sheets()
    if sh:
        try:
            worksheet = sh.worksheet(hoja_nombre)
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

def guardar_datos(hoja_nombre, lista_datos):
    sh = conectar_google_sheets()
    if sh:
        try:
            worksheet = sh.worksheet(hoja_nombre)
            datos_limpios = [str(d) if isinstance(d, (datetime, pd.Timestamp)) else d for d in lista_datos]
            worksheet.append_row(datos_limpios)
            return True
        except Exception as e:
            st.error(f"Error guardando: {e}")
            return False
    return False

# ==========================================
# INTERFAZ DE USUARIO
# ==========================================
st.sidebar.title("☁️ Gestión Eclesial")
menu = st.sidebar.radio("Navegación:", ["🏠 Inicio", "👥 Personas", "📊 Asistencia", "🎓 Educación"])

if menu == "🏠 Inicio":
    st.title("Bienvenido al Sistema Online")
    st.info("Este sistema está conectado a Google Drive en tiempo real.")
    
    col1, col2 = st.columns(2)
    with st.spinner("Conectando..."):
        df = obtener_datos("miembros")
    
    if not df.empty:
        col1.metric("Miembros Registrados", len(df))
        st.success("✅ Conexión Establecida")
    else:
        st.warning("⚠️ Sin conexión o sin datos")

elif menu == "👥 Personas":
    st.title("Directorio de Personas")
    tab1, tab2 = st.tabs(["Nuevo Registro", "Ver Lista"])
    
    with tab1:
        with st.form("nuevo_miembro", clear_on_submit=True):
            nombre = st.text_input("Nombre Completo")
            c1, c2 = st.columns(2)
            fecha = c1.date_input("Fecha Nacimiento", min_value=datetime(1920,1,1))
            sexo = c2.selectbox("Sexo", ["Masculino", "Femenino"])
            c3, c4 = st.columns(2)
            tel = c3.text_input("Teléfono")
            dire = c4.text_input("Dirección")
            tipo = st.radio("Tipo", ["Miembro", "Visitante", "Niño"], horizontal=True)
            
            if st.form_submit_button("Guardar"):
                if nombre:
                    guardar_datos("miembros", [nombre, fecha, sexo, tel, dire, tipo])
                    st.success("Guardado exitosamente")
                    st.cache_resource.clear()
    
    with tab2:
        if st.button("🔄 Actualizar"): st.cache_resource.clear()
        st.dataframe(obtener_datos("miembros"), use_container_width=True)

elif menu == "📊 Asistencia":
    st.title("Asistencia")
    c1, c2 = st.columns([1,2])
    with c1:
        with st.form("asist_form"):
            f = st.date_input("Fecha")
            c = st.number_input("Cantidad", min_value=0)
            t = st.selectbox("Evento", ["Culto General", "Jóvenes", "Oración"])
            if st.form_submit_button("Registrar"):
                guardar_datos("asistencia", [f, c, t])
                st.success("Registrado")
                st.cache_resource.clear()
    
    with c2:
        df = obtener_datos("asistencia")
        if not df.empty:
            df['Fecha'] = pd.to_datetime(df['Fecha'])
            df = df.sort_values('Fecha')
            fig = px.bar(df, x='Fecha', y='Cantidad', color='Tipo_Reunion')
            st.plotly_chart(fig, use_container_width=True)

elif menu == "🎓 Educación":
    st.title("Educación")
    df_m = obtener_datos("miembros")
    nombres = df_m['Nombre'].tolist() if not df_m.empty and 'Nombre' in df_m.columns else []
    
    c1, c2 = st.columns(2)
    alumno = c1.selectbox("Alumno", nombres) if nombres else None
    libro = c2.selectbox("Libro", ["Fundamentos", "Vida Discipular", "Liderazgo"])
    
    if st.button("Marcar Completado"):
        if alumno:
            guardar_datos("educacion", [alumno, libro, datetime.now().date()])
            st.success("Guardado")
            st.cache_resource.clear()
            
    st.dataframe(obtener_datos("educacion"), use_container_width=True)
