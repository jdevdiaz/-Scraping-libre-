"""
Microservicio de Scraping con Playwright
=========================================
FastAPI server que recibe URLs y devuelve HTML renderizado
usando un navegador real con técnicas anti-detección.

Uso:
    uvicorn main:app --host 0.0.0.0 --port 8000

Endpoints:
    POST /scrape  — Scraping general (navega a URL, scroll, devuelve HTML)
    POST /search  — Busca un producto en e-commerce (navega, busca, scroll, devuelve HTML)
    GET  /health  — Health check
"""

import asyncio
import os
import random
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright, Browser, BrowserContext
from playwright_stealth import Stealth

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
    version="1.0.0",
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
    url_final: str
    longitud: int
    titulo: str
    success: bool
    error: str = ""
    productos: list = []


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def create_stealth_context() -> BrowserContext:
    """Crea un contexto de navegador con configuración anti-detección."""
    # Obtenemos el UA real del navegador
    temp_page = await browser_instance.new_page()
    real_ua = await temp_page.evaluate("navigator.userAgent")
    await temp_page.close()
    
    # Limpiamos la palabra "HeadlessChrome" por "Chrome" para no levantar sospechas
    stealth_ua = real_ua.replace("HeadlessChrome", "Chrome")

    context = await browser_instance.new_context(
        viewport={"width": 1366, "height": 768},
        user_agent=stealth_ua,
        locale="es-CO",
        timezone_id="America/Bogota",
        geolocation={"latitude": 4.711, "longitude": -74.0721},
        permissions=["geolocation"],
    )
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
    # Scroll back to top
    await page.evaluate("window.scrollTo(0, 0)")
    await asyncio.sleep(0.5)


def clean_html(html: str) -> str:
    """Elimina etiquetas pesadas e inútiles para la IA reduciendo el tamaño drásticamente."""
    import re
    # Eliminar scripts, styles, svgs, noscripts, iframes
    cleaned = re.sub(r'<(script|style|svg|noscript|iframe|path)[^>]*>.*?</\1>', '', html, flags=re.IGNORECASE | re.DOTALL)
    # Eliminar comentarios HTML
    cleaned = re.sub(r'<!--.*?-->', '', cleaned, flags=re.DOTALL)
    return cleaned


def build_search_url(base_url: str, query: str) -> str:
    """Construye la URL de búsqueda según el sitio."""
    q = query.strip().replace(" ", "-")
    q_encoded = query.strip().replace(" ", "+")

    if "mercadolibre" in base_url:
        import re
        domain_match = re.match(r"https?://(?:www\.)?([^/]+)", base_url)
        if domain_match:
            domain = domain_match.group(1)
            if domain.startswith("listado."):
                return f"https://{domain}/{q}"
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


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "browser": browser_instance is not None}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_page(req: ScrapeRequest):
    """Scraping general: navega a la URL, scroll, devuelve HTML."""
    context = None
    try:
        context = await create_stealth_context()
        page = await context.new_page()
        
        # Aplicar el modo stealth
        await Stealth().apply_stealth_async(page)

        # Warmup de cookies: visitar el dominio raíz primero
        try:
            from urllib.parse import urlparse
            parsed_uri = urlparse(req.url)
            base_domain = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)
            await page.goto(base_domain, wait_until="commit", timeout=10000)
            await asyncio.sleep(random.uniform(0.5, 1.5))
        except Exception:
            pass

        await page.goto(req.url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
        await asyncio.sleep(random.uniform(1.0, 2.0))

        if req.scroll:
            await auto_scroll(page, req.max_scroll)

        html = await page.content()
        title = await page.title()
        final_url = page.url

        html = clean_html(html)

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
    Búsqueda de productos: construye URL de búsqueda según el sitio,
    navega con navegador real, scroll para cargar productos, devuelve HTML.
    """
    if not req.buscar:
        raise HTTPException(status_code=400, detail="Campo 'buscar' es requerido")

    context = None
    try:
        search_url = build_search_url(req.url, req.buscar)
        context = await create_stealth_context()
        page = await context.new_page()
        
        # Aplicar el modo stealth
        await Stealth().apply_stealth_async(page)

        # Warmup de cookies: visitar el dominio raíz primero
        try:
            from urllib.parse import urlparse
            parsed_uri = urlparse(req.url)
            base_domain = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)
            await page.goto(base_domain, wait_until="commit", timeout=10000)
            await asyncio.sleep(random.uniform(0.5, 1.5))
        except Exception:
            pass

        await page.goto(search_url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
        await asyncio.sleep(random.uniform(2.0, 4.0))

        # Cerrar popups/banners si existen
        for selector in [
            "button[data-testid='action:close']",
            ".cookie-consent-banner button",
            "[aria-label='Cerrar']",
            ".modal-close",
        ]:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    await asyncio.sleep(0.5)
            except Exception:
                pass

        if req.scroll:
            await auto_scroll(page, req.max_scroll)

        html = await page.content()
        title = await page.title()
        final_url = page.url

        # Detección básica de bloqueos por CAPTCHA o Cloudflare
        title_lower = title.lower()
        if "captcha" in title_lower or "just a moment" in title_lower or "robot" in title_lower or "security" in title_lower:
            raise Exception(f"Bloqueo detectado (CAPTCHA/Cloudflare). Título de la página: {title}")

        # Extracción local inteligente para evitar gastar tokens de IA
        productos_extraidos = []
        if "mercadolibre" in req.url.lower() or "mercadolibre" in final_url.lower():
            items = await page.query_selector_all(".ui-search-layout__item, .ui-search-result__wrapper")
            for item in items[:50]:
                title_el = await item.query_selector("h2, .poly-component__title, .ui-search-item__title")
                price_el = await item.query_selector(".andes-money-amount__fraction")
                link_el = await item.query_selector("a")
                
                if title_el and price_el and link_el:
                    try:
                        p_title = await title_el.inner_text()
                        p_price_text = await price_el.inner_text()
                        p_price = int(p_price_text.replace(".", "").replace(",", ""))
                        p_link = await link_el.get_attribute("href")
                        productos_extraidos.append({
                            "titulo": p_title.strip(),
                            "precio": p_price,
                            "link": p_link
                        })
                    except Exception:
                        pass

        html = clean_html(html)

        return ScrapeResponse(
            html=html,
            url_final=final_url,
            longitud=len(html),
            titulo=title,
            success=True,
            productos=productos_extraidos,
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
