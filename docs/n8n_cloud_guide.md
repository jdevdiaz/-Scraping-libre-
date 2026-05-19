# Guía de Lógica de Nodos - n8n Cloud

## Visión General del Workflow

El workflow de n8n recibe un webhook de Telegram, parsea el comando `/buscar`, determina el tipo de scraping (estático/dinámico), ejecuta la extracción, opcionalmente guarda en Google Sheets, y responde con 2 mensajes al usuario.

---

## Diagrama de Nodos

```
[Telegram Trigger]
        │
        ▼
[Code: Parser de Comando]
        │
        ▼
[Switch: Tipo de Scraping]
       / \
      /   \
     ▼     ▼
[Rama     [Rama
Estática] Dinámica]
     │        │
     ▼        ▼
[HTTP GET] [Navegador/API Scraping]
     │        │
     ▼        ▼
[Code:    [AI Agent (LLM):
 Análisis  Scraper Semántico]
 HTML]        │
     │        ▼
     ▼     [Code: Formatear
[Code:    resultados]
Formatear     │
reporte]      │
     │        │
     ├────────┤
     ▼        ▼
[Switch: ¿Guardar?]
    / \
   /   \
  ▼     ▼
[Sí]  [No]
  │     │
  ▼     │
[Google  │
Sheets]  │
  │     │
  ├─────┤
  ▼
[Telegram: Mensaje 1 - Reporte]
        │
        ▼
[Telegram: Mensaje 2 - Enlace Streamlit]
```

---

## Nodo 1: Telegram Trigger

- **Tipo:** `Telegram Trigger`
- **Configuración:**
  - Activar en: `message`
  - El nodo recibe el objeto completo del mensaje.
- **Salida relevante:** `{{ $json.message.text }}` contiene el comando completo.

---

## Nodo 2: Code - Parser de Comando

- **Tipo:** `Code` (JavaScript)
- **Propósito:** Extraer las variables posicionales del mensaje.

```javascript
// Entrada: /buscar [tipo] [url] [producto_o_guardar] [guardar]
const text = $input.first().json.message.text || '';
const parts = text.trim().split(/\s+/);

// Validación mínima
if (parts.length < 3 || parts[0] !== '/buscar') {
  return [{
    json: {
      error: true,
      mensaje: 'Formato inválido. Uso:\n/buscar estatico [URL]\n/buscar dinamico [URL] [producto]'
    }
  }];
}

const tipo = parts[1].toLowerCase(); // "estatico" o "dinamico"
const url = parts[2];
let buscar = '';
let guardar = false;

if (tipo === 'dinamico') {
  // /buscar dinamico [URL] [producto] [guardar?]
  buscar = parts[3] || '';
  guardar = (parts[4] || '').toLowerCase() === 'guardar';
  // Reemplazar guiones por espacios en la búsqueda
  buscar = buscar.replace(/-/g, ' ');
} else if (tipo === 'estatico') {
  // /buscar estatico [URL] [guardar?]
  guardar = (parts[3] || '').toLowerCase() === 'guardar';
}

const chatId = $input.first().json.message.chat.id;

return [{
  json: { tipo, url, buscar, guardar, chatId, error: false }
}];
```

---

## Nodo 3: Switch - Tipo de Scraping

- **Tipo:** `Switch`
- **Condiciones:**
  - **Salida 1 ("estatico"):** `{{ $json.tipo }}` es igual a `estatico`
  - **Salida 2 ("dinamico"):** `{{ $json.tipo }}` es igual a `dinamico`
  - **Fallback:** Va a un nodo de error que responde "Tipo no reconocido".

---

## Rama Estática

### Nodo 4a: HTTP Request - Descargar HTML

- **Tipo:** `HTTP Request`
- **Método:** `GET`
- **URL:** `{{ $json.url }}`
- **Opciones:**
  - Response Format: `String`
  - Timeout: 15000ms

### Nodo 5a: Code - Análisis de Estructura HTML

