import streamlit as st
import PyPDF2
from openai import OpenAI
import sqlite3
import pandas as pd

st.set_page_config(page_title="LexIA - Tu Tutor de Derecho", page_icon="⚖️", layout="wide")

conn = sqlite3.connect('derecho_app.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS materias (id INTEGER PRIMARY KEY, nombre TEXT, profesor TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS apuntes (id INTEGER PRIMARY KEY, materia_id INTEGER, nombre_archivo TEXT, texto TEXT)')
conn.commit()

st.sidebar.title("⚖️ LexIA")
api_key = st.sidebar.text_input("🔑 Tu OpenAI API Key", type="password", help="Consíguela en platform.openai.com")

menu = st.sidebar.radio("Navegación", ["📚 Mis Materias", "🧠 Sala de Estudio"])

def generar_respuesta_ia(prompt, texto, api_key):
    if not api_key:
        return "⚠️ Por favor, ingresa tu API Key de OpenAI en la barra lateral."
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un catedrático experto en Derecho. Ayuda a un estudiante a aprobar con claridad y precisión."},
                {"role": "user", "content": f"{prompt}\n\nTexto:\n{texto[:10000]}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error con la IA: {e}"

if menu == "📚 Mis Materias":
    st.title("Gestión de Materias")
    with st.expander("➕ Agregar Nueva Materia", expanded=True):
        col1, col2 = st.columns(2)
        nuevo_nombre = col1.text_input("Nombre de la Materia")
        nuevo_profesor = col2.text_input("Profesor titular")
        if st.button("Guardar Materia"):
            if nuevo_nombre:
                c.execute('INSERT INTO materias (nombre, profesor) VALUES (?, ?)', (nuevo_nombre, nuevo_profesor))
                conn.commit()
                st.success(f"Materia '{nuevo_nombre}' agregada.")
            else:
                st.warning("El nombre es obligatorio.")

    st.subheader("Tus Materias")
    df_materias = pd.read_sql_query("SELECT id, nombre as Materia, profesor as Profesor FROM materias", conn)
    if not df_materias.empty:
        st.dataframe(df_materias, hide_index=True, use_container_width=True)
        eliminar_id = st.selectbox("Selecciona el ID para eliminar materia", df_materias['id'].tolist())
        if st.button("🗑️ Eliminar Materia"):
            c.execute('DELETE FROM materias WHERE id=?', (eliminar_id,))
            c.execute('DELETE FROM apuntes WHERE materia_id=?', (eliminar_id,))
            conn.commit()
            st.success("Materia eliminada. Recarga la página.")
    else:
        st.info("No has agregado ninguna materia.")

elif menu == "🧠 Sala de Estudio":
    st.title("Sala de Estudio con IA")
    materias = pd.read_sql_query("SELECT * FROM materias", conn)
    if materias.empty:
        st.warning("Agrega una materia primero.")
    else:
        materia_seleccionada = st.selectbox("Selecciona materia para estudiar", materias['nombre'].tolist())
        materia_id = materias[materias['nombre'] == materia_seleccionada]['id'].values[0]
        st.divider()
        st.subheader("1. Sube material (PDF)")
        archivo_pdf = st.file_uploader("Sube apuntes o leyes", type="pdf")
        if archivo_pdf:
            if st.button("Procesar y Guardar PDF"):
                lector = PyPDF2.PdfReader(archivo_pdf)
                texto_extraido = "".join([p.extract_text() for p in lector.pages])
                c.execute('INSERT INTO apuntes (materia_id, nombre_archivo, texto) VALUES (?, ?, ?)', 
                          (int(materia_id), archivo_pdf.name, texto_extraido))
                conn.commit()
                st.success("Material guardado!")

        apuntes = pd.read_sql_query(f"SELECT * FROM apuntes WHERE materia_id={materia_id}", conn)
        if not apuntes.empty:
            st.subheader("2. Herramientas de estudio")
            apunte_seleccionado = st.selectbox("Selecciona un documento", apuntes['nombre_archivo'].tolist())
            texto_estudio = apuntes[apuntes['nombre_archivo'] == apunte_seleccionado]['texto'].values[0]

            tab1, tab2, tab3 = st.tabs(["📝 Resumen", "🃏 Flashcards", "📝 Simulacro de examen"])
            with tab1:
                if st.button("Generar resumen"):
                    prompt = "Resume este texto para un estudiante de Derecho:"
                    st.write(generar_respuesta_ia(prompt, texto_estudio, api_key))
            with tab2:
                if st.button("Generar flashcards"):
                    prompt = "Genera 10 flashcards Pregunta:Respuesta del siguiente texto:"
                    st.write(generar_respuesta_ia(prompt, texto_estudio, api_key))
            with tab3:
                if st.button("Generar simulacro"):
                    prompt = "Crea un simulacro de examen con 5 preguntas tipo test basado en este texto:"
                    st.write(generar_respuesta_ia(prompt, texto_estudio, api_key))