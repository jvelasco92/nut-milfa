"""
Genera un backup SQL completo de la base (grupos, atletas, mediciones) en un
único archivo .sql, restaurable con `psql` en cualquier base PostgreSQL vacía.

No depende de pg_dump (no está disponible en todos los entornos) — arma los
INSERT a mano usando psycopg2, que se encarga del escapado seguro de cada
valor.

Uso:
    source .venv/bin/activate
    python3 backup_db.py

Genera un archivo backups/backup_YYYY-MM-DD_HHhMM.sql (la carpeta se crea
sola si no existe).

Para restaurar en una base nueva (vacía, con las tablas ya creadas por
`database.init_db()`):
    psql "postgresql://usuario:clave@host:puerto/basededatos" -f backups/backup_....sql
"""
import os
from datetime import datetime

import database as db

TABLAS_EN_ORDEN = ["grupos", "atletas", "mediciones"]  # respeta las FKs (grupos -> atletas -> mediciones)


def generar_dump_sql() -> str:
    engine = db.get_engine()
    raw_conn = engine.raw_connection()
    cursor = raw_conn.cursor()

    lineas = [
        f"-- Backup Nut-Milfa generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "-- Restaurar con: psql \"<DATABASE_URL>\" -f este_archivo.sql",
        "-- (la base destino debe tener las tablas ya creadas, ej. corriendo database.init_db())",
        "",
        "BEGIN;",
        "",
    ]

    for tabla in TABLAS_EN_ORDEN:
        cursor.execute(f"SELECT * FROM {tabla} ORDER BY id")
        columnas = [desc[0] for desc in cursor.description]
        filas = cursor.fetchall()

        lineas.append(f"-- Tabla: {tabla} ({len(filas)} filas)")
        columnas_sql = ", ".join(columnas)
        placeholders = ", ".join(["%s"] * len(columnas))
        for fila in filas:
            insert_sql = cursor.mogrify(
                f"INSERT INTO {tabla} ({columnas_sql}) VALUES ({placeholders});",
                fila,
            ).decode("utf-8")
            lineas.append(insert_sql)

        if filas:
            lineas.append(f"SELECT setval(pg_get_serial_sequence('{tabla}', 'id'), (SELECT MAX(id) FROM {tabla}));")
        lineas.append("")

    lineas.append("COMMIT;")

    cursor.close()
    raw_conn.close()
    return "\n".join(lineas)


def main():
    contenido = generar_dump_sql()

    carpeta = os.path.join(os.path.dirname(__file__), "backups")
    os.makedirs(carpeta, exist_ok=True)

    nombre_archivo = f"backup_{datetime.now().strftime('%Y-%m-%d_%Hh%M')}.sql"
    ruta = os.path.join(carpeta, nombre_archivo)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"Backup generado: {ruta}")
    print(f"Tamaño: {os.path.getsize(ruta)} bytes")


if __name__ == "__main__":
    main()
