"""
Cálculos antropométricos: IMC, composición corporal y somatotipo de Heath-Carter.

Referencias:
- % Grasa: ecuación de Yuhasz (sumatoria de 6 pliegues).
- % Músculo: fórmula de Martin (1990) con perímetros corregidos por pliegue.
- Somatotipo: método de Heath-Carter (Carter & Heath, 1990).
"""
from __future__ import annotations

import math
from datetime import date

import plotly.graph_objects as go


# ---------------------------------------------------------------------------
# Índices básicos
# ---------------------------------------------------------------------------
def calcular_edad(fecha_nacimiento: date, fecha_referencia: date = None) -> int:
    if not fecha_nacimiento:
        return 0
    hoy = fecha_referencia or date.today()
    edad = hoy.year - fecha_nacimiento.year
    if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        edad -= 1
    return edad


def calcular_imc(peso: float, altura_cm: float) -> float:
    if not peso or not altura_cm:
        return 0.0
    altura_m = altura_cm / 100.0
    return round(peso / (altura_m ** 2), 2)


def calcular_indice_cintura_cadera(cintura: float, cadera: float) -> float:
    if not cintura or not cadera:
        return 0.0
    return round(cintura / cadera, 2)


def calcular_indice_cintura_talla(cintura: float, altura_cm: float) -> float:
    if not cintura or not altura_cm:
        return 0.0
    return round(cintura / altura_cm, 2)


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
# Semáforo de referencias (colores y umbrales tomados de "inputs/puntos de
# corte.xlsx"): IMC (OMS 1997/2000); % músculo esquelético y grasa visceral
# (OMRON HBF-514C); % grasa corporal (Gallagher et al. 2000); circunferencia
# de cintura e índice cintura/cadera (OMS 2011); índice cintura/talla.
# % músculo esquelético y % grasa corporal distinguen, además del sexo, la
# franja etaria (25-39, 40-59, 60-65 años); fuera de esas franjas no hay
# referencia cargada y se muestran sin clasificar.
# ---------------------------------------------------------------------------
COLOR_VERDE = "#2e7d32"
COLOR_AMARILLO = "#f2c400"
COLOR_NARANJA = "#e07b00"
COLOR_ROJO = "#d32f2f"
COLOR_CIAN = "#00acc1"
COLOR_AZUL = "#4a86e8"
COLOR_SIN_DATO = "#9aa5a9"

# Franjas etarias con referencia cargada para % músculo esquelético y % grasa corporal.
BANDAS_EDAD = [(25, 39), (40, 59), (60, 65)]

# Cada regla: (mínimo_inclusivo_o_None, máximo_exclusivo_o_None, etiqueta, color)

# Métricas sin distinción por sexo ni edad.
_REFERENCIAS_UNISEX = {
    "imc": [
        (None, 18.5, "BAJO PESO", COLOR_AMARILLO),
        (18.5, 25.0, "SALUDABLE", COLOR_VERDE),
        (25.0, 30.0, "SOBREPESO", COLOR_NARANJA),
        (30.0, None, "OBESIDAD", COLOR_ROJO),
    ],
    "grasa_visceral": [
        (None, 10, "NORMAL", COLOR_VERDE),
        (10, 15, "ALTO", COLOR_NARANJA),
        (15, None, "MUY ALTO", COLOR_ROJO),
    ],
    "pliegue_abdominal": [
        (None, 12, "FAVORABLE", COLOR_VERDE),
        (12, None, "ELEVADO", COLOR_ROJO),
    ],
    "indice_cintura_talla": [
        (None, 0.50, "SIN RIESGO", COLOR_VERDE),
        (0.50, None, "RIESGO AUMENTADO", COLOR_ROJO),
    ],
}

# Métricas con distinción por sexo, sin franja etaria.
_REFERENCIAS_SEXO = {
    "circ_cintura": {
        "Femenino": [
            (None, 80, "RIESGO NORMAL", COLOR_VERDE),
            (80, 88, "RIESGO AUMENTADO", COLOR_AMARILLO),
            (88, None, "RIESGO SUST. AUMENTADO", COLOR_ROJO),
        ],
        "Masculino": [
            (None, 94, "RIESGO NORMAL", COLOR_VERDE),
            (94, 102, "RIESGO AUMENTADO", COLOR_AMARILLO),
            (102, None, "RIESGO SUST. AUMENTADO", COLOR_ROJO),
        ],
    },
    "indice_cintura_cadera": {
        "Femenino": [
            (None, 0.85, "BAJO RIESGO", COLOR_VERDE),
            (0.85, None, "RIESGO AUMENTADO", COLOR_ROJO),
        ],
        "Masculino": [
            (None, 0.90, "BAJO RIESGO", COLOR_VERDE),
            (0.90, None, "RIESGO AUMENTADO", COLOR_ROJO),
        ],
    },
}

