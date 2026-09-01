"""
App de Nutrición Deportiva - Streamlit + Supabase (PostgreSQL)

Ejecutar con: streamlit run app.py
"""
from datetime import datetime, date

import pandas as pd
import streamlit as st

import database as db
import utils_somatotype as som
import pdf_generator as pdfgen
import branding

st.set_page_config(page_title="Nutrición Deportiva", page_icon="🥗", layout="wide")


# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------
def login():
    st.sidebar.title("🔐 Ingreso")
    usuario = st.sidebar.text_input("Usuario")
    clave = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Ingresar", use_container_width=True):
        usuarios = st.secrets.get("auth", {}).get("users", {})
        if usuario in usuarios and clave == usuarios[usuario]:
            st.session_state["auth_user"] = usuario
            st.rerun()
        else:
            st.sidebar.error("Usuario o contraseña incorrectos.")


def logout():
    if st.sidebar.button("Cerrar sesión", use_container_width=True):
        del st.session_state["auth_user"]
        st.rerun()


# ---------------------------------------------------------------------------
# Página: Dashboard
# ---------------------------------------------------------------------------
def pagina_dashboard():
    st.title("🏠 Dashboard")

    c1, c2, c3 = st.columns(3)
    c1.metric("Atletas registrados", db.contar_atletas())
    c2.metric("Grupos", db.contar_grupos())
    c3.metric("Mediciones cargadas", db.contar_mediciones())

    st.subheader("Últimas mediciones cargadas")
    df = db.listar_ultimas_mediciones(20)
    if df.empty:
        st.info("Todavía no hay mediciones cargadas.")
        return

    df_show = df.rename(columns={
        "fecha_hora_carga": "Fecha y hora de carga",
        "fecha_medicion": "Fecha de medición",
        "nombre": "Nombre", "apellido": "Apellido", "nombre_grupo": "Grupo",
        "peso": "Peso (kg)", "imc": "IMC",
        "bio_grasa_corporal": "% Grasa corporal", "pct_musculo_esqueletico": "% Músculo esquelético",
        "cargado_por": "Cargado por",
    })
    cols = ["Fecha y hora de carga", "Fecha de medición", "Nombre", "Apellido", "Grupo",
            "Peso (kg)", "IMC", "% Grasa corporal", "% Músculo esquelético", "Cargado por"]
    st.dataframe(df_show[cols], use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Página: Gestión de Grupos
# ---------------------------------------------------------------------------
def pagina_grupos():
    st.title("👥 Gestión de Grupos")

    with st.expander("➕ Crear nuevo grupo", expanded=False):
        with st.form("form_nuevo_grupo", clear_on_submit=True):
            nombre = st.text_input("Nombre del grupo *")
            descripcion = st.text_area("Descripción")
            if st.form_submit_button("Crear grupo"):
                if nombre.strip():
                    db.crear_grupo(nombre, descripcion)
                    st.success(f"Grupo '{nombre}' creado.")
                    st.rerun()
                else:
                    st.warning("El nombre es obligatorio.")

    st.subheader("Grupos existentes")
    df = db.listar_grupos()
    if df.empty:
        st.info("No hay grupos creados todavía.")
        return

    for _, row in df.iterrows():
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{row['nombre_grupo']}**  ·  {row['cantidad_atletas']} atleta(s)")
                st.caption(row["descripcion"] or "Sin descripción")
            with col2:
                editar = st.toggle("Editar", key=f"edit_{row['id']}")
            if editar:
                with st.form(f"form_editar_{row['id']}"):
                    nuevo_nombre = st.text_input("Nombre", value=row["nombre_grupo"])
                    nueva_desc = st.text_area("Descripción", value=row["descripcion"] or "")
                    c1, c2 = st.columns(2)
                    guardar = c1.form_submit_button("💾 Guardar cambios")
                    eliminar = c2.form_submit_button("🗑️ Eliminar grupo")
                    if guardar:
                        db.actualizar_grupo(row["id"], nuevo_nombre, nueva_desc)
                        st.success("Grupo actualizado.")
                        st.rerun()
                    if eliminar:
                        db.eliminar_grupo(row["id"])
                        st.warning("Grupo eliminado.")
                        st.rerun()


# ---------------------------------------------------------------------------
# Página: Cargar Medición
# ---------------------------------------------------------------------------
def pagina_cargar_medicion():
    st.title("📝 Cargar Medición")

    grupos_dict = db.obtener_grupos_dict()
    if not grupos_dict:
        st.warning("Primero creá al menos un grupo en '👥 Gestión de Grupos'.")
        return

    st.subheader("1. Seleccionar atleta")
    modo = st.radio("¿El atleta ya existe?", ["Atleta existente", "Nuevo atleta"], horizontal=True)

    atleta = None
    if modo == "Atleta existente":
        df_atletas = db.listar_atletas()
        if df_atletas.empty:
            st.info("No hay atletas cargados todavía. Elegí 'Nuevo atleta'.")
            return
        opciones = {
            f"{r['apellido']}, {r['nombre']} ({r['nombre_grupo']})": r["id"]
            for _, r in df_atletas.iterrows()
        }
        seleccion = st.selectbox("Atleta", list(opciones.keys()))
        atleta = db.obtener_atleta(opciones[seleccion])
    else:
        with st.container(border=True):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre *")
            apellido = c2.text_input("Apellido *")
            c3, c4, c5 = st.columns(3)
            sexo = c3.selectbox("Sexo *", ["Masculino", "Femenino"])
            fecha_nacimiento = c4.date_input(
                "Fecha de nacimiento *", value=date(1995, 1, 1),
                min_value=date(1930, 1, 1), max_value=date.today(),
            )
            email = c5.text_input("Email")
            grupo_nombre = st.selectbox("Grupo *", list(grupos_dict.keys()))
            if st.button("Registrar atleta"):
                if nombre.strip() and apellido.strip():
                    nuevo_id = db.crear_atleta(grupos_dict[grupo_nombre], nombre, apellido, sexo, fecha_nacimiento, email)
                    st.session_state["nuevo_atleta_id"] = nuevo_id
                    st.success(f"Atleta {nombre} {apellido} registrado. Ahora cargá su medición abajo.")
                else:
                    st.warning("Nombre y apellido son obligatorios.")
        if st.session_state.get("nuevo_atleta_id"):
            atleta = db.obtener_atleta(st.session_state["nuevo_atleta_id"])

    if not atleta:
        return

    st.divider()
    st.subheader(f"2. Medición de {atleta['nombre']} {atleta['apellido']}")
    st.caption(f"Sexo: {atleta['sexo']} · Edad: {atleta['edad']} años · Grupo: {atleta['nombre_grupo']}")

    fecha_medicion = st.date_input("Fecha de la medición", value=date.today())

    st.markdown("**Datos principales**")
    c1, c2, c3 = st.columns(3)
    peso = c1.number_input("Peso (kg)", min_value=0.0, step=0.1, format="%.1f")
    talla_m = c2.number_input("Talla (m)", min_value=0.0, step=0.01, format="%.2f")
    altura = round(talla_m * 100, 1)  # cm, usado internamente en todos los cálculos
    c3.metric("IMC (kg/m²)", som.calcular_imc(peso, altura) or "-")

    c1, c2, c3 = st.columns(3)
    pct_musculo_esqueletico = c1.number_input("% Músculo esquelético estimado", min_value=0.0, step=0.1, format="%.1f")
    bio_grasa_corporal = c2.number_input("% Grasa corporal estimado", min_value=0.0, step=0.1, format="%.1f")
    bio_grasa_visceral = c3.number_input("% Grasa visceral estimada", min_value=0.0, step=0.1, format="%.1f")

    c1, c2, c3 = st.columns(3)
    cintura = c1.number_input("Circ. cintura (cm)", min_value=0.0, step=0.1, format="%.1f")
    cadera = c2.number_input("Circ. cadera (cm)", min_value=0.0, step=0.1, format="%.1f")
    pliegue_abdominal = c3.number_input("Pliegue abdominal (mm)", min_value=0.0, step=0.1, format="%.1f")

    observaciones = st.text_area("Observación")

    with st.expander("📐 Mediciones avanzadas (ISAK) — opcional, para somatotipo e informe completo"):
        st.caption("Se completan solo si se quiere el detalle ISAK completo (somatotipo, % músculo/grasa por pliegues, etc). Si se dejan en blanco, esas secciones no aparecen en el informe individual.")

        st.markdown("**Datos adicionales**")
        c1, c2 = st.columns(2)
        talla_sentado = c1.number_input("Talla sentado (cm)", min_value=0.0, step=0.1, format="%.1f")

        st.markdown("**Perímetros (cm)**")
        c1, c2, c3 = st.columns(3)
        brazo_relajado = c1.number_input("Brazo relajado", min_value=0.0, step=0.1, format="%.1f")
        brazo_contraido = c2.number_input("Brazo contraído", min_value=0.0, step=0.1, format="%.1f")
        perimetro_muslo = c3.number_input("Muslo medio (perímetro)", min_value=0.0, step=0.1, format="%.1f")
        perimetro_pantorrilla = st.number_input("Pantorrilla (perímetro)", min_value=0.0, step=0.1, format="%.1f")

        st.markdown("**Pliegues cutáneos ISAK (mm)**")
        st.caption("El pliegue abdominal ya se cargó arriba, se reutiliza acá para la sumatoria de 6 pliegues.")
        c1, c2, c3 = st.columns(3)
        pliegue_tricipital = c1.number_input("Tricipital", min_value=0.0, step=0.1, format="%.1f")
        pliegue_subescapular = c2.number_input("Subescapular", min_value=0.0, step=0.1, format="%.1f")
        pliegue_suprailiaco = c3.number_input("Suprailíaco", min_value=0.0, step=0.1, format="%.1f")
        c4, c5 = st.columns(2)
        pliegue_muslo = c4.number_input("Muslo medio (pliegue)", min_value=0.0, step=0.1, format="%.1f")
        pliegue_pantorrilla = c5.number_input("Pantorrilla (pliegue)", min_value=0.0, step=0.1, format="%.1f")

        st.markdown("**Diámetros óseos (cm)** — necesarios para la mesomorfia de Heath-Carter")
        c1, c2 = st.columns(2)
        diam_humero = c1.number_input("Diámetro biepicondilar húmero", min_value=0.0, step=0.1, format="%.1f")
        diam_femur = c2.number_input("Diámetro biepicondilar fémur", min_value=0.0, step=0.1, format="%.1f")

        st.markdown("**Bioimpedancia adicional**")
        c1, c2, c3 = st.columns(3)
        bio_agua_corporal = c1.number_input("% Agua corporal", min_value=0.0, step=0.1, format="%.1f")
        bio_masa_muscular = c2.number_input("Masa muscular (kg)", min_value=0.0, step=0.1, format="%.1f")
        bio_masa_osea = c3.number_input("Masa ósea (kg)", min_value=0.0, step=0.1, format="%.1f")
        c4, c5 = st.columns(2)
        bio_metabolismo_basal = c4.number_input("Metabolismo basal (kcal)", min_value=0.0, step=1.0, format="%.0f")
        bio_edad_metabolica = c5.number_input("Edad metabólica (años)", min_value=0.0, step=1.0, format="%.0f")

    # --- Cálculo en tiempo real ---
    imc = som.calcular_imc(peso, altura)
    indice_cc = som.calcular_indice_cintura_cadera(cintura, cadera)
    indice_ct = som.calcular_indice_cintura_talla(cintura, altura)
    sumatoria_6 = som.calcular_sumatoria_6_pliegues(
        pliegue_tricipital, pliegue_subescapular, pliegue_suprailiaco,
        pliegue_abdominal, pliegue_muslo, pliegue_pantorrilla,
    )
    pct_grasa = som.calcular_porcentaje_grasa_yuhasz(sumatoria_6, atleta["sexo"])
    pct_musculo = som.calcular_porcentaje_musculo_martin(
        peso, altura, brazo_relajado, pliegue_tricipital,
        perimetro_muslo, pliegue_muslo, perimetro_pantorrilla, pliegue_pantorrilla,
    )
    somatotipo = som.calcular_somatotipo(
        peso, altura, pliegue_tricipital, pliegue_subescapular, pliegue_suprailiaco,
        brazo_contraido, perimetro_pantorrilla, pliegue_pantorrilla, diam_humero, diam_femur,
    )

    st.divider()
    st.subheader("3. Resultados con referencia (semáforo)")
    sexo = atleta["sexo"]
    m1, m2 = st.columns(2)
    with m1:
        et, co = som.clasificar_metrica("imc", imc, sexo)
        branding.render_metric_badge("IMC (kg/m²)", imc or "-", et, co)
        et, co = som.clasificar_metrica("grasa_corporal_pct", bio_grasa_corporal, sexo)
        branding.render_metric_badge("% Grasa corporal estimado", bio_grasa_corporal or "-", et, co)
        et, co = som.clasificar_metrica("grasa_visceral", bio_grasa_visceral, sexo)
        branding.render_metric_badge("% Grasa visceral estimada", bio_grasa_visceral or "-", et, co)
        et, co = som.clasificar_metrica("musculo_esqueletico_pct", pct_musculo_esqueletico, sexo)
        branding.render_metric_badge("% Músculo esquelético estimado", pct_musculo_esqueletico or "-", et, co)
    with m2:
        et, co = som.clasificar_metrica("pliegue_abdominal", pliegue_abdominal, sexo)
        branding.render_metric_badge("Pliegue abdominal (mm)", pliegue_abdominal or "-", et, co)
        et, co = som.clasificar_metrica("circ_cintura", cintura, sexo)
        branding.render_metric_badge("Circ. cintura (cm)", cintura or "-", et, co)
        et, co = som.clasificar_metrica("indice_cintura_cadera", indice_cc, sexo)
        branding.render_metric_badge("Índice cintura/cadera", indice_cc or "-", et, co)
        et, co = som.clasificar_metrica("indice_cintura_talla", indice_ct, sexo)
        branding.render_metric_badge("Índice cintura/talla", indice_ct or "-", et, co)

    if sexo == "Femenino":
        st.caption("⚠️ Circ. cintura, índice cintura/cadera, índice cintura/talla y % músculo esquelético solo tienen referencia cargada para hombres — se muestran sin clasificar para mujeres hasta contar con esos valores.")

    if any([pliegue_tricipital, pliegue_subescapular, pliegue_suprailiaco, pliegue_muslo, pliegue_pantorrilla]):
        st.subheader("Resultados ISAK avanzados")
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Σ 6 pliegues (mm)", sumatoria_6)
        a2.metric("% Grasa (Yuhasz)", pct_grasa)
        a3.metric("% Músculo (Martin)", pct_musculo)
        a4.metric("Somatotipo", f"{somatotipo['endomorfia']}-{somatotipo['mesomorfia']}-{somatotipo['ectomorfia']}")

    if st.button("💾 Guardar medición", type="primary", use_container_width=True):
        data = dict(
            atleta_id=atleta["id"],
            fecha_hora_carga=datetime.now(),
            fecha_medicion=fecha_medicion,
            cargado_por=st.session_state.get("auth_user"),
            peso=peso or None, altura=altura or None, talla_sentado=talla_sentado or None,
            brazo_relajado=brazo_relajado or None, brazo_contraido=brazo_contraido or None,
            cintura=cintura or None, cadera=cadera or None,
            perimetro_muslo_medio=perimetro_muslo or None, perimetro_pantorrilla=perimetro_pantorrilla or None,
            pliegue_tricipital=pliegue_tricipital or None, pliegue_subescapular=pliegue_subescapular or None,
            pliegue_suprailiaco=pliegue_suprailiaco or None, pliegue_abdominal=pliegue_abdominal or None,
            pliegue_muslo_medio=pliegue_muslo or None, pliegue_pantorrilla=pliegue_pantorrilla or None,
            diam_humero=diam_humero or None, diam_femur=diam_femur or None,
            bio_grasa_corporal=bio_grasa_corporal or None, bio_agua_corporal=bio_agua_corporal or None,
            bio_masa_muscular=bio_masa_muscular or None, bio_masa_osea=bio_masa_osea or None,
            bio_grasa_visceral=bio_grasa_visceral or None, bio_metabolismo_basal=bio_metabolismo_basal or None,
            bio_edad_metabolica=bio_edad_metabolica or None,
            pct_musculo_esqueletico=pct_musculo_esqueletico or None,
            indice_cintura_cadera=indice_cc or None, indice_cintura_talla=indice_ct or None,
            imc=imc or None,
            porcentaje_grasa=pct_grasa or None, porcentaje_musculo=pct_musculo or None,
            sumatoria_6_pliegues=sumatoria_6 or None,
            endomorfia=somatotipo["endomorfia"] or None, mesomorfia=somatotipo["mesomorfia"] or None,
            ectomorfia=somatotipo["ectomorfia"] or None,
            coord_x=somatotipo["coord_x"] or None, coord_y=somatotipo["coord_y"] or None,
            observaciones=observaciones,
        )
        db.crear_medicion(data)
        st.session_state.pop("nuevo_atleta_id", None)
        st.success("Medición guardada correctamente.")
        st.balloons()


# ---------------------------------------------------------------------------
# Página: Perfil de Atleta
# ---------------------------------------------------------------------------
def pagina_perfil_atleta():
    st.title("📊 Perfil de Atleta")

    grupos_dict = db.obtener_grupos_dict()
    c1, c2, c3 = st.columns(3)
    nombre_f = c1.text_input("Filtrar por nombre")
    apellido_f = c2.text_input("Filtrar por apellido")
    grupo_f = c3.selectbox("Filtrar por grupo", ["Todos"] + list(grupos_dict.keys()))

    grupo_id = grupos_dict.get(grupo_f) if grupo_f != "Todos" else None
    df_atletas = db.listar_atletas(grupo_id=grupo_id, nombre_filtro=nombre_f, apellido_filtro=apellido_f)

    if df_atletas.empty:
        st.info("No se encontraron atletas con esos filtros.")
        return

    opciones = {
        f"{r['apellido']}, {r['nombre']} ({r['nombre_grupo']})": r["id"]
        for _, r in df_atletas.iterrows()
    }
    seleccion = st.selectbox("Seleccioná un atleta", list(opciones.keys()))
    atleta = db.obtener_atleta(opciones[seleccion])
    st.session_state["atleta_perfil_actual"] = atleta

    st.caption(f"Sexo: {atleta['sexo']} · Edad: {atleta['edad']} · Grupo: {atleta['nombre_grupo']} · Email: {atleta.get('email') or '-'}")

    df_hist = db.listar_mediciones_atleta(atleta["id"])
    if df_hist.empty:
        st.info("Este atleta todavía no tiene mediciones cargadas.")
        return

    st.subheader("Historial de mediciones")
    cols_show = ["fecha_medicion", "fecha_hora_carga", "peso", "imc", "bio_grasa_corporal",
                 "pct_musculo_esqueletico", "bio_grasa_visceral", "cintura", "cadera",
                 "indice_cintura_cadera", "indice_cintura_talla", "pliegue_abdominal"]
    st.dataframe(df_hist[cols_show], use_container_width=True, hide_index=True)

    tab1, tab2 = st.tabs(["📈 Evolución temporal", "🔺 Somatocarta"])

    with tab1:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_hist["fecha_medicion"], y=df_hist["peso"], mode="lines+markers", name="Peso (kg)"))
        fig.add_trace(go.Scatter(x=df_hist["fecha_medicion"], y=df_hist["pct_musculo_esqueletico"], mode="lines+markers", name="% Músculo esquelético", yaxis="y2"))
        fig.add_trace(go.Scatter(x=df_hist["fecha_medicion"], y=df_hist["bio_grasa_corporal"], mode="lines+markers", name="% Grasa corporal", yaxis="y2"))
        fig.update_layout(
            xaxis_title="Fecha de medición", yaxis=dict(title="Peso (kg)"),
            yaxis2=dict(title="%", overlaying="y", side="right"),
            height=450, legend=dict(orientation="h"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        puntos = [
            {"x": r["coord_x"], "y": r["coord_y"], "fecha": str(r["fecha_medicion"]),
             "endomorfia": r["endomorfia"], "mesomorfia": r["mesomorfia"], "ectomorfia": r["ectomorfia"]}
            for _, r in df_hist.iterrows() if pd.notna(r["coord_x"])
        ]
        fig = som.crear_grafico_somatocarta(puntos, titulo=f"Somatocarta - {atleta['nombre']} {atleta['apellido']}")
        st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Página: Exportar & Reportes
# ---------------------------------------------------------------------------
def pagina_exportar():
    st.title("📑 Exportar & Reportes")

    tab1, tab2, tab3 = st.tabs(["📄 Reporte Individual", "📈 Historial Individual", "👥 Estadística por Grupo"])

    # --- Reporte individual (PDF) ---
    with tab1:
        df_atletas = db.listar_atletas()
        if df_atletas.empty:
            st.info("No hay atletas cargados.")
        else:
            opciones = {f"{r['apellido']}, {r['nombre']} ({r['nombre_grupo']})": r["id"] for _, r in df_atletas.iterrows()}
            seleccion = st.selectbox("Atleta", list(opciones.keys()), key="pdf_individual_select")
            atleta = db.obtener_atleta(opciones[seleccion])
            medicion = db.obtener_ultima_medicion(atleta["id"])
            if not medicion:
                st.warning("Este atleta no tiene mediciones cargadas.")
            else:
                st.caption(f"Se generará la ficha con la última medición: {medicion['fecha_medicion']}")
                df_hist_atleta = db.listar_mediciones_atleta(atleta["id"])
                medicion_anterior = df_hist_atleta.iloc[-2].to_dict() if len(df_hist_atleta) >= 2 else None
                pdf_bytes = pdfgen.generar_pdf_ficha_individual(atleta, medicion, medicion_anterior)
                st.download_button(
                    "⬇️ Descargar Ficha PDF", data=pdf_bytes,
                    file_name=f"ficha_{atleta['apellido']}_{atleta['nombre']}.pdf",
                    mime="application/pdf", use_container_width=True,
                )

    # --- Historial individual (Excel / PDF) ---
    with tab2:
        df_atletas = db.listar_atletas()
        if df_atletas.empty:
            st.info("No hay atletas cargados.")
        else:
            opciones = {f"{r['apellido']}, {r['nombre']} ({r['nombre_grupo']})": r["id"] for _, r in df_atletas.iterrows()}
            seleccion = st.selectbox("Atleta", list(opciones.keys()), key="hist_individual_select")
            atleta = db.obtener_atleta(opciones[seleccion])
            df_hist = db.listar_mediciones_atleta(atleta["id"])
            if df_hist.empty:
                st.warning("Este atleta no tiene mediciones cargadas.")
            else:
                st.dataframe(df_hist, use_container_width=True, hide_index=True)
                c1, c2 = st.columns(2)
                excel_bytes = pdfgen.generar_excel_historial(atleta, df_hist)
                c1.download_button(
                    "⬇️ Descargar Excel", data=excel_bytes,
                    file_name=f"historial_{atleta['apellido']}_{atleta['nombre']}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
                pdf_bytes = pdfgen.generar_pdf_historial(atleta, df_hist)
                c2.download_button(
                    "⬇️ Descargar PDF", data=pdf_bytes,
                    file_name=f"historial_{atleta['apellido']}_{atleta['nombre']}.pdf",
                    mime="application/pdf", use_container_width=True,
                )

    # --- Estadística poblacional por grupo ---
    with tab3:
        grupos_dict = db.obtener_grupos_dict()
        if not grupos_dict:
            st.info("No hay grupos creados.")
        else:
            grupo_nombre = st.selectbox("Grupo", list(grupos_dict.keys()), key="grupo_stats_select")
            grupo_id = grupos_dict[grupo_nombre]
            stats = db.estadisticas_grupo(grupo_id)
            df_detalle = db.detalle_grupo_ultimas_mediciones(grupo_id)

            if not stats or not stats.get("cantidad_atletas"):
                st.info("Este grupo todavía no tiene mediciones cargadas.")
            else:
                def _r(v):
                    return round(v, 2) if v is not None and pd.notna(v) else "-"

                st.subheader(f"Promedios del grupo: {grupo_nombre}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Atletas con medición", int(stats["cantidad_atletas"]))
                c2.metric("IMC promedio", _r(stats["imc_prom"]))
                c3.metric("% Grasa corporal promedio", _r(stats["grasa_prom"]))
                c4.metric("% Músculo esquelético promedio", _r(stats["musculo_prom"]))
                c5, c6, c7 = st.columns(3)
                c5.metric("% Grasa visceral promedio", _r(stats["grasa_visceral_prom"]))
                c6.metric("Índice cintura/cadera promedio", _r(stats["icc_prom"]))
                c7.metric("Índice cintura/talla promedio", _r(stats["ict_prom"]))

                if pd.notna(stats.get("endomorfia_prom")):
                    st.caption("Promedios ISAK (solo atletas con somatotipo cargado)")
                    d1, d2, d3 = st.columns(3)
                    d1.metric("Endomorfia grupal", _r(stats["endomorfia_prom"]))
                    d2.metric("Mesomorfia grupal", _r(stats["mesomorfia_prom"]))
                    d3.metric("Ectomorfia grupal", _r(stats["ectomorfia_prom"]))
                    puntos = [{
                        "x": stats["x_prom"], "y": stats["y_prom"], "fecha": "Promedio grupal",
                        "endomorfia": _r(stats["endomorfia_prom"]),
                        "mesomorfia": _r(stats["mesomorfia_prom"]),
                        "ectomorfia": _r(stats["ectomorfia_prom"]),
                    }]
                    st.plotly_chart(som.crear_grafico_somatocarta(puntos, titulo=f"Somatotipo grupal - {grupo_nombre}"), use_container_width=True)

                st.subheader("Detalle por atleta (última medición)")
                st.dataframe(df_detalle, use_container_width=True, hide_index=True)

                excel_bytes = pdfgen.generar_excel_grupal(grupo_nombre, df_detalle, stats)
                st.download_button(
                    "⬇️ Descargar Excel del grupo", data=excel_bytes,
                    file_name=f"estadistica_{grupo_nombre}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if "auth_user" not in st.session_state:
        branding.render_header()
        st.write("Iniciá sesión desde la barra lateral para continuar.")
        login()
        return

    db.init_db()

    with st.sidebar:
        branding.render_header(compact=True)
    st.sidebar.caption(f"Sesión: **{st.session_state['auth_user']}**")
    logout()
    st.sidebar.divider()

    branding.render_header()

    pagina = st.sidebar.radio(
        "Navegación",
        ["🏠 Dashboard", "👥 Gestión de Grupos", "📝 Cargar Medición", "📊 Perfil de Atleta", "📑 Exportar & Reportes"],
    )

    if pagina == "🏠 Dashboard":
        pagina_dashboard()
    elif pagina == "👥 Gestión de Grupos":
        pagina_grupos()
    elif pagina == "📝 Cargar Medición":
        pagina_cargar_medicion()
    elif pagina == "📊 Perfil de Atleta":
        pagina_perfil_atleta()
    elif pagina == "📑 Exportar & Reportes":
        pagina_exportar()


if __name__ == "__main__":
    main()
