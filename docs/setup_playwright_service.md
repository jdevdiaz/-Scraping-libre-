# Guía de Configuración: Microservicio Playwright + ngrok

## Requisitos previos (MX Linux)

```bash
# Python 3.10+
python3 --version

# pip actualizado
pip install --upgrade pip
```

## 1. Instalación del Microservicio

```bash
cd -Scraping-libre-/scraper_service

# Instalar dependencias
pip install -r requirements.txt

# Instalar navegador Chromium para Playwright
playwright install chromium
playwright install-deps chromium
```

## 2. Iniciar el Microservicio

```bash
cd scraper_service

# Opción 1: Script directo
./start.sh

# Opción 2: Manual
uvicorn main:app --host 0.0.0.0 --port 8000
```

El servidor estará en `http://localhost:8000`

### Verificar que funciona:
```bash
# Health check
curl http://localhost:8000/health

# Probar scraping estático
curl -X POST http://localhost:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://es.wikipedia.org"}'

# Probar búsqueda de productos
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.mercadolibre.com.co", "buscar": "ram"}'
```

## 3. Exponer con ngrok

### Instalar ngrok en MX Linux:
```bash
# Descargar e instalar
curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok-v3-stable-linux-amd64.tgz | sudo tar xz -C /usr/local/bin

# Verificar instalación
ngrok version
```

### Crear cuenta gratuita en ngrok:
1. Ve a https://dashboard.ngrok.com/signup
2. Crea una cuenta (gratis)
3. Copia tu authtoken desde https://dashboard.ngrok.com/get-started/your-authtoken

### Configurar ngrok:
```bash
ngrok config add-authtoken TU_TOKEN_AQUI
```

### Exponer el microservicio:
```bash
ngrok http 8000
```

Verás algo como:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
```

**Copia la URL `https://abc123.ngrok-free.app`** — esta es la URL que usarás en n8n.

### Nota importante:
- La URL de ngrok cambia cada vez que lo reinicias (en plan gratuito)
- Cada vez que reinicies ngrok, deberás actualizar la URL en el nodo "Playwright Scraper" de n8n
- Para una URL fija, necesitas ngrok Pro ($8/mes) o usar alternativas como:
  - [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/) (gratis, URL fija)
  - [localtunnel](https://github.com/localtunnel/localtunnel) (gratis, URL semi-fija)

## 4. Configurar en n8n Cloud

1. Abre tu workflow en n8n Cloud
2. Busca el nodo **"Playwright Scraper"** (HTTP Request POST)
3. Cambia la URL a: `https://TU-URL-NGROK.ngrok-free.app/search`
4. Guarda el workflow

## 5. Ejecutar todo junto

Terminal 1 — Microservicio:
```bash
cd scraper_service && ./start.sh
```

Terminal 2 — ngrok:
```bash
ngrok http 8000
```

Terminal 3 — Dashboard (opcional):
```bash
cd streamlit_app && streamlit run app.py
```

Luego prueba desde Telegram:
```
/buscar dinamico https://www.mercadolibre.com.co ram
```

## Troubleshooting

### Error: "Playwright browsers not installed"
```bash
playwright install chromium
playwright install-deps chromium
```

### Error: "Permission denied" en ngrok
```bash
chmod +x /usr/local/bin/ngrok
```

### Error: "Connection refused" desde n8n
- Verifica que ngrok está corriendo (`ngrok http 8000`)
- Verifica que el microservicio está corriendo (debe responder en /health)
- Copia la URL correcta de ngrok al nodo de n8n

### El scraping no devuelve productos
- Algunos sitios tienen protección anti-bot agresiva
- Intenta aumentar MAX_SCROLL: `MAX_SCROLL=12 ./start.sh`
- Verifica que el sitio no está usando Cloudflare o similar
