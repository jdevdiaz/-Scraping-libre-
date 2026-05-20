#!/bin/bash
# ============================================
# Script de inicio del Microservicio Playwright
# ============================================
# Uso: ./start.sh
# 
# Prerequisitos:
#   pip install -r requirements.txt
#   playwright install chromium
#
# Variables de entorno opcionales:
#   HEADLESS=true|false  (default: true)
#   MAX_SCROLL=8         (intentos de scroll)
#   TIMEOUT_MS=30000     (timeout de navegacion)

set -e

echo "=== Microservicio Playwright Scraper ==="
echo ""

# Verificar que playwright está instalado
if ! python3 -c "import playwright" 2>/dev/null; then
    echo "ERROR: playwright no está instalado."
    echo "Ejecuta: pip install -r requirements.txt && playwright install chromium"
    exit 1
fi

# Verificar que los browsers están instalados
if ! python3 -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.chromium.executable_path; p.stop()" 2>/dev/null; then
    echo "Instalando navegadores de Playwright..."
    playwright install chromium
    playwright install-deps chromium
fi

echo "Iniciando servidor en http://0.0.0.0:8000"
echo "Health check: http://localhost:8000/health"
echo ""
echo "Para exponer con ngrok:"
echo "  ngrok http 8000"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
