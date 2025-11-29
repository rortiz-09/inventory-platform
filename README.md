# Server Governance Platform

Una plataforma de gestión de inventario de servidores **Auto-Didacta** y de **Alta Precisión**, capaz de detectar versiones específicas (Major.Minor.Patch) y consultar sus ciclos de vida en tiempo real.

## 🚀 Características

- **Motor de Normalización de Alta Precisión**: Detecta versiones exactas de SO (RHEL 8.4 ≠ RHEL 8.9)
- **Motor de Obsolescencia Inteligente**: Integración con API endoflife.date + caché persistente
- **Health Score Dinámico**: Puntuación basada en EOL, ambiente y métricas operativas
- **Autenticación Segura**: bcrypt + roles (admin, platform_lead, viewer)
- **UI Dark Mode Premium**: Alertas custom, charts Plotly, tablas interactivas

## 📦 Tech Stack

- Python 3.12+
- Streamlit
- DuckDB (persistencia)
- Plotly (visualizaciones)
- Pydantic (modelos)
- httpx (API calls)
- bcrypt (seguridad)

## 🐳 Quick Start

```bash
# Construir y ejecutar con Docker
docker compose up -d --build

# Acceder a la aplicación
open http://localhost:8501
```

## 👥 Usuarios por Defecto

| Usuario | Contraseña | Rol |
|---------|------------|-----|
| admin | admin123 | Administrador |
| platform_lead | platform123 | Líder de Plataforma |
| viewer | viewer123 | Visualizador |

## 📁 Estructura del Proyecto

```
/app
├── /data                 # Volumen persistente (DuckDB)
├── /src
│   ├── /auth            # Autenticación (bcrypt, sesiones)
│   ├── /components      # UI (alertas, charts, tablas)
│   ├── /core            # Base de datos DuckDB
│   ├── /logic           # Motores de inteligencia
│   │   ├── normalizer.py       # Regex de alta precisión
│   │   ├── lifecycle_engine.py # API + caché
│   │   ├── health_score.py     # Calculador de score
│   │   └── network_classifier.py
│   ├── /models          # Pydantic models
│   └── main.py          # Entry point
├── /styles
│   └── theme.css        # Dark mode styling
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```

## 🔧 Desarrollo Local

```bash
# Instalar dependencias con uv
uv sync

# Ejecutar aplicación
uv run streamlit run src/main.py
```

## 📊 Mapeo de Redes

| Subnet | Ambiente | Ciudad |
|--------|----------|--------|
| 192.168.59.0/24 | prod | gye |
| 192.168.21.0/24 | prod | uio |
| 192.168.77.0/24 | dev | shared |
| 192.168.76.0/24 | test | shared |

## 📈 Health Score

**Base: 100 puntos**

| Factor | Condición | Penalización |
|--------|-----------|--------------|
| EOL Vencido | Fecha EOL pasada | -40 |
| EOL Inminente | < 180 días | -20 |
| Versión Desconocida | No normalizada | -15 |
| Ambiente PROD | environment='prod' | -20 |
| Sin Owner | owner IS NULL | -5 |
| Sin IP | ip IS NULL | -10 |

## 📝 License

MIT