- **Tipo:** `Code` (JavaScript)
- **Propósito:** Parsear el HTML crudo y extraer métricas SEO.

```javascript
const html = $input.first().json.data || $input.first().json.body || '';
const url = $('Code: Parser de Comando').first().json.url;

// Extraer título
const titleMatch = html.match(/<title[^>]*>(.*?)<\/title>/is);
const titulo = titleMatch ? titleMatch[1].trim() : 'Sin título';

// Extraer meta description
const descMatch = html.match(/<meta\s+name=["']description["']\s+content=["'](.*?)["']/is);
const descripcion = descMatch ? descMatch[1].trim() : 'Sin descripción';

// Contar encabezados
const countTag = (tag) => (html.match(new RegExp(`<${tag}[\\s>]`, 'gi')) || []).length;
const h1 = countTag('h1');
const h2 = countTag('h2');
const h3 = countTag('h3');

// Contar enlaces
const enlaces = (html.match(/<a\s/gi) || []).length;

// Extraer palabras clave (top 5 por frecuencia en texto visible)
const textOnly = html
  .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
  .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
  .replace(/<[^>]+>/g, ' ')
  .replace(/\s+/g, ' ')
  .toLowerCase();

const stopWords = new Set([
  'de', 'la', 'el', 'en', 'y', 'a', 'los', 'del', 'las', 'un', 'por',
  'con', 'no', 'una', 'su', 'para', 'es', 'al', 'que', 'se', 'lo',
  'como', 'más', 'o', 'pero', 'sus', 'le', 'ya', 'the', 'and', 'of',
  'to', 'in', 'is', 'it', 'for', 'on', 'with', 'as', 'at', 'this',
  'be', 'are', 'an', 'was', 'or', 'not', 'has', 'had', 'from', 'but'
]);

const wordFreq = {};
textOnly.split(/\s+/).forEach(word => {
  const clean = word.replace(/[^a-záéíóúñü]/g, '');
  if (clean.length > 3 && !stopWords.has(clean)) {
    wordFreq[clean] = (wordFreq[clean] || 0) + 1;
  }
});

const topKeywords = Object.entries(wordFreq)
  .sort((a, b) => b[1] - a[1])
  .slice(0, 5)
  .map(([word]) => word);

const guardar = $('Code: Parser de Comando').first().json.guardar;
const chatId = $('Code: Parser de Comando').first().json.chatId;

return [{
  json: {
    tipo: 'estatico',
    url,
    titulo,
    descripcion,
    h1, h2, h3,
    enlaces,
    palabras_clave: topKeywords.join(', '),
    guardar,
    chatId,
    fecha: new Date().toISOString().split('T')[0]
  }
}];
```

### Nodo 6a: Code - Formatear Reporte Estático

```javascript
const d = $input.first().json;

const reporte = `📊 *REPORTE DE AUDITORÍA WEB*
━━━━━━━━━━━━━━━━━━━━━━━━
🌐 *URL:* ${d.url}
📝 *Título:* ${d.titulo}

📐 *Estructura de Encabezados:*
   H1: ${d.h1} | H2: ${d.h2} | H3: ${d.h3}

🔗 *Total de Enlaces:* ${d.enlaces}

🏷️ *Top 5 Palabras Clave:*
${d.palabras_clave}

📅 Fecha: ${d.fecha}`;

return [{ json: { ...d, reporte } }];
```

---

## Rama Dinámica

### Nodo 4b: Scraping del Sitio Dinámico

**Opción A — Usar un servicio de renderizado externo (recomendado en n8n Cloud):**

- **Tipo:** `HTTP Request`
- **URL:** Servicio tipo ScrapingBee, Browserless, o ScrapFly que renderice JavaScript.
- **Ejemplo con endpoint genérico:**
  - URL: `https://api.scraping-service.com/render`
  - Parámetros: `url={{ $json.url }}`, `search={{ $json.buscar }}`

**Opción B — Usar el nodo HTTP + manipulación de la URL del e-commerce:**

