"""
Cálculos antropométricos: IMC, composición corporal y somatotipo de Heath-Carter.

Referencias:
- % Grasa: ecuación de Yuhasz (sumatoria de 6 pliegues).
- % Músculo: fórmula de Martin (1990) con perímetros corregidos por pliegue.
- Somatotipo: método de Heath-Carter (Carter & Heath, 1990).
"""
from __future__ import annotations

import math

import plotly.graph_objects as go


# ---------------------------------------------------------------------------
# Índices básicos
# ---------------------------------------------------------------------------
def calcular_imc(peso: float, altura_cm: float) -> float:
    if not peso or not altura_cm:
        return 0.0
    altura_m = altura_cm / 100.0
    return round(peso / (altura_m ** 2), 2)


def calcular_sumatoria_6_pliegues(tricipital, subescapular, suprailiaco, abdominal, muslo_medio, pantorrilla) -> float:
    valores = [tricipital, subescapular, suprailiaco, abdominal, muslo_medio, pantorrilla]
    valores = [v for v in valores if v]
    return round(sum(valores), 2) if valores else 0.0


def calcular_porcentaje_grasa_yuhasz(sumatoria_6: float, sexo: str) -> float:
    """Ecuación de Yuhasz sobre la sumatoria de 6 pliegues (tríceps, subescapular,
    suprailíaco, abdominal, muslo medio y pantorrilla)."""
    if not sumatoria_6:
        return 0.0
    if sexo == "Femenino":
        pct = sumatoria_6 * 0.1548 + 3.580
    else:
        pct = sumatoria_6 * 0.1051 + 2.585
    return round(pct, 2)


def calcular_porcentaje_musculo_martin(
    peso: float,
    altura_cm: float,
    brazo_relajado: float,
    pliegue_tricipital: float,
    perimetro_muslo: float,
    pliegue_muslo: float,
    perimetro_pantorrilla: float,
    pliegue_pantorrilla: float,
) -> float:
    """Fórmula de Martin (1990) para masa muscular total a partir de perímetros
    corregidos de brazo, muslo y pantorrilla. Devuelve el % respecto del peso."""
    if not all([peso, altura_cm, brazo_relajado, perimetro_muslo, perimetro_pantorrilla]):
        return 0.0

    def corregido(perimetro_cm, pliegue_mm):
        return perimetro_cm - (math.pi * (pliegue_mm or 0) / 10.0)

    amb_c = corregido(brazo_relajado, pliegue_tricipital)
    amu_c = corregido(perimetro_muslo, pliegue_muslo)
    amp_c = corregido(perimetro_pantorrilla, pliegue_pantorrilla)

    masa_muscular_g = altura_cm * (
        0.0553 * amb_c ** 2 + 0.0987 * amu_c ** 2 + 0.0331 * amp_c ** 2
    ) - 2445
    masa_muscular_kg = max(masa_muscular_g / 1000.0, 0.0)

    return round((masa_muscular_kg / peso) * 100, 2)


# ---------------------------------------------------------------------------
# Somatotipo de Heath-Carter
# ---------------------------------------------------------------------------
def calcular_endomorfia(pliegue_tricipital, pliegue_subescapular, pliegue_suprailiaco, altura_cm) -> float:
    if not altura_cm:
        return 0.0
    suma = (pliegue_tricipital or 0) + (pliegue_subescapular or 0) + (pliegue_suprailiaco or 0)
    x = suma * (170.18 / altura_cm)
    endo = -0.7182 + 0.1451 * x - 0.00068 * x ** 2 + 0.0000014 * x ** 3
    return round(endo, 2)


def calcular_mesomorfia(
    altura_cm: float,
    diam_humero: float,
    diam_femur: float,
    perimetro_brazo_contraido: float,
    pliegue_tricipital: float,
    perimetro_pantorrilla: float,
    pliegue_pantorrilla: float,
) -> float:
    if not all([altura_cm, diam_humero, diam_femur, perimetro_brazo_contraido, perimetro_pantorrilla]):
        return 0.0

    brazo_corregido = perimetro_brazo_contraido - ((pliegue_tricipital or 0) / 10.0)
    pantorrilla_corregida = perimetro_pantorrilla - ((pliegue_pantorrilla or 0) / 10.0)

    meso = (
        (0.858 * diam_humero)
        + (0.601 * diam_femur)
        + (0.188 * brazo_corregido)
        + (0.161 * pantorrilla_corregida)
        - (0.131 * altura_cm)
        + 4.5
    )
    return round(meso, 2)


