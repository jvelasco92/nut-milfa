# Nutrición Deportiva — App de Antropometría Colaborativa

App en Streamlit para que dos nutricionistas carguen y consulten mediciones
antropométricas (perímetros, pliegues, IMC, % grasa, % músculo y somatotipo
de Heath-Carter) sobre una base PostgreSQL centralizada en Supabase.

## Estructura del proyecto

```
app.py                          # UI Streamlit, navegación y autenticación
database.py                     # Modelos SQLAlchemy y acceso a datos (Supabase/PostgreSQL)
utils_somatotype.py             # IMC, % grasa (Yuhasz), % músculo (Martin), somatotipo Heath-Carter
pdf_generator.py                # Reportes PDF (ReportLab) y Excel (Pandas/OpenPyXL)
requirements.txt
.streamlit/secrets.toml.example # Plantilla de secretos (copiar a secrets.toml)
```

## Notas sobre los cálculos

- **% Grasa**: ecuación de Yuhasz sobre la sumatoria de 6 pliegues (distingue sexo).
- **% Músculo**: fórmula de Martin (1990) con perímetros de brazo, muslo y
  pantorrilla corregidos por su pliegue correspondiente.
- **Somatotipo (Heath-Carter)**: la mesomorfia requiere los diámetros
  biepicondilares de húmero y fémur — por eso el formulario de carga incluye
  un campo opcional "Diámetros óseos" que no estaba en el enunciado original
  pero es imprescindible para que la mesomorfia sea válida. Si se dejan en 0,
  la mesomorfia (y por lo tanto la Y de la somatocarta) no se calculará.

## 1. Configurar el proyecto en Supabase

1. Crear una cuenta en [supabase.com](https://supabase.com) y un **New Project**.
   Elegí una contraseña segura para la base — la vas a necesitar en el paso 3.
2. Esperá a que el proyecto termine de aprovisionarse (1-2 minutos).
3. Ir a **Project Settings → Database → Connection string → URI**.
   - Copiá la cadena en modo **Session pooler** (puerto 5432) o **Transaction
     pooler** (puerto 6543) — Streamlit Cloud funciona mejor contra el pooler
     que contra la conexión directa.
   - Reemplazá `[YOUR-PASSWORD]` por la contraseña del paso 1.
4. No hace falta crear las tablas a mano: la app las crea automáticamente
   (`database.init_db()`) la primera vez que corre, usando SQLAlchemy.
   Si preferís crearlas vos mismo, podés correr localmente:
   ```bash
   python -c "import database as db; db.init_db()"
   ```
   (con `secrets.toml` ya configurado apuntando a Supabase).

## 2. Configurar los secretos localmente

1. Copiá la plantilla:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
2. Editá `.streamlit/secrets.toml`:
   - Pegá tu `DATABASE_URL` de Supabase.
   - Definí usuario/contraseña para las dos nutricionistas en `[auth.users]`.
3. **Nunca subas `secrets.toml` a git** (ya está en `.gitignore`).

## 3. Correr la app localmente

```bash
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Abrí el navegador en `http://localhost:8501`, ingresá con uno de los usuarios
configurados y empezá a cargar grupos, atletas y mediciones.

## 4. Desplegar en Streamlit Community Cloud

1. Subí el proyecto a un repositorio de GitHub (sin `secrets.toml`, solo el
   `.example`).
2. Entrá a [share.streamlit.io](https://share.streamlit.io) con tu cuenta de
   GitHub y hacé clic en **New app**.
3. Elegí el repositorio, la rama y como **Main file path** poné `app.py`.
4. Antes de desplegar (o después, desde **Settings → Secrets**), pegá el
   contenido de tu `secrets.toml` local (con `DATABASE_URL` y `[auth.users]`
   reales) en el cuadro de **Secrets** de Streamlit Cloud. Esto reemplaza al
   archivo local — Streamlit Cloud lo inyecta como `st.secrets`.
5. Desplegá. La primera carga puede tardar un poco mientras se instalan las
   dependencias (ReportLab, Matplotlib, etc.).
6. Verificá la conexión: al entrar y loguearte, andá a "🏠 Dashboard" — si no
   tira error de conexión, la base está bien configurada. Si falla, revisá que
   la `DATABASE_URL` use el **pooler** de Supabase (Streamlit Cloud corre
   detrás de IPv4 y el pooler es compatible; la conexión directa de Supabase
   es IPv6-only en el plan gratuito).

## 5. Uso colaborativo entre las dos nutricionistas

- Ambas comparten la misma `DATABASE_URL`, por lo que ven los mismos grupos,
  atletas y mediciones en tiempo real (cada una con su propio usuario/clave).
- Cada medición guarda `cargado_por` con el usuario que la cargó y
  `fecha_hora_carga` con el timestamp exacto, para trazabilidad cuando ambas
  cargan datos sobre los mismos atletas.

## 6. Mantenimiento

- Para agregar más nutricionistas, sumá más pares `usuario = "clave"` dentro
  de `[auth.users]` en los secrets (local y en Streamlit Cloud).
- Para respaldar los datos, usá el **Database Backups** de Supabase o
  exportá desde la pestaña "📑 Exportar & Reportes" de la app.
