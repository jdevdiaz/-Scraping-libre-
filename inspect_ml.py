import asyncio
from playwright.async_api import async_playwright

async def inspect_ml():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        url = "https://listado.mercadolibre.com.co/memoria-ram"
        print(f"Navegando a {url} ...")
        await page.goto(url)
        
        # Esperamos al layout (que rara vez cambia)
        try:
            await page.wait_for_selector(".ui-search-layout")
        except:
            print("No se encontró el layout, de pronto nos bloquearon o cambiaron toda la estructura.")
        
        # Probamos diferentes clases de contenedor conocidas
        selectors = [
            ".ui-search-layout__item", 
            ".ui-search-result__wrapper",
            "li.ui-search-layout__item",
            ".andes-card"
        ]
        
        items = []
        for sel in selectors:
            items = await page.query_selector_all(sel)
            if items:
                print(f"¡Éxito! Encontrados {len(items)} items usando el selector: '{sel}'")
                break
                
        if items:
            html = await items[0].inner_html()
            # Escribir el HTML
            with open("ml_debug.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("Escrito a ml_debug.html, por favor dime si se creó el archivo.")
        else:
            print("NO SE ENCONTRARON ITMES CON NINGUNA DE LAS CLASES CONOCIDAS.")
            body = await page.inner_html("body")
            with open("ml_debug.html", "w", encoding="utf-8") as f:
                f.write(body)
            print("Se guardó todo el body en ml_debug.html para analizar.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_ml())