# Métricas con distinción por sexo y franja etaria.
_REFERENCIAS_EDAD_SEXO = {
    "musculo_esqueletico_pct": {
        (25, 39): {
            "Femenino": [
                (None, 24.3, "BAJO", COLOR_ROJO),
                (24.3, 30.4, "NORMAL", COLOR_VERDE),
                (30.4, 35.4, "ALTO", COLOR_CIAN),
                (35.4, None, "MUY ALTO", COLOR_AZUL),
            ],
            "Masculino": [
                (None, 33.3, "BAJO", COLOR_ROJO),
                (33.3, 39.4, "NORMAL", COLOR_VERDE),
                (39.4, 44.1, "ALTO", COLOR_CIAN),
                (44.1, None, "MUY ALTO", COLOR_AZUL),
            ],
        },
        (40, 59): {
            "Femenino": [
                (None, 24.1, "BAJO", COLOR_ROJO),
                (24.1, 30.2, "NORMAL", COLOR_VERDE),
                (30.2, 35.2, "ALTO", COLOR_CIAN),
                (35.2, None, "MUY ALTO", COLOR_AZUL),
            ],
            "Masculino": [
                (None, 33.1, "BAJO", COLOR_ROJO),
                (33.1, 39.2, "NORMAL", COLOR_VERDE),
                (39.2, 43.9, "ALTO", COLOR_CIAN),
                (43.9, None, "MUY ALTO", COLOR_AZUL),
            ],
        },
        (60, 65): {
            "Femenino": [
                (None, 23.9, "BAJO", COLOR_ROJO),
                (23.9, 30.0, "NORMAL", COLOR_VERDE),
                (30.0, 35.0, "ALTO", COLOR_CIAN),
                (35.0, None, "MUY ALTO", COLOR_AZUL),
            ],
            "Masculino": [
                (None, 32.9, "BAJO", COLOR_ROJO),
                (32.9, 39.0, "NORMAL", COLOR_VERDE),
                (39.0, 43.7, "ALTO", COLOR_CIAN),
                (43.7, None, "MUY ALTO", COLOR_AZUL),
            ],
        },
    },
    "grasa_corporal_pct": {
        (25, 39): {
            "Femenino": [
                (None, 21.0, "BAJO", COLOR_AMARILLO),
                (21.0, 33.0, "NORMAL", COLOR_VERDE),
                (33.0, 39.0, "ALTO", COLOR_NARANJA),
                (39.0, None, "MUY ALTO", COLOR_ROJO),
            ],
            "Masculino": [
                (None, 8.0, "BAJO", COLOR_AMARILLO),
                (8.0, 20.0, "NORMAL", COLOR_VERDE),
                (20.0, 25.0, "ALTO", COLOR_NARANJA),
                (25.0, None, "MUY ALTO", COLOR_ROJO),
            ],
        },
        (40, 59): {
            "Femenino": [
                (None, 23.0, "BAJO", COLOR_AMARILLO),
                (23.0, 34.0, "NORMAL", COLOR_VERDE),
                (34.0, 40.0, "ALTO", COLOR_NARANJA),
                (40.0, None, "MUY ALTO", COLOR_ROJO),
            ],
            "Masculino": [
                (None, 11.0, "BAJO", COLOR_AMARILLO),
                (11.0, 22.0, "NORMAL", COLOR_VERDE),
                (22.0, 28.0, "ALTO", COLOR_NARANJA),
                (28.0, None, "MUY ALTO", COLOR_ROJO),
            ],
        },
        (60, 65): {
            "Femenino": [
                (None, 24.0, "BAJO", COLOR_AMARILLO),
                (24.0, 36.0, "NORMAL", COLOR_VERDE),
                (36.0, 42.0, "ALTO", COLOR_NARANJA),
                (42.0, None, "MUY ALTO", COLOR_ROJO),
            ],
            "Masculino": [
                (None, 13.0, "BAJO", COLOR_AMARILLO),
                (13.0, 25.0, "NORMAL", COLOR_VERDE),
                (25.0, 30.0, "ALTO", COLOR_NARANJA),
                (30.0, None, "MUY ALTO", COLOR_ROJO),
            ],
        },
    },
}


def _banda_edad(edad):
    if edad is None:
        return None
    for banda in BANDAS_EDAD:
        if banda[0] <= edad <= banda[1]:
            return banda
    return None


def _reglas_para(metrica: str, sexo: str = "Masculino", edad: int = None):
    """Reglas (mínimo, máximo, etiqueta, color) para metrica/sexo/edad, o None si no hay referencia cargada."""
    if metrica in _REFERENCIAS_UNISEX:
        return _REFERENCIAS_UNISEX[metrica]
    if metrica in _REFERENCIAS_SEXO:
        return _REFERENCIAS_SEXO[metrica].get(sexo)
    if metrica in _REFERENCIAS_EDAD_SEXO:
        banda = _banda_edad(edad)
        if banda is None:
            return None
        return _REFERENCIAS_EDAD_SEXO[metrica][banda].get(sexo)
    return None


def reglas_referencia(metrica: str, sexo: str = "Masculino", edad: int = None) -> list[tuple]:
    """Lista de reglas (mínimo, máximo, etiqueta, color) usada para clasificar
    esa métrica (útil para armar leyendas)."""
    return _reglas_para(metrica, sexo, edad) or []


def clasificar_metrica(metrica: str, valor: float, sexo: str = "Masculino", edad: int = None) -> tuple[str, str]:
    """Devuelve (etiqueta, color_hex) para un valor según las referencias de
    'puntos de corte.xlsx'. Si no hay valor cargado, o no hay referencia para
    ese sexo/edad, devuelve ("Sin dato"/"Sin referencia", color gris)."""
    if valor is None or valor == 0:
        return "Sin dato", COLOR_SIN_DATO

    reglas = _reglas_para(metrica, sexo, edad)
    if not reglas:
        return "Sin referencia", COLOR_SIN_DATO

    for minimo, maximo, etiqueta, color in reglas:
        if minimo is not None and valor < minimo:
            continue
        if maximo is not None and valor >= maximo:
            continue
        return etiqueta, color

    ultimo = reglas[-1]
    return ultimo[2], ultimo[3]


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
