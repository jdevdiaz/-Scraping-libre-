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
    # Scroll back to top
    await page.evaluate("window.scrollTo(0, 0)")
    await asyncio.sleep(0.5)


def build_search_url(base_url: str, query: str) -> str:
    """Construye la URL de búsqueda según el sitio."""
    q = query.strip().replace(" ", "-")
    q_encoded = query.strip().replace(" ", "+")

    if "mercadolibre" in base_url:
        # MercadoLibre: https://listado.mercadolibre.com.co/query
        import re
        domain_match = re.match(r"https?://(?:www\.)?([^/]+)", base_url)
        if domain_match:
            domain = domain_match.group(1)
            # listado.mercadolibre.com.co/query
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

        await page.goto(req.url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
        await asyncio.sleep(random.uniform(1.0, 2.0))

        if req.scroll:
            await auto_scroll(page, req.max_scroll)

        html = await page.content()
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