Para Mercado Libre, la búsqueda se puede hacer directamente por URL:

```javascript
// Nodo Code previo para construir la URL de búsqueda
const base = $input.first().json.url;
const query = $input.first().json.buscar.replace(/\s+/g, '-');
// Mercado Libre: https://listado.mercadolibre.com.co/{query}
const searchUrl = base.includes('mercadolibre')
  ? `https://listado.mercadolibre.com.co/${query}`
  : `${base}/search?q=${encodeURIComponent($input.first().json.buscar)}`;

return [{ json: { ...$input.first().json, searchUrl } }];
```

Luego hacer HTTP GET a `{{ $json.searchUrl }}`.

### Nodo 5b: AI Agent - Scraper Semántico (LLM)

- **Tipo:** `AI Agent` o `OpenAI` (nodo de n8n)
- **Modelo:** GPT-4o-mini o equivalente
- **System Prompt:**

```
Eres un extractor de datos de e-commerce. Se te proporcionará el HTML de una
página de resultados de búsqueda. Extrae TODOS los productos visibles y
devuélvelos como un array JSON. Cada objeto debe tener:
- "titulo": nombre del producto
- "precio": precio numérico (sin símbolos de moneda, solo dígitos)
- "moneda": código de moneda (ej: "COP", "MXN", "USD")
- "enlace": URL completa del producto
- "vendedor": nombre del vendedor si está disponible, sino "N/A"

Responde ÚNICAMENTE con el array JSON, sin texto adicional ni markdown.
```

- **User Message:** `{{ $json.data }}` (el HTML renderizado)
- **Importante:** Configurar `Response Format` como JSON si el nodo lo permite.

### Nodo 6b: Code - Procesar Respuesta del LLM

```javascript
const llmResponse = $input.first().json.message?.content
  || $input.first().json.text
  || $input.first().json.output
  || '';

let productos = [];
try {
  // Limpiar posibles backticks de markdown
  const cleaned = llmResponse.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
  productos = JSON.parse(cleaned);
} catch (e) {
  return [{
    json: {
      error: true,
      mensaje: 'La IA no pudo extraer productos. Intenta con otro producto o URL.'
    }
  }];
}

// Calcular métricas
const precios = productos
  .map(p => parseFloat(p.precio))
  .filter(p => !isNaN(p) && p > 0);

const precioPromedio = precios.length
  ? Math.round(precios.reduce((a, b) => a + b, 0) / precios.length)
  : 0;
const masBarato = precios.length ? Math.min(...precios) : 0;
const masCaro = precios.length ? Math.max(...precios) : 0;

const query = $('Code: Parser de Comando').first().json.buscar;
const url = $('Code: Parser de Comando').first().json.url;
const guardar = $('Code: Parser de Comando').first().json.guardar;
const chatId = $('Code: Parser de Comando').first().json.chatId;
const fecha = new Date().toISOString().split('T')[0];

const reporte = `🛒 *REPORTE DE PRODUCTOS*
━━━━━━━━━━━━━━━━━━━━━━━━
🔎 *Búsqueda:* ${query}
🌐 *Fuente:* ${url}

💰 *Precio Promedio:* $${precioPromedio.toLocaleString()}
📉 *Más Barato:* $${masBarato.toLocaleString()}
📈 *Más Caro:* $${masCaro.toLocaleString()}
📦 *Total Items:* ${productos.length}

📅 Fecha: ${fecha}`;

