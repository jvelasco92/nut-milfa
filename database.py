"""
Capa de acceso a datos para la app de Nutrición Deportiva.

Usa SQLAlchemy sobre PostgreSQL (Supabase). La cadena de conexión se lee
de st.secrets["DATABASE_URL"].
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, date

import pandas as pd
import streamlit as st
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    Date,
    ForeignKey,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

import utils_somatotype as som

Base = declarative_base()


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------
class Grupo(Base):
    __tablename__ = "grupos"

    id = Column(Integer, primary_key=True)
    nombre_grupo = Column(String(150), nullable=False, unique=True)
    descripcion = Column(Text)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    atletas = relationship("Atleta", back_populates="grupo", cascade="all, delete-orphan")


class Atleta(Base):
    __tablename__ = "atletas"

    id = Column(Integer, primary_key=True)
    grupo_id = Column(Integer, ForeignKey("grupos.id", ondelete="SET NULL"))
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    sexo = Column(String(20), nullable=False, default="Masculino")
    fecha_nacimiento = Column(Date)
    edad = Column(Integer)  # se recalcula a partir de fecha_nacimiento en cada carga
    email = Column(String(150))
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    grupo = relationship("Grupo", back_populates="atletas")
    mediciones = relationship("Medicion", back_populates="atleta", cascade="all, delete-orphan")


class Medicion(Base):
    __tablename__ = "mediciones"

    id = Column(Integer, primary_key=True)
    atleta_id = Column(Integer, ForeignKey("atletas.id", ondelete="CASCADE"), nullable=False)

    # Trazabilidad temporal
    fecha_hora_carga = Column(DateTime, default=datetime.utcnow, nullable=False)
    fecha_medicion = Column(Date, nullable=False)
    cargado_por = Column(String(100))

    # Datos básicos
    peso = Column(Float)
    altura = Column(Float)
    talla_sentado = Column(Float)

    # Perímetros (cm)
    brazo_relajado = Column(Float)
    brazo_contraido = Column(Float)
    cintura = Column(Float)
    cadera = Column(Float)
    perimetro_muslo_medio = Column(Float)
    perimetro_pantorrilla = Column(Float)

    # Pliegues cutáneos (mm)
    pliegue_tricipital = Column(Float)
    pliegue_subescapular = Column(Float)
    pliegue_suprailiaco = Column(Float)
    pliegue_abdominal = Column(Float)
    pliegue_muslo_medio = Column(Float)
    pliegue_pantorrilla = Column(Float)

    # Diámetros óseos (cm) - necesarios para la mesomorfia de Heath-Carter
    diam_humero = Column(Float)
    diam_femur = Column(Float)

    # Datos de balanza de bioimpedancia (opcionales, complementan los cálculos manuales)
    bio_grasa_corporal = Column(Float)      # % graso medido por la balanza
    bio_agua_corporal = Column(Float)       # % de agua corporal
    bio_masa_muscular = Column(Float)       # kg de masa muscular
    bio_masa_osea = Column(Float)           # kg de masa ósea
    bio_grasa_visceral = Column(Float)      # nivel de grasa visceral (escala del equipo, ej. 1-59)
    bio_metabolismo_basal = Column(Float)   # kcal/día
    bio_edad_metabolica = Column(Float)     # años

    # Resultados calculados
    imc = Column(Float)
    porcentaje_grasa = Column(Float)          # % graso calculado por pliegues (Yuhasz) - avanzado/ISAK
    porcentaje_musculo = Column(Float)        # % muscular calculado (Martin) - avanzado/ISAK
    sumatoria_6_pliegues = Column(Float)
    indice_cintura_cadera = Column(Float)
    indice_cintura_talla = Column(Float)
    pct_musculo_esqueletico = Column(Float)   # % músculo esquelético estimado por balanza (campo "core")

    # Somatotipo
    endomorfia = Column(Float)
    mesomorfia = Column(Float)
    ectomorfia = Column(Float)
    coord_x = Column(Float)
    coord_y = Column(Float)

    observaciones = Column(Text)

    atleta = relationship("Atleta", back_populates="mediciones")


# ---------------------------------------------------------------------------
# Conexión
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_engine():
    url = st.secrets["DATABASE_URL"]
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)


# Columnas agregadas después de la primera versión de las tablas.
# create_all() no altera tablas ya existentes, así que se agregan a mano
# (ADD COLUMN IF NOT EXISTS es idempotente: no rompe nada si ya existen).
_COLUMNAS_NUEVAS = {
    "mediciones": {
        "bio_grasa_corporal": "FLOAT",
        "bio_agua_corporal": "FLOAT",
        "bio_masa_muscular": "FLOAT",
        "bio_masa_osea": "FLOAT",
        "bio_grasa_visceral": "FLOAT",
        "bio_metabolismo_basal": "FLOAT",
        "bio_edad_metabolica": "FLOAT",
        "indice_cintura_cadera": "FLOAT",
        "indice_cintura_talla": "FLOAT",
        "pct_musculo_esqueletico": "FLOAT",
    },
    "atletas": {
        "fecha_nacimiento": "DATE",
    },
}


def _migrar_columnas_nuevas() -> None:
    with get_engine().begin() as conn:
        for tabla, columnas in _COLUMNAS_NUEVAS.items():
            for nombre, tipo in columnas.items():
                conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN IF NOT EXISTS {nombre} {tipo}"))


def init_db() -> None:
    """Crea las tablas si no existen y aplica migraciones simples de columnas nuevas."""
    Base.metadata.create_all(get_engine())
    _migrar_columnas_nuevas()


@contextmanager
def get_session():
    Session = sessionmaker(bind=get_engine(), expire_on_commit=False)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Grupos
# ---------------------------------------------------------------------------
def crear_grupo(nombre_grupo: str, descripcion: str = "") -> int:
    with get_session() as s:
        g = Grupo(nombre_grupo=nombre_grupo.strip(), descripcion=descripcion.strip())
        s.add(g)
        s.flush()
        grupo_id = g.id
    listar_grupos.clear()
    contar_grupos.clear()
    return grupo_id


def actualizar_grupo(grupo_id: int, nombre_grupo: str, descripcion: str) -> None:
    with get_session() as s:
        g = s.get(Grupo, grupo_id)
        if g:
            g.nombre_grupo = nombre_grupo.strip()
            g.descripcion = descripcion.strip()
    listar_grupos.clear()
    listar_atletas.clear()


def eliminar_grupo(grupo_id: int) -> None:
    with get_session() as s:
        g = s.get(Grupo, grupo_id)
        if g:
            s.delete(g)
    listar_grupos.clear()
    listar_atletas.clear()
    contar_grupos.clear()


@st.cache_data(ttl=30, show_spinner=False)
def listar_grupos() -> pd.DataFrame:
    query = text(
        """
        SELECT g.id, g.nombre_grupo, g.descripcion, g.fecha_creacion,
               COUNT(a.id) AS cantidad_atletas
        FROM grupos g
        LEFT JOIN atletas a ON a.grupo_id = g.id
        GROUP BY g.id, g.nombre_grupo, g.descripcion, g.fecha_creacion
        ORDER BY g.nombre_grupo
        """
    )
    return pd.read_sql_query(query, get_engine())


def obtener_grupos_dict() -> dict:
    df = listar_grupos()
    return {row["nombre_grupo"]: row["id"] for _, row in df.iterrows()}


# ---------------------------------------------------------------------------
# Atletas
# ---------------------------------------------------------------------------
def crear_atleta(grupo_id, nombre: str, apellido: str, sexo: str, fecha_nacimiento: date, email: str = "") -> int:
    with get_session() as s:
        a = Atleta(
            grupo_id=grupo_id,
            nombre=nombre.strip(),
            apellido=apellido.strip(),
            sexo=sexo,
            fecha_nacimiento=fecha_nacimiento,
            edad=som.calcular_edad(fecha_nacimiento),
            email=(email or "").strip(),
        )
        s.add(a)
        s.flush()
        atleta_id = a.id
    listar_atletas.clear()
    contar_atletas.clear()
    return atleta_id


def actualizar_atleta(atleta_id: int, grupo_id, nombre: str, apellido: str, sexo: str, fecha_nacimiento: date, email: str) -> None:
    with get_session() as s:
        a = s.get(Atleta, atleta_id)
        if a:
            a.grupo_id = grupo_id
            a.nombre = nombre.strip()
            a.apellido = apellido.strip()
            a.sexo = sexo
            a.fecha_nacimiento = fecha_nacimiento
            a.edad = som.calcular_edad(fecha_nacimiento)
            a.email = (email or "").strip()
    listar_atletas.clear()
    obtener_atleta.clear()


def eliminar_atleta(atleta_id: int) -> None:
    with get_session() as s:
        a = s.get(Atleta, atleta_id)
        if a:
            s.delete(a)
    listar_atletas.clear()
    obtener_atleta.clear()
    contar_atletas.clear()


@st.cache_data(ttl=30, show_spinner=False)
def listar_atletas(grupo_id=None, nombre_filtro: str = "", apellido_filtro: str = "") -> pd.DataFrame:
    sql = """
        SELECT a.id, a.nombre, a.apellido, a.sexo, a.edad, a.email,
               a.fecha_registro, a.grupo_id,
               COALESCE(g.nombre_grupo, 'Sin grupo') AS nombre_grupo
        FROM atletas a
        LEFT JOIN grupos g ON g.id = a.grupo_id
        WHERE 1=1
    """
    params = {}
    if grupo_id:
        sql += " AND a.grupo_id = :grupo_id"
        params["grupo_id"] = grupo_id
    if nombre_filtro:
        sql += " AND a.nombre ILIKE :nombre"
        params["nombre"] = f"%{nombre_filtro}%"
    if apellido_filtro:
        sql += " AND a.apellido ILIKE :apellido"
        params["apellido"] = f"%{apellido_filtro}%"
    sql += " ORDER BY a.apellido, a.nombre"
    return pd.read_sql_query(text(sql), get_engine(), params=params)


@st.cache_data(ttl=30, show_spinner=False)
def obtener_atleta(atleta_id: int) -> dict | None:
    df = pd.read_sql_query(
        text(
            """
            SELECT a.*, COALESCE(g.nombre_grupo, 'Sin grupo') AS nombre_grupo
            FROM atletas a LEFT JOIN grupos g ON g.id = a.grupo_id
            WHERE a.id = :id
            """
        ),
        get_engine(),
        params={"id": atleta_id},
    )
    if df.empty:
        return None
    return df.iloc[0].to_dict()


# ---------------------------------------------------------------------------
# Mediciones
# ---------------------------------------------------------------------------
def crear_medicion(data: dict) -> int:
    with get_session() as s:
        m = Medicion(**data)
        s.add(m)
        s.flush()
        medicion_id = m.id
    listar_mediciones_atleta.clear()
    obtener_ultima_medicion.clear()
    listar_ultimas_mediciones.clear()
    estadisticas_grupo.clear()
    detalle_grupo_ultimas_mediciones.clear()
    contar_mediciones.clear()
    return medicion_id


def actualizar_medicion(medicion_id: int, data: dict) -> None:
    with get_session() as s:
        m = s.get(Medicion, medicion_id)
        if m:
            for campo, valor in data.items():
                setattr(m, campo, valor)
    listar_mediciones_atleta.clear()
    obtener_ultima_medicion.clear()
    listar_ultimas_mediciones.clear()
    estadisticas_grupo.clear()
    detalle_grupo_ultimas_mediciones.clear()


def eliminar_medicion(medicion_id: int) -> None:
    with get_session() as s:
        m = s.get(Medicion, medicion_id)
        if m:
            s.delete(m)
    listar_mediciones_atleta.clear()
    obtener_ultima_medicion.clear()
    listar_ultimas_mediciones.clear()
    estadisticas_grupo.clear()
    detalle_grupo_ultimas_mediciones.clear()
    contar_mediciones.clear()


@st.cache_data(ttl=30, show_spinner=False)
def listar_mediciones_atleta(atleta_id: int) -> pd.DataFrame:
    return pd.read_sql_query(
        text(
            """
            SELECT * FROM mediciones
            WHERE atleta_id = :atleta_id
            ORDER BY fecha_medicion ASC, fecha_hora_carga ASC
            """
        ),
        get_engine(),
        params={"atleta_id": atleta_id},
    )


@st.cache_data(ttl=30, show_spinner=False)
def obtener_ultima_medicion(atleta_id: int) -> dict | None:
    df = pd.read_sql_query(
        text(
            """
            SELECT * FROM mediciones WHERE atleta_id = :atleta_id
            ORDER BY fecha_medicion DESC, fecha_hora_carga DESC LIMIT 1
            """
        ),
        get_engine(),
        params={"atleta_id": atleta_id},
    )
    if df.empty:
        return None
    return df.iloc[0].to_dict()


@st.cache_data(ttl=30, show_spinner=False)
def listar_ultimas_mediciones(limite: int = 15) -> pd.DataFrame:
    return pd.read_sql_query(
        text(
            """
            SELECT m.id, m.fecha_hora_carga, m.fecha_medicion, m.cargado_por,
                   m.peso, m.imc, m.bio_grasa_corporal, m.pct_musculo_esqueletico,
                   a.nombre, a.apellido,
                   COALESCE(g.nombre_grupo, 'Sin grupo') AS nombre_grupo
            FROM mediciones m
            JOIN atletas a ON a.id = m.atleta_id
            LEFT JOIN grupos g ON g.id = a.grupo_id
            ORDER BY m.fecha_hora_carga DESC
            LIMIT :limite
            """
        ),
        get_engine(),
        params={"limite": limite},
    )


# ---------------------------------------------------------------------------
# Dashboard / estadísticas
# ---------------------------------------------------------------------------
@st.cache_data(ttl=30, show_spinner=False)
def contar_atletas() -> int:
    with get_engine().connect() as c:
        return c.execute(text("SELECT COUNT(*) FROM atletas")).scalar() or 0


@st.cache_data(ttl=30, show_spinner=False)
def contar_grupos() -> int:
    with get_engine().connect() as c:
        return c.execute(text("SELECT COUNT(*) FROM grupos")).scalar() or 0


@st.cache_data(ttl=30, show_spinner=False)
def contar_mediciones() -> int:
    with get_engine().connect() as c:
        return c.execute(text("SELECT COUNT(*) FROM mediciones")).scalar() or 0


@st.cache_data(ttl=30, show_spinner=False)
def estadisticas_grupo(grupo_id: int) -> dict:
    """Promedios grupales calculados sobre la última medición de cada atleta del grupo."""
    sql = text(
        """
        WITH ultima AS (
            SELECT DISTINCT ON (m.atleta_id) m.*
            FROM mediciones m
            JOIN atletas a ON a.id = m.atleta_id
            WHERE a.grupo_id = :grupo_id
            ORDER BY m.atleta_id, m.fecha_medicion DESC, m.fecha_hora_carga DESC
        )
        SELECT
            COUNT(*) AS cantidad_atletas,
            AVG(peso) AS peso_prom,
            AVG(imc) AS imc_prom,
            AVG(bio_grasa_corporal) AS grasa_prom,
            AVG(pct_musculo_esqueletico) AS musculo_prom,
            AVG(bio_grasa_visceral) AS grasa_visceral_prom,
            AVG(indice_cintura_cadera) AS icc_prom,
            AVG(indice_cintura_talla) AS ict_prom,
            AVG(sumatoria_6_pliegues) AS sumatoria_prom,
            AVG(endomorfia) AS endomorfia_prom,
            AVG(mesomorfia) AS mesomorfia_prom,
            AVG(ectomorfia) AS ectomorfia_prom,
            AVG(coord_x) AS x_prom,
            AVG(coord_y) AS y_prom
        FROM ultima
        """
    )
    df = pd.read_sql_query(sql, get_engine(), params={"grupo_id": grupo_id})
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


@st.cache_data(ttl=30, show_spinner=False)
def detalle_grupo_ultimas_mediciones(grupo_id: int) -> pd.DataFrame:
    sql = text(
        """
        WITH ultima AS (
            SELECT DISTINCT ON (m.atleta_id) m.*
            FROM mediciones m
            JOIN atletas a ON a.id = m.atleta_id
            WHERE a.grupo_id = :grupo_id
            ORDER BY m.atleta_id, m.fecha_medicion DESC, m.fecha_hora_carga DESC
        )
        SELECT a.nombre, a.apellido, a.sexo, a.edad, u.fecha_medicion,
               u.peso, u.altura, u.imc,
               u.pct_musculo_esqueletico, u.bio_grasa_corporal, u.bio_grasa_visceral,
               u.cintura, u.cadera, u.pliegue_abdominal,
               u.indice_cintura_cadera, u.indice_cintura_talla,
               u.porcentaje_grasa, u.porcentaje_musculo,
               u.sumatoria_6_pliegues, u.endomorfia, u.mesomorfia, u.ectomorfia,
               u.coord_x, u.coord_y
        FROM ultima u
        JOIN atletas a ON a.id = u.atleta_id
        ORDER BY a.apellido, a.nombre
        """
    )
    return pd.read_sql_query(sql, get_engine(), params={"grupo_id": grupo_id})
