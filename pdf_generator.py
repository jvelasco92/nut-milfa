"""
Generación de reportes PDF (ReportLab) y Excel (Pandas/OpenPyXL).
"""
from __future__ import annotations

import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)

import branding

PRIMARY_COLOR = colors.HexColor(branding.COLOR_PRIMARY)
PRIMARY_DARK = colors.HexColor(branding.COLOR_PRIMARY_DARK)
ACCENT_BRAND = colors.HexColor(branding.COLOR_ACCENT)
ACCENT_COLOR = colors.HexColor("#eaf3ee")
MUTED_COLOR = colors.HexColor(branding.COLOR_TEXT_MUTED)


def _dibujar_encabezado(canvas_obj, doc):
    """Header de marca (logo + nombre + nutricionistas) repetido en cada página."""
    canvas_obj.saveState()
    width, height = A4
    y = height - 1.35 * cm

    r = 0.5 * cm
    cx = 1.9 * cm
    canvas_obj.setFillColor(PRIMARY_COLOR)
    canvas_obj.circle(cx, y, r, stroke=0, fill=1)

    canvas_obj.saveState()
    canvas_obj.translate(cx, y)
    canvas_obj.rotate(20)
    canvas_obj.setFillColor(ACCENT_BRAND)
    canvas_obj.ellipse(-r * 0.55, -r * 0.85, r * 0.55, r * 0.85, stroke=0, fill=1)
    canvas_obj.restoreState()

    canvas_obj.setFillColor(PRIMARY_DARK)
    canvas_obj.setFont("Helvetica-Bold", 15)
    canvas_obj.drawString(2.7 * cm, y + 0.12 * cm, branding.NOMBRE_APP)

    canvas_obj.setFillColor(ACCENT_BRAND)
    canvas_obj.setFont("Helvetica-Bold", 7)
    canvas_obj.drawString(2.7 * cm, y - 0.32 * cm, branding.TAGLINE)

    canvas_obj.setFillColor(MUTED_COLOR)
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.drawRightString(width - 1.5 * cm, y + 0.05 * cm, branding.NUTRICIONISTAS)

    canvas_obj.setStrokeColor(colors.HexColor("#e4e9ea"))
    canvas_obj.setLineWidth(0.8)
    canvas_obj.line(1.5 * cm, height - 2.05 * cm, width - 1.5 * cm, height - 2.05 * cm)

    canvas_obj.restoreState()


# ---------------------------------------------------------------------------
# Gráficos auxiliares (matplotlib) para embeber en el PDF
# ---------------------------------------------------------------------------
def _grafico_somatocarta_png(puntos: list[tuple[float, float]]) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.axhline(0, color="lightgray", linewidth=1)
    ax.axvline(0, color="lightgray", linewidth=1)
    ax.set_xlim(-9, 9)
    ax.set_ylim(-6, 12)
    ax.text(-8, -5.3, "ENDOMORFIA", fontsize=8, color="#c0392b")
    ax.text(6.2, -5.3, "ECTOMORFIA", fontsize=8, color="#2980b9")
    ax.text(-1.5, 11.2, "MESOMORFIA", fontsize=8, color="#27ae60")

    if puntos:
        xs = [p[0] for p in puntos]
        ys = [p[1] for p in puntos]
        if len(puntos) > 1:
            ax.plot(xs, ys, "--", color="gray", linewidth=1)
        ax.scatter(xs, ys, s=80, color=branding.COLOR_PRIMARY, edgecolor="black", zorder=5)
        for i, (x, y) in enumerate(zip(xs, ys), start=1):
            ax.annotate(str(i), (x, y), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=8)

    ax.set_xlabel("X (Ecto - Endo)")
    ax.set_ylabel("Y (2·Meso - (Endo+Ecto))")
    ax.set_title("Somatocarta")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf


def _grafico_evolucion_png(df: pd.DataFrame) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(6, 3.2))
    ax.plot(df["fecha_medicion"], df["peso"], marker="o", label="Peso (kg)")
    ax2 = ax.twinx()
    ax2.plot(df["fecha_medicion"], df["porcentaje_grasa"], marker="s", color="#c0392b", label="% Grasa")
    ax2.plot(df["fecha_medicion"], df["porcentaje_musculo"], marker="^", color="#27ae60", label="% Músculo")

    ax.set_ylabel("Peso (kg)")
    ax2.set_ylabel("%")
    ax.set_xlabel("Fecha de medición")
    fig.autofmt_xdate(rotation=30)

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Estilos comunes
# ---------------------------------------------------------------------------
def _base_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TituloApp", fontSize=18, textColor=PRIMARY_COLOR, spaceAfter=4, leading=22))
    styles.add(ParagraphStyle(name="Subtitulo", fontSize=11, textColor=colors.grey, spaceAfter=12))
    styles.add(ParagraphStyle(name="Seccion", fontSize=13, textColor=PRIMARY_COLOR, spaceBefore=14, spaceAfter=6))
    return styles


