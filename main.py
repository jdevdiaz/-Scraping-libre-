import asyncio
from src.infrastructure.browser import BrowserManager
from src.services.extractor import MLExtractor
from config.settings import OUTPUT_FILE
import json

async def main():
    print("🚀 Iniciando el Scraper de Memorias RAM...")
    
    # 1. Inicializamos el puente de infraestructura
    browser_manager = BrowserManager()
    
    try:
        # 2. Obtenemos la página (puedes poner headless=False para VER qué pasa)
        page = await browser_manager.get_page(headless=True)
        
        # 3. Inicializamos el servicio de extracción
        extractor = MLExtractor(page)
        
        print("🔍 Buscando productos en Mercado Libre...")
        await extractor.search_products()
        
        print("📦 Extrayendo datos...")
        products = await extractor.extract_data()
        
        # 4. Transformamos los objetos a una lista de diccionarios para JSON
        data_to_save = [vars(p) for p in products]
        
        # 5. Guardamos los resultados
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            
        print(f"✅ ¡Éxito! Se han guardado {len(products)} productos en {OUTPUT_FILE}")

    except Exception as e:
        print(f"❌ Error en la ejecución: {e}")
    
    finally:
        # 6. Siempre cerramos el navegador, pase lo que pase
        await browser_manager.close()
        print("🔒 Navegador cerrado.")

if __name__ == "__main__":
    asyncio.run(main())