def calcular_ectomorfia(altura_cm: float, peso: float) -> float:
    if not altura_cm or not peso:
        return 0.0
    hwr = altura_cm / (peso ** (1 / 3))
    if hwr >= 40.75:
        ecto = 0.732 * hwr - 28.58
    elif hwr >= 38.25:
        ecto = 0.463 * hwr - 17.63
    else:
        ecto = 0.1
    return round(max(ecto, 0.1), 2)


def calcular_somatotipo(
    peso: float,
    altura_cm: float,
    pliegue_tricipital: float,
    pliegue_subescapular: float,
    pliegue_suprailiaco: float,
    perimetro_brazo_contraido: float,
    perimetro_pantorrilla: float,
    pliegue_pantorrilla: float,
    diam_humero: float = None,
    diam_femur: float = None,
) -> dict:
    endo = calcular_endomorfia(pliegue_tricipital, pliegue_subescapular, pliegue_suprailiaco, altura_cm)
    meso = calcular_mesomorfia(
        altura_cm, diam_humero, diam_femur, perimetro_brazo_contraido, pliegue_tricipital,
        perimetro_pantorrilla, pliegue_pantorrilla,
    )
    ecto = calcular_ectomorfia(altura_cm, peso)

    x = round(ecto - endo, 2)
    y = round((2 * meso) - (endo + ecto), 2)

    return {
        "endomorfia": endo,
        "mesomorfia": meso,
        "ectomorfia": ecto,
        "coord_x": x,
        "coord_y": y,
    }


# ---------------------------------------------------------------------------
# Somatocarta (gráfico interactivo Plotly)
# ---------------------------------------------------------------------------
def crear_grafico_somatocarta(puntos: list[dict], titulo: str = "Somatocarta") -> go.Figure:
    """puntos: lista de dicts con keys x, y, fecha (str), endomorfia, mesomorfia, ectomorfia."""
    fig = go.Figure()

    # Líneas guía de referencia (ejes y triángulo de zonas aproximado)
    fig.add_shape(type="line", x0=-9, y0=0, x1=9, y1=0, line=dict(color="lightgray", width=1))
    fig.add_shape(type="line", x0=0, y0=-6, x1=0, y1=12, line=dict(color="lightgray", width=1))

    fig.add_annotation(x=-8, y=-5.3, text="ENDOMORFIA", showarrow=False, font=dict(size=10, color="#c0392b"))
    fig.add_annotation(x=8, y=-5.3, text="ECTOMORFIA", showarrow=False, font=dict(size=10, color="#2980b9"))
    fig.add_annotation(x=0, y=11.3, text="MESOMORFIA", showarrow=False, font=dict(size=10, color="#27ae60"))

    if puntos:
        xs = [p["x"] for p in puntos]
        ys = [p["y"] for p in puntos]
        fechas = [p.get("fecha", "") for p in puntos]
        texto = [
            f"Fecha: {p.get('fecha','')}<br>Endo: {p['endomorfia']} / Meso: {p['mesomorfia']} / Ecto: {p['ectomorfia']}"
            for p in puntos
        ]

        if len(puntos) > 1:
            fig.add_trace(
                go.Scatter(
                    x=xs, y=ys, mode="lines", line=dict(color="#7f8c8d", width=1, dash="dot"),
                    showlegend=False, hoverinfo="skip",
                )
            )

        fig.add_trace(
            go.Scatter(
                x=xs, y=ys, mode="markers+text",
                marker=dict(size=14, color=list(range(len(xs))), colorscale="Blues", showscale=False,
                            line=dict(width=1, color="#2c3e50")),
                text=[str(i + 1) for i in range(len(xs))],
                textposition="top center",
                hovertext=texto, hoverinfo="text",
                name="Mediciones",
            )
        )

    fig.update_layout(
        title=titulo,
        xaxis=dict(title="X (Ecto - Endo)", range=[-9, 9], zeroline=False),
        yaxis=dict(title="Y (2·Meso - (Endo+Ecto))", range=[-6, 12], zeroline=False),
        height=500,
        plot_bgcolor="white",
    )
    return fig