def _tabla_datos(pairs: list[tuple[str, str]], col_widths=(6 * cm, 6 * cm)) -> Table:
    data = [[k, v] for k, v in pairs]
    t = Table(data, colWidths=list(col_widths))
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), ACCENT_COLOR),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def _fmt(v, suf=""):
    if v is None or v == "" or (isinstance(v, float) and pd.isna(v)):
        return "-"
    return f"{v}{suf}"


# ---------------------------------------------------------------------------
# PDF: Ficha individual
# ---------------------------------------------------------------------------
def generar_pdf_ficha_individual(atleta: dict, medicion: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2.6 * cm, bottomMargin=1.5 * cm)
    styles = _base_styles()
    story = []

    story.append(Paragraph("Ficha Antropométrica Individual", styles["TituloApp"]))
    story.append(
        Paragraph(
            f"{atleta['nombre']} {atleta['apellido']} — Grupo: {atleta.get('nombre_grupo', '-')}",
            styles["Subtitulo"],
        )
    )

    story.append(_tabla_datos([
        ("Sexo", _fmt(atleta.get("sexo"))),
        ("Edad", _fmt(atleta.get("edad"), " años")),
        ("Email", _fmt(atleta.get("email"))),
        ("Fecha de medición", _fmt(medicion.get("fecha_medicion"))),
        ("Fecha y hora de carga", _fmt(medicion.get("fecha_hora_carga"))),
        ("Cargado por", _fmt(medicion.get("cargado_por"))),
    ]))

    story.append(Paragraph("Datos Básicos", styles["Seccion"]))
    story.append(_tabla_datos([
        ("Peso (kg)", _fmt(medicion.get("peso"))),
        ("Altura (cm)", _fmt(medicion.get("altura"))),
        ("Talla sentado (cm)", _fmt(medicion.get("talla_sentado"))),
        ("IMC", _fmt(medicion.get("imc"))),
    ]))

    story.append(Paragraph("Perímetros (cm)", styles["Seccion"]))
    story.append(_tabla_datos([
        ("Brazo relajado", _fmt(medicion.get("brazo_relajado"))),
        ("Brazo contraído", _fmt(medicion.get("brazo_contraido"))),
        ("Cintura", _fmt(medicion.get("cintura"))),
        ("Cadera", _fmt(medicion.get("cadera"))),
        ("Muslo medio", _fmt(medicion.get("perimetro_muslo_medio"))),
        ("Pantorrilla", _fmt(medicion.get("perimetro_pantorrilla"))),
    ]))

    story.append(Paragraph("Pliegues Cutáneos (mm)", styles["Seccion"]))
    story.append(_tabla_datos([
        ("Tricipital", _fmt(medicion.get("pliegue_tricipital"))),
        ("Subescapular", _fmt(medicion.get("pliegue_subescapular"))),
        ("Suprailíaco", _fmt(medicion.get("pliegue_suprailiaco"))),
        ("Abdominal", _fmt(medicion.get("pliegue_abdominal"))),
        ("Muslo medio", _fmt(medicion.get("pliegue_muslo_medio"))),
        ("Pantorrilla", _fmt(medicion.get("pliegue_pantorrilla"))),
        ("Sumatoria 6 pliegues", _fmt(medicion.get("sumatoria_6_pliegues"), " mm")),
    ]))

    story.append(Paragraph("Composición Corporal y Somatotipo", styles["Seccion"]))
    story.append(_tabla_datos([
        ("% Grasa (Yuhasz)", _fmt(medicion.get("porcentaje_grasa"), " %")),
        ("% Músculo (Martin)", _fmt(medicion.get("porcentaje_musculo"), " %")),
        ("Endomorfia", _fmt(medicion.get("endomorfia"))),
        ("Mesomorfia", _fmt(medicion.get("mesomorfia"))),
        ("Ectomorfia", _fmt(medicion.get("ectomorfia"))),
        ("Coordenadas (X, Y)", f"({_fmt(medicion.get('coord_x'))}, {_fmt(medicion.get('coord_y'))})"),
    ]))

    datos_bio = [
        ("% Grasa corporal", _fmt(medicion.get("bio_grasa_corporal"), " %")),
        ("% Agua corporal", _fmt(medicion.get("bio_agua_corporal"), " %")),
        ("Masa muscular", _fmt(medicion.get("bio_masa_muscular"), " kg")),
        ("Masa ósea", _fmt(medicion.get("bio_masa_osea"), " kg")),
        ("Grasa visceral (nivel)", _fmt(medicion.get("bio_grasa_visceral"))),
        ("Metabolismo basal", _fmt(medicion.get("bio_metabolismo_basal"), " kcal")),
        ("Edad metabólica", _fmt(medicion.get("bio_edad_metabolica"), " años")),
    ]
    if any(v != "-" for _, v in datos_bio):
        story.append(Paragraph("Datos de Bioimpedancia", styles["Seccion"]))
        story.append(_tabla_datos(datos_bio))

    x, y = medicion.get("coord_x"), medicion.get("coord_y")
    if x is not None and y is not None:
        img_buf = _grafico_somatocarta_png([(x, y)])
        story.append(Spacer(1, 10))
        story.append(Image(img_buf, width=11 * cm, height=8.8 * cm))

    story.append(Paragraph("Observaciones / Valoración Clínica", styles["Seccion"]))
    obs = medicion.get("observaciones") or "Sin observaciones registradas."
    story.append(Paragraph(obs, styles["Normal"]))

    doc.build(story, onFirstPage=_dibujar_encabezado, onLaterPages=_dibujar_encabezado)
    buffer.seek(0)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# PDF: Historial
