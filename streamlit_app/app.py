"""
Pipeline Híbrido de Scraping - Dashboard Streamlit
===================================================
Aplicación de analítica visual que se conecta a Google Sheets para
visualizar datos de scraping estático (SEO/estructura) y dinámico
(e-commerce) generados por el pipeline de n8n + Telegram.

Ejecutar:
    streamlit run streamlit_app/app.py
"""

import json
import os
from typing import Any

import gspread
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

# ─── Configuración global ────────────────────────────────────────────────────

load_dotenv()

GOOGLE_CREDENTIALS_PATH = os.getenv(
    "GOOGLE_CREDENTIALS_PATH", "credentials/service_account.json"
)
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Scraping_Pipeline")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


# ─── Conexión a Google Sheets ────────────────────────────────────────────────


@st.cache_resource(ttl=300)
def get_gspread_client() -> gspread.Client:
    """Autentica y retorna un cliente de gspread con caché de 5 min."""
    creds = Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_PATH, scopes=SCOPES
    )
    return gspread.authorize(creds)


def load_sheet_data(sheet_name: str) -> list[dict[str, Any]]:
    """Carga todos los registros de una pestaña como lista de dicts."""
    try:
        client = get_gspread_client()
        spreadsheet = client.open(GOOGLE_SHEET_NAME)
        worksheet = spreadsheet.worksheet(sheet_name)
        return worksheet.get_all_records()
    except gspread.exceptions.WorksheetNotFound:
        st.warning(f"La pestaña '{sheet_name}' no existe en el libro.")
        return []
    except FileNotFoundError:
        st.error(
            "No se encontró el archivo de credenciales de Google. "
            f"Ruta configurada: `{GOOGLE_CREDENTIALS_PATH}`"
        )
        return []
    except Exception as e:
        st.error(f"Error conectando a Google Sheets: {e}")
        return []


# ─── Funciones de procesamiento ──────────────────────────────────────────────


