from playwright.async_api import async_playwright, Page
from config.settings import TIMEOUT


class BrowserManager:
    """
    Gestiona la instancia del navegador Playwright.
    Se encarga de la configuración de sigilo (Stealth) y el ciclo de vida del browser.
    """

    def __init__(self):
        self.playwright = None
        self.browser    = None
        self.context    = None

    async def get_page(self, headless: bool = True) -> Page:
        """
        Lanza el navegador y devuelve una página configurada con modo sigilo.

        Args:
            headless: Si es True, no se verá la ventana del navegador (ideal para WSL).

        Returns:
            Una instancia de Page de Playwright lista para navegar.
        """
        self.playwright = await async_playwright().start()

        # Lanzamos Chromium con User-Agent real para evitar detección
        self.browser = await self.playwright.chromium.launch(headless=headless)

        self.context = await self.browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/119.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
        )

        page = await self.context.new_page()

        from playwright_stealth import Stealth
        await Stealth().apply_stealth_async(page)
        page.set_default_timeout(TIMEOUT)

        return page

    async def close(self) -> None:
        """Cierra todos los procesos del navegador para liberar memoria."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("🔒 Navegador cerrado correctamente.")     # ← movido fuera del if