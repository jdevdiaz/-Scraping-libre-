"""
Configuraciones globales del proyecto.
Aquí definimos constantes que no cambian durante la ejecución.
"""

# URL base para la búsqueda (Cambiable según el país)
BASE_URL = "https://listado.mercadolibre.com.co/"

# Término de búsqueda específico
SEARCH_QUERY = "memoria-ram"

# Configuración de sigilo y límites
MAX_PRODUCTS = 50
TIMEOUT = 30000  # Tiempo máximo de espera en milisegundos (30 segundos)

# Ruta del archivo de salida
OUTPUT_FILE = "data/ram_products.json"

# Identificador de la fuente (Escalabilidad)
SOURCE_NAME = "Mercado Libre"