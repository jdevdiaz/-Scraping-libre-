"""
Microservicio de Scraping con Playwright
=========================================
FastAPI server que recibe URLs y devuelve HTML limpio + productos extraídos
usando un navegador real con técnicas anti-detección.

Uso:
    uvicorn main:app --host 0.0.0.0 --port 8000

Endpoints:
    POST /scrape  — Scraping general (navega a URL, scroll, devuelve HTML limpio)
    POST /search  — Busca productos en e-commerce (extrae productos directamente)
    GET  /health  — Health check
"""

import asyncio
import json
import os
import re
import random
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright, Browser, BrowserContext

# ─── Configuración ───────────────────────────────────────────────────────────

HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
MAX_SCROLL_ATTEMPTS = int(os.getenv("MAX_SCROLL", "8"))
TIMEOUT_MS = int(os.getenv("TIMEOUT_MS", "30000"))

browser_instance: Browser | None = None
playwright_instance = None


# ─── Lifecycle ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global browser_instance, playwright_instance
    playwright_instance = await async_playwright().start()
    browser_instance = await playwright_instance.chromium.launch(
        headless=HEADLESS,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ],
    )
    print(f"Browser launched (headless={HEADLESS})")
    yield
    await browser_instance.close()
    await playwright_instance.stop()


app = FastAPI(
    title="Playwright Scraper Service",
    description="Microservicio de scraping con navegador real",
    version="2.0.0",
    lifespan=lifespan,
)


# ─── Models ──────────────────────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    url: str
    buscar: str = ""
    scroll: bool = True
    max_scroll: int = MAX_SCROLL_ATTEMPTS


