import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://listado.mercadolibre.com.co/memoria-ram")
        
        items = await page.query_selector_all(".ui-search-result__wrapper")
        print(f"Items found: {len(items)}")
        if items:
            item = items[0]
            title = await item.query_selector(".ui-search-item__title")
            price = await item.query_selector(".poly-price__number .andes-money-amount__fraction")
            if not price:
                price = await item.query_selector(".ui-search-price--size-medium .andes-money-amount__fraction")
            link = await item.query_selector("a.ui-search-link")
            
            print(f"Title: {title is not None}")
            print(f"Price: {price is not None}")
            print(f"Link: {link is not None}")
            
            if title: print(await title.inner_text())
            
        await browser.close()

asyncio.run(main())
