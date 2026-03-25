from playwright.async_api import Page, ElementHandle
from src.models.product import RAMProduct
from datetime import datetime
from config.settings import SOURCE_NAME, SEARCH_QUERY


class MLExtractor:
    """Navega y extrae datos de productos en Mercado Libre."""

    # ── Selectores CSS ──────────────────────────────────────────────────────
    _URL          = "https://www.mercadolibre.com.co/"
    _INPUT        = "input.nav-search-input"
    _RESULTS      = ".ui-search-layout"
    _ITEM         = ".ui-search-result__wrapper"
    _TITLE        = ".ui-search-item__title"
    _PRICE        = ".poly-price__number .andes-money-amount__fraction"
    _LINK         = "a.ui-search-link"

    MAX_PRODUCTS  = 50

    def __init__(self, page: Page):
        self.page = page

    async def search_products(self) -> None:
        """Navega a la página y realiza la búsqueda."""
        await self.page.goto(self._URL)
        await self.page.fill(self._INPUT, SEARCH_QUERY)
        await self.page.keyboard.press("Enter")
        await self.page.wait_for_selector(self._RESULTS)

    async def _parse_item(self, item: ElementHandle) -> RAMProduct | None:
        """Extrae un RAMProduct desde un elemento de resultado. Retorna None si falta algún campo."""
        title = await item.query_selector(self._TITLE)
        price = await item.query_selector(self._PRICE)
        link  = await item.query_selector(self._LINK)

        if not (title and price and link):
            return None

        return RAMProduct(
            title      = await title.inner_text(),
            price      = int((await price.inner_text()).replace(".", "")),
            currency   = "COP",
            link       = await link.get_attribute("href"),
            source     = SOURCE_NAME,
            scraped_at = datetime.now().isoformat(),
        )

    async def extract_data(self) -> list[RAMProduct]:
        """Extrae la información de los primeros MAX_PRODUCTS productos."""
        products = []
        items = await self.page.query_selector_all(self._ITEM)

        for item in items[: self.MAX_PRODUCTS]:
            try:
                product = await self._parse_item(item)
                if product:
                    products.append(product)
            except Exception as e:
                print(f"[WARN] Error extrayendo un producto: {e}")

        return products


# ─────────────────────────────────────────────
#  MODO DEBUG  –  ejecución directa por consola
#  Uso:  python -m src.services.extractor
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import asyncio
    from playwright.async_api import async_playwright

    async def _debug_run():
        print("[DEBUG] Iniciando navegador en modo headless …")
        async with async_playwright() as pw:
            browser  = await pw.chromium.launch(headless=True)
            page     = await browser.new_page()
            extractor = MLExtractor(page)

            print(f"[DEBUG] Buscando: '{SEARCH_QUERY}' en {SOURCE_NAME} …")
            await extractor.search_products()

            print("[DEBUG] Extrayendo productos …")
            products = await extractor.extract_data()

            print(f"\n[DEBUG] Total productos extraídos: {len(products)}\n")
            for i, p in enumerate(products, 1):
                print(
                    f"  [{i:02d}] {p.title}\n"
                    f"        Precio : {p.price:,} {p.currency}\n"
                    f"        Link   : {p.link}\n"
                    f"        Fuente : {p.source}  |  {p.scraped_at}\n"
                )

            await browser.close()
        print("[DEBUG] Finalizado.")

    asyncio.run(_debug_run())