# ---------------------------------------------------------------------------
def generar_pdf_historial(atleta: dict, df_historial: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2.6 * cm, bottomMargin=1.5 * cm)
    styles = _base_styles()
    story = []

    story.append(Paragraph("Historial Antropométrico", styles["TituloApp"]))
    story.append(
        Paragraph(
            f"{atleta['nombre']} {atleta['apellido']} — Grupo: {atleta.get('nombre_grupo', '-')}",
            styles["Subtitulo"],
        )
    )

    cols = ["fecha_medicion", "peso", "imc", "porcentaje_grasa", "porcentaje_musculo", "sumatoria_6_pliegues"]
    headers = ["Fecha", "Peso", "IMC", "% Grasa", "% Músculo", "Σ6 Pliegues"]
    data = [headers] + df_historial[cols].astype(str).values.tolist()
    t = Table(data, colWidths=[3 * cm] + [2.6 * cm] * 5)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ACCENT_COLOR]),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    story.append(t)

    if len(df_historial) >= 2:
        story.append(Paragraph("Evolución Temporal", styles["Seccion"]))
        story.append(Image(_grafico_evolucion_png(df_historial), width=15 * cm, height=8 * cm))

    puntos = list(zip(df_historial["coord_x"].dropna(), df_historial["coord_y"].dropna()))
    if puntos:
        story.append(Paragraph("Somatocarta - Evolución", styles["Seccion"]))
        story.append(Image(_grafico_somatocarta_png(puntos), width=11 * cm, height=8.8 * cm))

    doc.build(story, onFirstPage=_dibujar_encabezado, onLaterPages=_dibujar_encabezado)
    buffer.seek(0)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------
def generar_excel_historial(atleta: dict, df_historial: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_historial.to_excel(writer, index=False, sheet_name="Historial")
        info = pd.DataFrame(
            [{"Nombre": atleta["nombre"], "Apellido": atleta["apellido"],
              "Sexo": atleta.get("sexo"), "Edad": atleta.get("edad"),
              "Grupo": atleta.get("nombre_grupo")}]
        )
        info.to_excel(writer, index=False, sheet_name="Atleta")
    buffer.seek(0)
    return buffer.getvalue()


def generar_excel_grupal(nombre_grupo: str, df_detalle: pd.DataFrame, estadisticas: dict) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_detalle.to_excel(writer, index=False, sheet_name="Detalle")
        pd.DataFrame([estadisticas]).to_excel(writer, index=False, sheet_name="Promedios")
    buffer.seek(0)
    return buffer.getvalue()
