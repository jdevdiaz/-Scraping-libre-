
1. **config**  
   - Archivo: `config/settings.py`  
   - Responsabilidad: define variables globales como `SOURCE_NAME`, `SEARCH_QUERY`, rutas y parámetros de scraping.  
   - Decisión: mantener todo configurable para facilitar cambios de fuente o query sin modificar el código.

2. **browser**  
   - Archivo: `src/infrastructure/browser.py`  
   - Responsabilidad: inicializar Playwright (Chromium/Firefox/WebKit), manejar contextos y páginas, aplicar configuraciones headless y stealth.  
   - Decisión: usar `BrowserManager` para centralizar la gestión del navegador, simplificando pruebas y reutilización.

3. **extractor**  
   - Archivo: `src/services/extractor.py`  
   - Responsabilidad: interactuar con el HTML, buscar productos, extraer información y mapear a `RAMProduct`.  
   - Diseño: clase `MLExtractor` con métodos `search_products()` y `extract_data()` para separar navegación de extracción.

4. **utils**  
   - Archivos: varios módulos auxiliares según necesidad (parseo, limpieza de datos, validación).  
   - Responsabilidad: tareas genéricas que no dependen del navegador ni del modelo.

5. **model**  
   - Archivo: `src/models/product.py`  
   - Responsabilidad: definición de `RAMProduct` como dataclass para garantizar estructura consistente de los datos.  
   - Campos: `title`, `price`, `currency`, `link`, `source`, `scraped_at`.

6. **storage**  
   - Archivo: a implementar según estrategia de persistencia (CSV, JSON, DB).  
   - Responsabilidad: guardar resultados del scraping de manera consistente y reproducible.

7. **data**  
   - Carpeta para almacenar resultados exportados.  

## Decisiones de Diseño

- **Separación de responsabilidades**: cada módulo tiene un foco único.  
- **Pruebas internas**: `_debug_run()` en extractor permite testear sin lanzar todo el pipeline.  
- **Headless y stealth**: estrategias aplicadas para minimizar detección anti-bots.  
- **Configurabilidad**: todo parámetro relevante centralizado en `settings.py`.

## Limitaciones

- Depende de selectores específicos de Mercado Libre (`ui-search-item__title`, `poly-price__number`). Cambios en la web pueden romper extracción.  
## Limitaciones

- Dependencia de selectores específicos de Mercado Libre (`ui-search-item__title`, `poly-price__number`). Cambios en la web pueden romper extracción.
- Configuración de variables de entorno: se requirió organizar `.env_scraping` correctamente para evitar errores de paths y dependencias.
- Playwright requiere dependencias del sistema Linux (WSL) para funcionar correctamente; algunas bibliotecas (GTK, GStreamer, etc.) son obligatorias.
- No hay manejo de paginación implementado; se limita a los primeros 50 productos.
- Dificultad inicial en la estructura de código: se detectaron secciones mal organizadas que dificultaban imports y pruebas.
- Dependencia de modelos de soporte externos para estrategias de extracción y stealth: se probó con modelos **Cloudsonet 4.6, Thinking y Gemini Pro Height**, lo cual aportó estabilidad en el scraping.