return [{
  json: {
    tipo: 'dinamico',
    url,
    query,
    productos,
    datosJson: JSON.stringify(productos),
    precioPromedio,
    masBarato,
    masCaro,
    totalItems: productos.length,
    reporte,
    guardar,
    chatId,
    fecha
  }
}];
```

---

## Nodo 7: Switch - ¿Guardar en Google Sheets?

- **Tipo:** `Switch`
- **Condición:**
  - **Salida 1 ("guardar"):** `{{ $json.guardar }}` es `true`
  - **Salida 2 ("no_guardar"):** todo lo demás (default)

### Nodo 8 (Solo si guardar=true): Google Sheets - Append Row

**Para Scraping Estático:**

- **Tipo:** `Google Sheets`
- **Operación:** `Append Row`
- **Spreadsheet:** `Scraping_Pipeline`
- **Sheet:** `Scraping_Estatico`
- **Columnas mapeadas:**

| Columna Sheets     | Valor n8n                    |
| ------------------- | ----------------------------- |
| Fecha               | `{{ $json.fecha }}`           |
| URL                 | `{{ $json.url }}`             |
| Titulo              | `{{ $json.titulo }}`          |
| Descripcion         | `{{ $json.descripcion }}`     |
| Cantidad_H1         | `{{ $json.h1 }}`              |
| Cantidad_H2         | `{{ $json.h2 }}`              |
| Cantidad_H3         | `{{ $json.h3 }}`              |
| Enlaces_Totales     | `{{ $json.enlaces }}`         |
| Palabras_Clave      | `{{ $json.palabras_clave }}`  |

**Para Scraping Dinámico:**

- **Sheet:** `Scraping_Dinamico`
- **Columnas mapeadas:**

| Columna Sheets   | Valor n8n                    |
| ----------------- | ----------------------------- |
| Fecha             | `{{ $json.fecha }}`           |
| URL_Origen        | `{{ $json.url }}`             |
| Query_Buscado     | `{{ $json.query }}`           |
| Datos_JSON        | `{{ $json.datosJson }}`       |

---

## Nodos 9-10: Respuestas a Telegram

### Nodo 9: Telegram - Mensaje 1 (Reporte)

- **Tipo:** `Telegram`
- **Operación:** `Send Message`
- **Chat ID:** `{{ $json.chatId }}`
- **Text:** `{{ $json.reporte }}`
- **Parse Mode:** `Markdown`

### Nodo 10: Telegram - Mensaje 2 (Enlace)

- **Tipo:** `Telegram`
- **Operación:** `Send Message`
- **Chat ID:** `{{ $json.chatId }}`
- **Text:**
```
📊 Ver análisis completo en el dashboard:
{{ $env.STREAMLIT_URL || 'http://localhost:8501' }}
```

---

## Nodo de Error (Fallback)

Para cualquier rama que falle, agregar un nodo `Error Trigger` conectado a:

```javascript
const chatId = $('Code: Parser de Comando').first().json.chatId;
const errorMsg = `❌ Error procesando tu solicitud.\n\n${$input.first().json.error?.message || 'Error desconocido'}`;

return [{
  json: { chatId, text: errorMsg }
}];
```

Conectado a un nodo `Telegram: Send Message`.

---

## Variables de Entorno en n8n Cloud

Configurar en **Settings > Variables**:

| Variable           | Descripción                          | Ejemplo                          |
| ------------------- | ------------------------------------- | --------------------------------- |
| `STREAMLIT_URL`     | URL pública del dashboard             | `http://tu-ip:8501`              |
| `TELEGRAM_BOT_TOKEN`| Token del bot de Telegram             | `123456:ABC-DEF...`              |

---

## Credenciales Requeridas en n8n

1. **Telegram API** — Token del Bot (obtenido vía @BotFather)
2. **Google Sheets OAuth2** o **Service Account** — Para escritura en Sheets
3. **OpenAI API** (o proveedor LLM elegido) — Para el AI Agent en la rama dinámica

---

## Checklist de Implementación

- [ ] Crear el Bot de Telegram vía @BotFather y obtener el token
- [ ] Crear el libro de Google Sheets `Scraping_Pipeline` con las 2 pestañas
- [ ] Configurar credenciales de Google en n8n Cloud
- [ ] Configurar credencial de OpenAI/LLM en n8n Cloud
- [ ] Importar/recrear el workflow nodo por nodo
- [ ] Activar el workflow y probar con `/buscar estatico https://wikipedia.org`
- [ ] Probar con `/buscar dinamico https://mercadolibre.com.co ram`
