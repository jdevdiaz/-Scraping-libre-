# Diario de Desarrollo - Proyecto Web Scraping

## Sesión 1: Configuración inicial del proyecto
- Creación de entorno virtual `.env_scraping`.
- Instalación de dependencias: `playwright`, `playwright_stealth`, `python-dotenv`.
- Inicialización de estructura de carpetas (`src/models`, `src/infrastructure`, `src/services`, `docs`).

## Sesión 2: BrowserManager
- Implementación de `BrowserManager` para centralizar la apertura de navegadores.
- Problema: error `ModuleNotFoundError: No module named 'playwright'`.
- Solución: activar entorno virtual correcto y reinstalar `playwright`.

## Sesión 3: MLExtractor
- Implementación de `MLExtractor` para búsqueda y extracción de productos.
- Observaciones:
  - Selectores de Mercado Libre: `input.nav-search-input`, `ui-search-result__wrapper`.
  - Campos extraídos: `title`, `price`, `link`, `currency`, `source`, `scraped_at`.
- Problema: `TimeoutError` en `page.fill`.
- Solución: validar selectores, aumentar timeout y usar delays opcionales para asegurar carga.

## Sesión 4: Testing y debug
- Se creó `_debug_run()` en extractor para pruebas headless locales.
- Verificación de imports con `verify_imports.py`.
- Problema: `ImportError` con `stealth_async`.
- Solución: actualizar `playwright_stealth` o usar `stealth_sync` temporalmente.

## Sesión 5: Integración final
- Confirmado flujo `BrowserManager → MLExtractor → RAMProduct`.
- Preparación de scripts de prueba y documentación interna.
- Observaciones sobre WSL:
  - Dependencias de Linux requeridas por Playwright (GTK, libgstreamer, etc.)
  - Necesidad de instalar browsers (`playwright install`) después de cualquier actualización.

## Sesión X: Dificultades y soluciones principales
- **Variables de entorno mal configuradas**:
  - Problema: rutas de entorno y dependencias no reconocidas por Python/Playwright.
  - Solución: reorganizar `.env_scraping`, activar el entorno antes de cualquier ejecución.
- **Estructura de código inicial confusa**:
  - Problema: imports circulares y scripts de prueba mal ubicados.
  - Solución: refactorizar módulos (`browser.py`, `extractor.py`) y crear `_debug_run()` para pruebas locales por consola.
- **Dependencias de modelos externos**:
  - Se utilizó soporte de **Antigravity** con modelos: Cloudsonet 4.6, Thinking y Gemini Pro Height.
  - Resultado: mejor estabilidad y ejecución de estrategias stealth para scraping headless.