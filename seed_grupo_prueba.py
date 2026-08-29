"""
Script de una sola vez para cargar atletas y mediciones de ejemplo dentro
del grupo "Grupo Prueba", pensado para poder probar reportes y gráficos
con datos realistas.

Uso:
    source .venv/bin/activate
    python3 seed_grupo_prueba.py

Es seguro correrlo más de una vez: no borra nada, solo agrega atletas
nuevos (con nombres distintos) cada vez que se ejecuta.
"""
import random
from datetime import date, timedelta

import database as db
import utils_somatotype as som

random.seed()

NOMBRE_GRUPO = "Grupo Prueba"

ATLETAS_EJEMPLO = [
    ("Facundo", "Rodríguez", "Masculino", 24),
    ("Tomás", "Ibáñez", "Masculino", 29),
    ("Camila", "Suárez", "Femenino", 22),
    ("Valentina", "Correa", "Femenino", 27),
    ("Bruno", "Aguirre", "Masculino", 31),
]


def _rango(base, variacion):
    return round(base + random.uniform(-variacion, variacion), 1)


def generar_medicion_realista(sexo: str, fecha_medicion: date, factor_progreso: float = 0.0) -> dict:
    """Genera valores antropométricos plausibles para un/a deportista.
    `factor_progreso` > 0 simula mejoras leves en mediciones sucesivas."""
    if sexo == "Masculino":
        peso = _rango(78, 8) - factor_progreso * 1.2
        altura = _rango(178, 7)
        pliegue_tricipital = max(4, _rango(9, 2.5) - factor_progreso * 0.6)
        pliegue_subescapular = max(5, _rango(12, 3) - factor_progreso * 0.6)
        pliegue_suprailiaco = max(4, _rango(11, 3) - factor_progreso * 0.6)
        pliegue_abdominal = max(5, _rango(14, 3.5) - factor_progreso * 0.7)
        pliegue_muslo = max(5, _rango(12, 3) - factor_progreso * 0.6)
        pliegue_pantorrilla = max(4, _rango(9, 2) - factor_progreso * 0.4)
        diam_humero = _rango(7.0, 0.4)
        diam_femur = _rango(9.6, 0.4)
    else:
        peso = _rango(62, 6) - factor_progreso * 0.8
        altura = _rango(165, 6)
        pliegue_tricipital = max(6, _rango(15, 3) - factor_progreso * 0.6)
        pliegue_subescapular = max(6, _rango(13, 3) - factor_progreso * 0.5)
        pliegue_suprailiaco = max(6, _rango(14, 3) - factor_progreso * 0.5)
        pliegue_abdominal = max(6, _rango(16, 3.5) - factor_progreso * 0.6)
        pliegue_muslo = max(8, _rango(18, 3.5) - factor_progreso * 0.6)
        pliegue_pantorrilla = max(6, _rango(13, 2.5) - factor_progreso * 0.4)
        diam_humero = _rango(6.0, 0.3)
        diam_femur = _rango(8.6, 0.4)

    talla_sentado = round(altura * 0.52, 1)
    brazo_relajado = _rango(29 if sexo == "Masculino" else 26, 2)
    brazo_contraido = brazo_relajado + _rango(3, 0.8)
    cintura = _rango(82 if sexo == "Masculino" else 72, 5)
    cadera = _rango(96 if sexo == "Masculino" else 98, 5)
    perimetro_muslo = _rango(55 if sexo == "Masculino" else 54, 4)
    perimetro_pantorrilla = _rango(37 if sexo == "Masculino" else 35, 2.5)

    imc = som.calcular_imc(peso, altura)
    sumatoria_6 = som.calcular_sumatoria_6_pliegues(
        pliegue_tricipital, pliegue_subescapular, pliegue_suprailiaco,
        pliegue_abdominal, pliegue_muslo, pliegue_pantorrilla,
    )
    pct_grasa = som.calcular_porcentaje_grasa_yuhasz(sumatoria_6, sexo)
    pct_musculo = som.calcular_porcentaje_musculo_martin(
        peso, altura, brazo_relajado, pliegue_tricipital,
        perimetro_muslo, pliegue_muslo, perimetro_pantorrilla, pliegue_pantorrilla,
    )
    somatotipo = som.calcular_somatotipo(
        peso, altura, pliegue_tricipital, pliegue_subescapular, pliegue_suprailiaco,
        brazo_contraido, perimetro_pantorrilla, pliegue_pantorrilla, diam_humero, diam_femur,
    )

    return dict(
        fecha_medicion=fecha_medicion,
        peso=peso, altura=altura, talla_sentado=talla_sentado,
        brazo_relajado=round(brazo_relajado, 1), brazo_contraido=round(brazo_contraido, 1),
        cintura=cintura, cadera=cadera,
        perimetro_muslo_medio=perimetro_muslo, perimetro_pantorrilla=perimetro_pantorrilla,
        pliegue_tricipital=round(pliegue_tricipital, 1), pliegue_subescapular=round(pliegue_subescapular, 1),
        pliegue_suprailiaco=round(pliegue_suprailiaco, 1), pliegue_abdominal=round(pliegue_abdominal, 1),
        pliegue_muslo_medio=round(pliegue_muslo, 1), pliegue_pantorrilla=round(pliegue_pantorrilla, 1),
        diam_humero=diam_humero, diam_femur=diam_femur,
        bio_grasa_corporal=round(pct_grasa + random.uniform(-1, 1), 1),
        bio_agua_corporal=round(58 + random.uniform(-3, 3), 1),
        bio_masa_muscular=round(peso * (pct_musculo / 100) + random.uniform(-1, 1), 1),
        bio_masa_osea=round(3.2 if sexo == "Masculino" else 2.4, 1),
        bio_grasa_visceral=float(random.randint(3, 9)),
        bio_metabolismo_basal=float(round(1600 if sexo == "Masculino" else 1350 + random.uniform(-80, 80))),
        bio_edad_metabolica=float(random.randint(20, 35)),
        imc=imc, porcentaje_grasa=pct_grasa, porcentaje_musculo=pct_musculo,
        sumatoria_6_pliegues=sumatoria_6,
        endomorfia=somatotipo["endomorfia"], mesomorfia=somatotipo["mesomorfia"],
        ectomorfia=somatotipo["ectomorfia"], coord_x=somatotipo["coord_x"], coord_y=somatotipo["coord_y"],
        observaciones="Medición de ejemplo generada automáticamente para pruebas.",
    )