def normalize_keys(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normaliza las claves de los registros: elimina espacios y unifica case."""
    if not records:
        return records
    return [{k.strip(): v for k, v in row.items()} for row in records]


def parse_json_cell(raw: str) -> list[dict[str, Any]]:
    """Deserializa de forma segura una celda que contiene JSON."""
    if not raw or not isinstance(raw, str):
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
        return []
    except (json.JSONDecodeError, TypeError):
        return []


def build_dynamic_dataframe(json_data: list[dict[str, Any]]) -> pd.DataFrame:
    """Convierte una lista de dicts en DataFrame, normaliza precios."""
    if not json_data:
        return pd.DataFrame()
    df = pd.DataFrame(json_data)
    price_cols = [
        c for c in df.columns if "precio" in c.lower() or "price" in c.lower()
    ]
    for col in price_cols:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(r"[^\d.]", "", regex=True),
            errors="coerce",
        )
    return df


# ─── Visualizaciones: Scraping Estático ──────────────────────────────────────


def render_static_dashboard(records: list[dict[str, Any]]) -> None:
    """Renderiza el dashboard para auditorías de sitios estáticos."""
    if not records:
        st.info("No hay registros de scraping estático disponibles.")
        return

    df = pd.DataFrame(records)

    st.subheader("Registros de Auditoría SEO / Estructura")
    st.dataframe(df, use_container_width=True)

    selected_idx = st.selectbox(
        "Selecciona un registro para ver detalles:",
        range(len(df)),
        format_func=lambda i: f"{df.iloc[i].get('Fecha', 'N/A')} - {df.iloc[i].get('URL', 'N/A')}",
    )

    if selected_idx is not None:
        row = df.iloc[selected_idx]
        st.markdown("---")
        st.markdown(f"### Detalle: {row.get('Titulo', 'Sin título')}")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("H1", row.get("Cantidad_H1", 0))
        col2.metric("H2", row.get("Cantidad_H2", 0))
        col3.metric("H3", row.get("Cantidad_H3", 0))
        col4.metric("Enlaces", row.get("Enlaces_Totales", 0))

        headings_data = {
            "Tipo": ["H1", "H2", "H3"],
            "Cantidad": [
                int(row.get("Cantidad_H1", 0)),
                int(row.get("Cantidad_H2", 0)),
                int(row.get("Cantidad_H3", 0)),
            ],
        }
        fig_headings = px.bar(
            pd.DataFrame(headings_data),
            x="Tipo",
            y="Cantidad",
            title="Distribución de Encabezados",
            color="Tipo",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        st.plotly_chart(fig_headings, use_container_width=True)

        keywords_raw = row.get("Palabras_Clave", "")
        if keywords_raw:
            keywords = (
                keywords_raw
                if isinstance(keywords_raw, list)
                else [k.strip() for k in str(keywords_raw).split(",") if k.strip()]
            )
            if keywords:
                st.markdown("**Top Palabras Clave:**")
                st.write(", ".join(keywords))

        desc = row.get("Descripcion", "")
        if desc:
            with st.expander("Meta Descripción"):
                st.write(desc)


# ─── Visualizaciones: Scraping Dinámico ──────────────────────────────────────


def render_dynamic_dashboard(records: list[dict[str, Any]]) -> None:
    """Renderiza el dashboard para scraping de e-commerce."""
    if not records:
        st.info("No hay registros de scraping dinámico disponibles.")
        return

    df_records = pd.DataFrame(records)

    st.subheader("Historial de Búsquedas en E-commerce")
    st.dataframe(
        df_records[[c for c in df_records.columns if c.lower() != "datos_json"]],
        use_container_width=True,
    )

    selected_idx = st.selectbox(
        "Selecciona una búsqueda para analizar:",
        range(len(df_records)),
        format_func=lambda i: (
            f"{df_records.iloc[i].get('Fecha', 'N/A')} - "
            f"\"{df_records.iloc[i].get('Query_Buscado', df_records.iloc[i].get('Query_buscado', 'N/A'))}\" en "
            f"{df_records.iloc[i].get('URL_Origen', 'N/A')}"
        ),
        key="dynamic_selector",
    )

    if selected_idx is not None:
        row = df_records.iloc[selected_idx]
        json_col = next(
            (c for c in df_records.columns if c.lower() == "datos_json"),
            "Datos_JSON",
        )
        json_raw = row.get(json_col, "")
        items = parse_json_cell(str(json_raw))

        if not items:
            st.warning("No se pudo deserializar la celda Datos_JSON/Datos_json.")
            return

        df_products = build_dynamic_dataframe(items)

        if df_products.empty:
            st.warning("El DataFrame resultante está vacío.")
            return

        st.markdown("---")
        st.markdown(
            f"### Análisis: \"{row.get('Query_Buscado', row.get('Query_buscado', ''))}\" "
            f"({len(df_products)} productos)"
        )

        # Detectar columna de precio dinámicamente
        price_col = None
        for candidate in df_products.columns:
            if "precio" in candidate.lower() or "price" in candidate.lower():
                if pd.api.types.is_numeric_dtype(df_products[candidate]):
                    price_col = candidate
                    break

        if price_col:
            valid_prices = df_products[price_col].dropna()
            if not valid_prices.empty:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Items", len(df_products))
                col2.metric(
                    "Precio Promedio",
                    f"${valid_prices.mean():,.0f}",
                )
                col3.metric(
                    "Mas Barato",
                    f"${valid_prices.min():,.0f}",
                )
                col4.metric(
                    "Mas Caro",
                    f"${valid_prices.max():,.0f}",
                )

                # Histograma de precios
                fig_hist = px.histogram(
                    df_products,
                    x=price_col,
                    nbins=20,
                    title="Distribución de Precios",
                    labels={price_col: "Precio"},
                    color_discrete_sequence=["#636EFA"],
                )
                st.plotly_chart(fig_hist, use_container_width=True)

                # Box plot
                fig_box = px.box(
                    df_products,
                    y=price_col,
                    title="Rango de Precios (Box Plot)",
                    labels={price_col: "Precio"},
                )
                st.plotly_chart(fig_box, use_container_width=True)

        # Detectar columna de título/nombre
        title_col = None
        for candidate in df_products.columns:
            if any(
                kw in candidate.lower()
                for kw in ["titulo", "title", "nombre", "name", "producto"]
            ):
                title_col = candidate
                break

        # Top 10 por precio
        if price_col and title_col:
            st.markdown("#### Top 10 - Productos Mas Baratos")
            top_cheap = df_products.dropna(subset=[price_col]).nsmallest(10, price_col)
            st.dataframe(top_cheap, use_container_width=True)

            st.markdown("#### Top 10 - Productos Mas Caros")
            top_expensive = df_products.dropna(subset=[price_col]).nlargest(
                10, price_col
            )
            st.dataframe(top_expensive, use_container_width=True)

        # Detectar columnas categóricas para gráficos adicionales
        cat_cols = df_products.select_dtypes(include=["object"]).columns.tolist()
        excluded = {"link", "url", "enlace", "href", "imagen", "image", "img"}
        cat_cols = [c for c in cat_cols if c.lower() not in excluded and c != title_col]

        if cat_cols:
            chosen_cat = st.selectbox(
                "Agrupar por columna categórica:",
                cat_cols,
                key="cat_group",
            )
            counts = df_products[chosen_cat].value_counts().head(15)
            fig_cat = px.bar(
                x=counts.index,
                y=counts.values,
                title=f"Distribución por: {chosen_cat}",
                labels={"x": chosen_cat, "y": "Cantidad"},
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            st.plotly_chart(fig_cat, use_container_width=True)

        # Tabla completa expandible
        with st.expander("Ver datos completos (JSON deserializado)"):
            st.dataframe(df_products, use_container_width=True)


# ─── Página principal ────────────────────────────────────────────────────────


def main() -> None:
    """Punto de entrada de la aplicación Streamlit."""
    st.set_page_config(
        page_title="Pipeline de Scraping - Dashboard",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("Pipeline de Scraping Hibrido")
    st.caption("Telegram + n8n + Google Sheets + Streamlit")

    # Sidebar: navegación
    st.sidebar.header("Navegacion")
    page = st.sidebar.radio(
        "Tipo de análisis:",
        ["Scraping Dinamico (E-commerce)", "Scraping Estatico (SEO)"],
    )

    st.sidebar.markdown("---")
    if st.sidebar.button("Recargar datos"):
        st.cache_resource.clear()
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "**Fuente:** Google Sheets  \n" f"**Libro:** `{GOOGLE_SHEET_NAME}`"
    )

    # Renderizar según selección
    if page == "Scraping Dinamico (E-commerce)":
        with st.spinner("Cargando datos dinámicos desde Google Sheets..."):
            records = normalize_keys(load_sheet_data("Scraping_Dinamico"))
        render_dynamic_dashboard(records)
    else:
        with st.spinner("Cargando datos estáticos desde Google Sheets..."):
            records = normalize_keys(load_sheet_data("Scraping_Estatico"))
        render_static_dashboard(records)


if __name__ == "__main__":
    main()