class ScrapeResponse(BaseModel):
    html: str
    productos: list[dict[str, Any]] = []
    url_final: str
    longitud: int
    titulo: str
    total_productos: int = 0
    success: bool
    error: str = ""


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def create_stealth_context() -> BrowserContext:
    """Crea un contexto de navegador con configuración anti-detección."""
    context = await browser_instance.new_context(
        viewport={"width": 1366, "height": 768},
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
        locale="es-CO",
        timezone_id="America/Bogota",
        geolocation={"latitude": 4.711, "longitude": -74.0721},
        permissions=["geolocation"],
    )

    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['es-CO', 'es', 'en'] });
        window.chrome = { runtime: {} };
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) =>
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters);
    """)
    return context


async def auto_scroll(page, max_attempts: int = 8) -> None:
    """Scroll progresivo para cargar contenido dinámico."""
    prev_height = 0
    for i in range(max_attempts):
        current_height = await page.evaluate("document.body.scrollHeight")
        if current_height == prev_height and i > 0:
            break
        prev_height = current_height
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(random.uniform(1.0, 2.5))
    await page.evaluate("window.scrollTo(0, 0)")
    await asyncio.sleep(0.5)


def is_blocked(html: str) -> bool:
    """Detecta si el sitio mostró una página de bloqueo/CAPTCHA."""
    block_indicators = [
        "account-verification",
        "suspicious-traffic",
        "captcha",
        "robot",
        "blocked",
        "access denied",
        "cf-challenge",  # Cloudflare
        "challenge-platform",
    ]
    html_lower = html.lower()
    return any(indicator in html_lower for indicator in block_indicators)


def build_search_url(base_url: str, query: str) -> str:
    """Construye la URL de búsqueda según el sitio."""
    q = query.strip().replace(" ", "-")
    q_encoded = query.strip().replace(" ", "+")

    if "mercadolibre" in base_url:
        domain_match = re.match(r"https?://(?:www\.)?([^/]+)", base_url)
        if domain_match:
            domain = domain_match.group(1)
            return f"https://listado.{domain}/{q}"
        return f"{base_url}/{q}"
    elif "amazon" in base_url:
        return f"{base_url}/s?k={q_encoded}"
    elif "ebay" in base_url:
        return f"{base_url}/sch/i.html?_nkw={q_encoded}"
    elif "aliexpress" in base_url:
        return f"https://www.aliexpress.com/wholesale?SearchText={q_encoded}"
    else:
        return f"{base_url}/search?q={q_encoded}"


def clean_html(raw_html: str) -> str:
    """Limpia HTML eliminando scripts, styles y contenido no relevante."""
    # Eliminar scripts
    cleaned = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', raw_html, flags=re.IGNORECASE)
    # Eliminar styles
    cleaned = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', cleaned, flags=re.IGNORECASE)
    # Eliminar SVGs
    cleaned = re.sub(r'<svg[^>]*>[\s\S]*?</svg>', '', cleaned, flags=re.IGNORECASE)
    # Eliminar comentarios HTML
    cleaned = re.sub(r'<!--[\s\S]*?-->', '', cleaned)
    # Eliminar atributos data-* y style inline para reducir tamaño
    cleaned = re.sub(r'\s+data-[a-z-]+="[^"]*"', '', cleaned)
    cleaned = re.sub(r'\s+style="[^"]*"', '', cleaned)
    # Eliminar clases CSS muy largas (más de 100 chars)
    cleaned = re.sub(r'\s+class="[^"]{100,}"', '', cleaned)
    # Colapsar whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = re.sub(r'>\s+<', '><', cleaned)
    return cleaned.strip()


async def extract_products_mercadolibre(page) -> list[dict]:
    """Extrae productos de MercadoLibre usando selectores del DOM."""
    products = []
    try:
        # Selectores de MercadoLibre (múltiples variantes para resiliencia)
        selectors = [
            "li.ui-search-layout__item",
            "div.ui-search-result",
            "li[class*='search-layout__item']",
            "div[class*='poly-card']",
            "section.poly-card",
        ]

        items = []
        for selector in selectors:
            items = await page.query_selector_all(selector)
            if items:
                break

        if not items:
            # Fallback: intentar con selectores más genéricos
            items = await page.query_selector_all("ol.ui-search-layout li")

        for item in items[:50]:  # Max 50 productos
            product = {}
            try:
                # Título
                title_el = await item.query_selector(
                    "h2.poly-component__title a, "
                    "a.poly-component__title, "
                    "h2.ui-search-item__title, "
                    "a.ui-search-link__title-card, "
                    "h2 a[class*='title']"
                )
                if title_el:
                    product["titulo"] = (await title_el.inner_text()).strip()
                    href = await title_el.get_attribute("href")
                    product["enlace"] = href or ""
                else:
                    # Intentar obtener título de cualquier h2
                    h2 = await item.query_selector("h2")
                    if h2:
                        product["titulo"] = (await h2.inner_text()).strip()
                    else:
                        continue

                # Precio
                price_el = await item.query_selector(
                    "span.andes-money-amount__fraction, "
                    "span[class*='price-tag-fraction'], "
                    "span.poly-price__current .andes-money-amount__fraction"
                )
                if price_el:
                    price_text = (await price_el.inner_text()).strip()
                    price_text = re.sub(r'[^\d]', '', price_text)
                    product["precio"] = int(price_text) if price_text else 0
                else:
                    product["precio"] = 0

                # Moneda
                currency_el = await item.query_selector(
                    "span.andes-money-amount__currency-symbol"
                )
                if currency_el:
                    symbol = (await currency_el.inner_text()).strip()
                    if "$" in symbol:
                        product["moneda"] = "COP"
                    elif "US" in symbol:
                        product["moneda"] = "USD"
                    else:
                        product["moneda"] = "COP"
                else:
                    product["moneda"] = "COP"

                # Enlace (si no se obtuvo antes)
                if not product.get("enlace"):
                    link_el = await item.query_selector("a[href*='mercadolibre']")
                    if link_el:
                        product["enlace"] = await link_el.get_attribute("href") or ""
                    else:
                        product["enlace"] = ""

                # Vendedor
                seller_el = await item.query_selector(
                    "span.poly-component__seller, "
                    "p.ui-search-official-store-label, "
                    "span[class*='seller']"
                )
                if seller_el:
                    product["vendedor"] = (await seller_el.inner_text()).strip()
                else:
                    product["vendedor"] = "N/A"

                if product.get("titulo") and product.get("precio", 0) > 0:
                    products.append(product)

            except Exception:
                continue

    except Exception as e:
        print(f"Error extracting products: {e}")

    return products


async def extract_products_generic(page, base_url: str) -> list[dict]:
    """Extrae productos de sitios genéricos usando heurísticas."""
    if "mercadolibre" in base_url:
        return await extract_products_mercadolibre(page)

    # Para otros sitios, devolver lista vacía (Groq analizará el HTML)
    return []


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "browser": browser_instance is not None}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_page(req: ScrapeRequest):
    """Scraping general: navega a la URL, scroll, devuelve HTML limpio."""
    context = None
    try:
        context = await create_stealth_context()
        page = await context.new_page()

        await page.goto(req.url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
        await asyncio.sleep(random.uniform(1.0, 2.0))

        if req.scroll:
            await auto_scroll(page, req.max_scroll)

        raw_html = await page.content()
        html = clean_html(raw_html)
        title = await page.title()
        final_url = page.url

        return ScrapeResponse(
            html=html,
            url_final=final_url,
            longitud=len(html),
            titulo=title,
            success=True,
        )

    except Exception as e:
        return ScrapeResponse(
            html="",
            url_final=req.url,
            longitud=0,
            titulo="",
            success=False,
            error=str(e),
        )
    finally:
        if context:
            await context.close()


@app.post("/search", response_model=ScrapeResponse)
async def search_products(req: ScrapeRequest):
    """
    Búsqueda de productos: navega con navegador real, extrae productos
    directamente del DOM y también devuelve HTML limpio como fallback.
    Incluye detección de bloqueos y reintento automático.
    """
    if not req.buscar:
        raise HTTPException(status_code=400, detail="Campo 'buscar' es requerido")

    max_retries = 2
    last_error = ""

    for attempt in range(max_retries):
        context = None
        try:
            search_url = build_search_url(req.url, req.buscar)
            context = await create_stealth_context()
            page = await context.new_page()

            # Espera aleatoria antes de navegar (simula comportamiento humano)
            if attempt > 0:
                await asyncio.sleep(random.uniform(3.0, 6.0))

            await page.goto(search_url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
            await asyncio.sleep(random.uniform(2.0, 4.0))

            # Verificar si estamos bloqueados
            raw_html = await page.content()
            if is_blocked(raw_html):
                last_error = f"El sitio mostro una pagina de verificacion/CAPTCHA (intento {attempt + 1})"
                print(f"[BLOCKED] Attempt {attempt + 1}: {search_url}")
                await context.close()
                context = None
                if attempt < max_retries - 1:
                    await asyncio.sleep(random.uniform(5.0, 10.0))
                    continue
                else:
                    return ScrapeResponse(
                        html="",
                        url_final=search_url,
                        longitud=0,
                        titulo="",
                        success=False,
                        error=last_error + ". El sitio esta bloqueando peticiones desde este servidor. Intenta de nuevo en unos minutos.",
                    )

            # Cerrar popups/banners si existen
            for selector in [
                "button[data-testid='action:close']",
                ".cookie-consent-banner button",
                "[aria-label='Cerrar']",
                ".modal-close",
                "button.cookie-consent-banner-opt-out__action--key-accept",
            ]:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        await asyncio.sleep(0.5)
                except Exception:
                    pass

            # Esperar a que carguen los productos
            try:
                await page.wait_for_selector(
                    "li.ui-search-layout__item, div.poly-card, section.poly-card, ol.ui-search-layout",
                    timeout=10000,
                )
            except Exception:
                pass  # Continuar aunque no encuentre el selector exacto

            if req.scroll:
                await auto_scroll(page, req.max_scroll)

            # Extraer productos directamente del DOM
            productos = await extract_products_generic(page, req.url)

            # Obtener HTML limpio como fallback para Groq
            raw_html = await page.content()
            html = clean_html(raw_html)
            html = html[:60000]

            title = await page.title()
            final_url = page.url

            return ScrapeResponse(
                html=html,
                productos=productos,
                url_final=final_url,
                longitud=len(html),
                titulo=title,
                total_productos=len(productos),
                success=True,
            )

        except Exception as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                continue
            return ScrapeResponse(
                html="",
                url_final=req.url,
                longitud=0,
                titulo="",
                success=False,
                error=last_error,
            )
        finally:
            if context:
                await context.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
