from dataclasses import dataclass
from datetime import datetime

@dataclass
class RAMProduct:
    """
    Representa una unidad de Memoria RAM con trazabilidad y escalabilidad.
    """
    title: str
    price: int
    currency: str
    link: str
    source: str      # Ejemplo: "Mercado Libre"
    scraped_at: str  # Fecha y hora de la extracción (ISO 8601)