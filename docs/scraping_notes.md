# Notas Técnicas de Scraping - Mercado Libre

## Selectores Clave
- Input de búsqueda: `input.nav-search-input`
- Contenedor de producto: `.ui-search-result__wrapper`
- Título: `.ui-search-item__title`
- Precio: `.poly-price__number .andes-money-amount__fraction`
- Link: `a.ui-search-link`

## Observaciones
- Mercado Libre puede cambiar selectores, por lo que se recomienda validar periódicamente.
- Se limita a los primeros 50 productos; paginación futura pendiente.
- Se extrae moneda fija `COP` según configuración.

## Estrategias Anti-bots
- Navegador headless (`headless=True`) + stealth opcional (`stealth_async` o `stealth_sync`).
- Delays opcionales entre navegación y extracción para simular comportamiento humano.

## Recomendaciones
- Validar dependencias Linux si se ejecuta en WSL (`libgtk-4`, `libgstreamer`, etc.).
- Configurar timeouts razonables (`wait_for_selector`) para evitar `TimeoutError`.
- Documentar cambios de selectores en `scraping_notes.md` para mantenimiento futuro.
- Utilizar `_debug_run()` para pruebas locales antes de integración completa.

## Dificultades Técnicas

- Timeout en `page.fill()` y `wait_for_selector` debido a carga lenta o cambios de DOM.
- Variables de entorno (`.env_scraping`) mal configuradas generaron errores de path y de importación.
- Dependencias de Linux necesarias para Playwright en WSL (GTK, GStreamer, libavif, etc.).
- Necesidad de usar modelos externos para estrategias stealth: Cloudsonet 4.6, Thinking, Gemini Pro Height.
- Estructura de código inicial requería refactor para separar responsabilidades y permitir testing local.W