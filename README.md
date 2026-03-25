# 🕸️ Mercado Libre Web Scraper (Playwright + Python)

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![Playwright](https://img.shields.io/badge/Playwright-Async-green?style=for-the-badge&logo=playwright)
![WSL2](https://img.shields.io/badge/WSL-2.0-orange?style=for-the-badge&logo=linux)

##  Descripción General
Este proyecto es un **Web Scraper modular y asíncrono** diseñado para extraer información de productos (como Memorias RAM) desde Mercado Libre. Utiliza **Playwright** en modo *headless* junto con estrategias antidetención (`playwright-stealth`) para simular el comportamiento humano y eludir protecciones antibot.

El sistema está construido bajo principios de **Clean Code y Arquitectura Modular**, separando claramente las responsabilidades en infraestructura, servicios de dominio y modelos de datos.

---

##  Arquitectura del Proyecto

La base de código sigue una estructura escalable, facilitando el mantenimiento y la integración de nuevas estrategias de extracción o almacenamiento.

```text
Web_Scraping/
├── config/                 # Configuraciones globales y variables de entorno
│   ├── settings.py         # Constantes estáticas (URLs, timeouts, selectores)
│   └── config.yaml         # (Opcional) Configuración externa estructurada
├── data/                   # Directorio de salida para los datos extraídos (JSON/CSV)
├── docs/                   # Documentación interna (Diarios, Arquitectura, Notas)
├── logs/                   # (Opcional) Archivos de registro de ejecución
├── src/
│   ├── core/               # Utilidades transversales y helpers genéricos
│   ├── infrastructure/     # Adaptadores de tecnología externa
│   │   ├── browser.py      # Gestión del ciclo de vida de Playwright y Stealth Mode
│   │   └── storage.py      # Gestión de persistencia (Ej. escritura a disco/JSON)
│   ├── models/             # Tipos de datos y entidades del dominio (DataClasses)
│   │   └── product.py      # Definición de la entidad Producto (RAMProduct)
│   └── services/           # Lógica de negocio y casos de uso
│       └── extractor.py    # Navegación, búsqueda y extracción del DOM (MLExtractor)
├── tests/                  # Pruebas unitarias e integrales
├── main.py                 # Punto de entrada de la aplicación (Orquestador)
└── requirements.txt        # Dependencias estrictas del entorno
```

### Flujo de Datos
1. **Inicialización**: `main.py` levanta el `BrowserManager` (Infraestructura).
2. **Navegación Asíncrona**: El browser abre un contexto limpio con inyección de evasiones *Stealth*.
3. **Extracción**: `MLExtractor` (Servicio) asume el control de la página, busca el término configurado y parsea el DOM usando selectores CSS actualizados.
4. **Transformación**: Se mapean los elementos HTML a objetos de dominio `RAMProduct` (Modelo).
5. **Persistencia**: La lista final se serializa y se guarda en `data/ram_products.json`.

---

##  Guía de Instalación y Ejecución

### 1. Prerrequisitos
- **Ubuntu/WSL2** (Se asume entorno Linux para una ejecución óptima de Chromium).
- **Python 3.12+**.

### 2. Configurar el Entorno Virtual
Clona este repositorio y configura tu entorno virtual (`.env_scraping`):

```bash
# Crear el entorno virtual
python3 -m venv .env_scraping

# Activar el entorno virtual
source .env_scraping/bin/activate
```

### 3. Instalar Dependencias
Instala los paquetes de Python definidos en `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 4. Instalar Navegadores de Playwright (Específico WSL)
Playwright requiere instalar los navegadores subyacentes y sus librerías correspondientes en el sistema operativo:

```bash
# Instala los binarios de los navegadores (Chromium, Firefox, WebKit)
playwright install

# (Solo Ubuntu/WSL) Instala librerías nativas requeridas (GTK, GStreamer, libavif, etc.)
playwright install-deps
```

### 5. Ejecutar el Scraper
Para iniciar el proceso completo de extracción:

```bash
python main.py
```

*Los resultados se generarán automáticamente en la carpeta `data/`.*

### Opcional: Modo Debug Local
El servicio de extracción cuenta con un bloque de tests aislado para pruebas rápidas en la consola sin ejecutar toda la infraestructura del proyecto:

```bash
python -m src.services.extractor
```

---

##  Stack Tecnológico y Buenas Prácticas

- **Concurrencia Extrema**: Diseño basado 100% en `asyncio` y `playwright.async_api` para I/O no bloqueante.
- **Evasión de Bots (Stealth Mode)**: Uso de la clase `Stealth` inyectada en cada contexto asíncrono para mutar headers y ocultar variables de entorno como `webdriver`.
- **Mantenibilidad Constructiva**: 
  - Centralización de selectores CSS propensos a cambiar.
  - Tipado fuerte (Type Hints) e instancias de `dataclass` puras.
- **Resiliencia al Fallo**: Patrón de `try/except` envoltorio a nivel de ítem; si la estructura de un producto particular cambia, se salta limpiamente en lugar de romper la ejecución.

---

##  Patrones a Mejorar (Roadmap / Tareas Pendientes)
- [ ] Implementar soporte para paginación (Scraping de +50 productos).
- [ ] Pasar a un sistema estructurado de logging (`import logging`) y descartar los clásicos `print()`.
- [ ] Manejo de persistencia agnóstica: Guardar transparentemente hacia PostgreSQL o MongoDB a través de un Adapter.
- [ ] Validaciones profundas sobre los Data Classes (Ej. migración a `Pydantic` o `Marshmallow`).
- [ ] Sistema de reintentos exponencial y control frente a posibles CAPTCHAs.
