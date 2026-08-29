"""
Identidad visual de la app: colores de marca, logo (SVG inline) y encabezado.

El logo es un ícono vectorial simple (círculo + hoja) para que se vea nítido
en cualquier resolución, sin depender de archivos de imagen externos.
"""
import streamlit as st

COLOR_PRIMARY = "#1f6f78"       # Teal — salud / nutrición
COLOR_PRIMARY_DARK = "#154f56"
COLOR_ACCENT = "#8bc34a"        # Verde lima — energía / deporte
COLOR_TEXT_MUTED = "#5a6b70"
COLOR_RING = "#bcdad0"

NOMBRE_APP = "Nut-Milfa"
TAGLINE = "NUTRICIÓN DEPORTIVA"
NUTRICIONISTAS = "Lic. María Sol Mileo  ·  Lic. Lucila Fassano"

_LOGO_SVG = """<svg width="{size}" height="{size}" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg">
  <circle cx="30" cy="30" r="29" fill="none" stroke="{ring}" stroke-width="1.5"/>
  <circle cx="30" cy="30" r="26" fill="{primary}"/>
  <path d="M30 12 C43 18, 43 42, 30 49 C17 42, 17 18, 30 12 Z" fill="{accent}"/>
  <line x1="30" y1="15" x2="30" y2="46" stroke="#ffffff" stroke-width="1.4" opacity="0.85"/>
</svg>"""


def logo_svg(size: int = 60) -> str:
    return _LOGO_SVG.format(size=size, primary=COLOR_PRIMARY, accent=COLOR_ACCENT, ring=COLOR_RING)


def render_header(compact: bool = False) -> None:
    """Banner con logo + nombre de marca. `compact=True` para la barra lateral."""
    icon_size = 38 if compact else 60
    titulo_size = "1.05rem" if compact else "1.7rem"
    padding = "8px 12px" if compact else "16px 20px"
    margin_bottom = "10px" if compact else "18px"
    mostrar_tagline = "" if not compact else "display:none;"
    mostrar_nutris = "" if not compact else "display:none;"

    html = f"""
    <div style="display:flex;align-items:center;gap:14px;background:#ffffff;
                border:1px solid #e4e9ea;border-radius:12px;padding:{padding};
                margin-bottom:{margin_bottom};">
        {logo_svg(icon_size)}
        <div>
            <div style="font-size:{titulo_size};font-weight:700;color:{COLOR_PRIMARY_DARK};
                        line-height:1.15;font-family:'Source Sans Pro',sans-serif;">
                {NOMBRE_APP}
            </div>
            <div style="{mostrar_tagline}font-size:0.72rem;letter-spacing:1.5px;
                        color:{COLOR_ACCENT};font-weight:700;margin-top:2px;">
                {TAGLINE}
            </div>
            <div style="{mostrar_nutris}font-size:0.78rem;color:{COLOR_TEXT_MUTED};margin-top:4px;">
                {NUTRICIONISTAS}
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