def main():
    db.init_db()

    grupos = db.obtener_grupos_dict()
    if NOMBRE_GRUPO not in grupos:
        print(f"No encontré el grupo '{NOMBRE_GRUPO}'. Creándolo...")
        grupo_id = db.crear_grupo(NOMBRE_GRUPO, "Grupo de prueba para validar reportes y gráficos.")
    else:
        grupo_id = grupos[NOMBRE_GRUPO]

    hoy = date.today()
    fechas = [hoy - timedelta(days=90), hoy - timedelta(days=45), hoy]

    for nombre, apellido, sexo, edad in ATLETAS_EJEMPLO:
        atleta_id = db.crear_atleta(grupo_id, nombre, apellido, sexo, edad, email="")
        print(f"Atleta creado: {nombre} {apellido} (id={atleta_id})")

        for i, fecha in enumerate(fechas):
            medicion = generar_medicion_realista(sexo, fecha, factor_progreso=i)
            medicion["atleta_id"] = atleta_id
            medicion["cargado_por"] = "seed_script"
            db.crear_medicion(medicion)
        print(f"  -> {len(fechas)} mediciones cargadas.")

    print("Listo. Entrá a la app y mirá 'Grupo Prueba' en Perfil de Atleta / Exportar & Reportes.")


if __name__ == "__main__":
    main()
