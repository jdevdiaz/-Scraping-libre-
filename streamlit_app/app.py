"""
Pipeline Híbrido de Scraping - Dashboard Streamlit v2
======================================================
Dashboard elegante y dinámico para visualizar datos de scraping
estático (SEO/estructura) y dinámico (e-commerce).

Ejecutar:
    streamlit run streamlit_app/app.py
"""

import json
import os
from typing import Any

import gspread
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

# ─── Configuración global ────────────────────────────────────────────────────

load_dotenv()

GOOGLE_CREDENTIALS_PATH = os.getenv(
    "GOOGLE_CREDENTIALS_PATH", "credentials/service_account.json"
)
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Scraping_Pipeline")
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

THEME_COLORS = {
    "primary": "#667eea",
    "secondary": "#764ba2",
    "success": "#2ecc71",
    "warning": "#f39c12",
    "danger": "#e74c3c",
    "info": "#3498db",
    "gradient": ["#667eea", "#764ba2", "#f093fb", "#f5576c", "#4facfe"],
}


# ─── CSS personalizado ──────────────────────────────────────────────────────

def inject_custom_css() -> None:
    st.markdown("""
    <style>
    .main-title {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 0;
    }
    .subtitle {
        color: #888;
        font-size: 1rem;
        margin-top: -10px;
        margin-bottom: 30px;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea20, #764ba220);
        border-radius: 12px;
        padding: 20px;
        border-left: 4px solid #667eea;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: 700;
        color: #333;
        border-bottom: 2px solid #667eea;
        padding-bottom: 8px;
        margin: 30px 0 15px 0;
    }
    .info-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-saved {
        background: #2ecc7130;
        color: #27ae60;
    }
    .badge-total {
        background: #3498db30;
        color: #2980b9;
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
    }
    </style>
    """, unsafe_allow_html=True)


# ─── Conexión a Google Sheets ────────────────────────────────────────────────

@st.cache_resource(ttl=300)
def get_gspread_client() -> gspread.Client:
    creds = Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_PATH, scopes=SCOPES
    )
    return gspread.authorize(creds)


def load_sheet_data(sheet_name: str) -> list[dict[str, Any]]:
    try:
        client = get_gspread_client()
        if GOOGLE_SHEETS_ID:
            spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)
        else:
            spreadsheet = client.open(GOOGLE_SHEET_NAME)
        worksheet = spreadsheet.worksheet(sheet_name)
        return worksheet.get_all_records()
    except gspread.exceptions.WorksheetNotFound:
        st.warning(f"La pestana '{sheet_name}' no existe en el libro.")
        return []
    except FileNotFoundError:
        st.error(
            "No se encontro el archivo de credenciales de Google. "
            f"Ruta configurada: `{GOOGLE_CREDENTIALS_PATH}`"
        )
        return []
    except Exception as e:
        st.error(f"Error conectando a Google Sheets: {e}")
        return []


# ─── Funciones de procesamiento ──────────────────────────────────────────────

def normalize_keys(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not records:
        return records
    return [{k.strip(): v for k, v in row.items()} for row in records]


def parse_json_cell(raw: str) -> list[dict[str, Any]]:
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


def detect_column(df: pd.DataFrame, keywords: list[str]) -> str | None:
    for candidate in df.columns:
        if any(kw in candidate.lower() for kw in keywords):
            return candidate
    return None


# ─── Dashboard de Resumen ────────────────────────────────────────────────────

def render_overview(records_static: list, records_dynamic: list) -> None:
    total_static = len(records_static)
    total_dynamic = len(records_dynamic)
    total = total_static + total_dynamic

    st.markdown('<div class="section-header">Resumen General</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Registros", total)
    col2.metric("Auditorias SEO", total_static)
    col3.metric("Busquedas E-commerce", total_dynamic)

    if total == 0:
        st.info("No hay datos guardados todavia. Usa el bot de Telegram con el comando `/buscar` para empezar.")
        return

    col_left, col_right = st.columns(2)

    with col_left:
        fig_pie = go.Figure(data=[go.Pie(
            labels=["Estatico (SEO)", "Dinamico (E-commerce)"],
            values=[total_static, total_dynamic],
            hole=0.5,
            marker=dict(colors=[THEME_COLORS["primary"], THEME_COLORS["warning"]]),
            textinfo="label+value",
        )])
        fig_pie.update_layout(
            title="Distribucion por Tipo",
            showlegend=False,
            height=350,
            margin=dict(t=50, b=20, l=20, r=20),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        all_dates = []
        for r in records_static:
            d = r.get("Fecha", "")
            if d:
                all_dates.append({"Fecha": str(d), "Tipo": "Estatico"})
        for r in records_dynamic:
            d = r.get("Fecha", "")
            if d:
                all_dates.append({"Fecha": str(d), "Tipo": "Dinamico"})

        if all_dates:
            df_dates = pd.DataFrame(all_dates)
            df_dates["Fecha"] = pd.to_datetime(df_dates["Fecha"], errors="coerce")
            df_dates = df_dates.dropna(subset=["Fecha"])
            if not df_dates.empty:
                counts = df_dates.groupby([df_dates["Fecha"].dt.date, "Tipo"]).size().reset_index(name="Cantidad")
                counts.columns = ["Fecha", "Tipo", "Cantidad"]
                fig_timeline = px.bar(
                    counts, x="Fecha", y="Cantidad", color="Tipo",
                    title="Actividad por Fecha",
                    color_discrete_map={"Estatico": THEME_COLORS["primary"], "Dinamico": THEME_COLORS["warning"]},
                )
                fig_timeline.update_layout(height=350, margin=dict(t=50, b=20, l=20, r=20))
                st.plotly_chart(fig_timeline, use_container_width=True)

    if records_static:
        st.markdown("**Ultimas Auditorias SEO:**")
        df_recent = pd.DataFrame(records_static[-5:])
        display_cols = [c for c in ["Fecha", "URL", "Titulo", "Enlaces_Totales"] if c in df_recent.columns]
        if display_cols:
            st.dataframe(df_recent[display_cols], use_container_width=True, hide_index=True)

    if records_dynamic:
        st.markdown("**Ultimas Busquedas E-commerce:**")
        df_recent = pd.DataFrame(records_dynamic[-5:])
        display_cols = [c for c in df_recent.columns if c.lower() != "datos_json"]
        if display_cols:
            st.dataframe(df_recent[display_cols], use_container_width=True, hide_index=True)


# ─── Visualizaciones: Scraping Estático ──────────────────────────────────────

def render_static_dashboard(records: list[dict[str, Any]]) -> None:
    if not records:
        st.info("No hay registros de scraping estatico disponibles.")
        st.markdown("Usa en Telegram: `/buscar estatico [URL] guardar`")
        return

    df = pd.DataFrame(records)

    st.markdown('<div class="section-header">Registros de Auditoria SEO</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("Total Auditorias", len(df))
    with col2:
        if "URL" in df.columns:
            urls_unicos = df["URL"].nunique()
            st.metric("URLs Unicas", urls_unicos)

    st.dataframe(df, use_container_width=True, hide_index=True)

    if len(df) == 0:
        return

    selected_idx = st.selectbox(
        "Selecciona un registro para ver detalles:",
        range(len(df)),
        format_func=lambda i: f"{df.iloc[i].get('Fecha', 'N/A')} - {df.iloc[i].get('URL', 'N/A')}",
    )

    if selected_idx is not None:
        row = df.iloc[selected_idx]
        st.markdown("---")
        st.markdown(f"### {row.get('Titulo', 'Sin titulo')}")
        st.caption(f"URL: {row.get('URL', 'N/A')} | Fecha: {row.get('Fecha', 'N/A')}")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("H1", row.get("Cantidad_H1", 0))
        col2.metric("H2", row.get("Cantidad_H2", 0))
        col3.metric("H3", row.get("Cantidad_H3", 0))
        col4.metric("Enlaces Totales", row.get("Enlaces_Totales", 0))

        col_left, col_right = st.columns(2)

        with col_left:
            headings_data = {
                "Tipo": ["H1", "H2", "H3"],
                "Cantidad": [
                    int(row.get("Cantidad_H1", 0) or 0),
                    int(row.get("Cantidad_H2", 0) or 0),
                    int(row.get("Cantidad_H3", 0) or 0),
                ],
            }
            fig_headings = px.bar(
                pd.DataFrame(headings_data),
                x="Tipo", y="Cantidad",
                title="Estructura de Encabezados",
                color="Tipo",
                color_discrete_sequence=[THEME_COLORS["primary"], THEME_COLORS["info"], THEME_COLORS["success"]],
            )
            fig_headings.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig_headings, use_container_width=True)

        with col_right:
            h_total = sum(headings_data["Cantidad"])
            links = int(row.get("Enlaces_Totales", 0) or 0)
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=h_total,
                title={"text": "Score Estructura HTML"},
                gauge={
                    "axis": {"range": [0, max(h_total * 2, 20)]},
                    "bar": {"color": THEME_COLORS["primary"]},
                    "steps": [
                        {"range": [0, 5], "color": "#ffcccc"},
                        {"range": [5, 15], "color": "#ffffcc"},
                        {"range": [15, max(h_total * 2, 20)], "color": "#ccffcc"},
                    ],
                },
            ))
            fig_gauge.update_layout(height=350)
            st.plotly_chart(fig_gauge, use_container_width=True)

        keywords_raw = row.get("Palabras_Clave", "")
        if keywords_raw:
            keywords = (
                keywords_raw
                if isinstance(keywords_raw, list)
                else [k.strip() for k in str(keywords_raw).split(",") if k.strip()]
            )
            if keywords:
                st.markdown("**Top Palabras Clave:**")
                cols = st.columns(min(len(keywords), 5))
                for i, kw in enumerate(keywords[:10]):
                    cols[i % len(cols)].code(kw)

        desc = row.get("Descripcion", "")
        if desc and desc != "Sin descripcion":
            with st.expander("Meta Descripcion"):
                st.write(desc)

    if len(df) > 1 and "Enlaces_Totales" in df.columns:
        st.markdown("---")
        st.markdown('<div class="section-header">Comparativa entre Sitios</div>', unsafe_allow_html=True)

        df_compare = df.copy()
        df_compare["Enlaces_Totales"] = pd.to_numeric(df_compare["Enlaces_Totales"], errors="coerce")
        df_compare["Total_H"] = (
            pd.to_numeric(df_compare.get("Cantidad_H1", 0), errors="coerce").fillna(0)
            + pd.to_numeric(df_compare.get("Cantidad_H2", 0), errors="coerce").fillna(0)
            + pd.to_numeric(df_compare.get("Cantidad_H3", 0), errors="coerce").fillna(0)
        )

        label_col = "Titulo" if "Titulo" in df_compare.columns else "URL"
        fig_compare = px.scatter(
            df_compare, x="Enlaces_Totales", y="Total_H",
            text=label_col,
            title="Enlaces vs Encabezados por Sitio",
            labels={"Enlaces_Totales": "Total Enlaces", "Total_H": "Total Encabezados"},
            color_discrete_sequence=[THEME_COLORS["primary"]],
            size="Enlaces_Totales",
            size_max=40,
        )
        fig_compare.update_traces(textposition="top center", textfont_size=10)
        fig_compare.update_layout(height=450)
        st.plotly_chart(fig_compare, use_container_width=True)


# ─── Visualizaciones: Scraping Dinámico ──────────────────────────────────────

def render_dynamic_dashboard(records: list[dict[str, Any]]) -> None:
    if not records:
        st.info("No hay registros de scraping dinamico disponibles.")
        st.markdown("Usa en Telegram: `/buscar dinamico [URL] [producto] guardar`")
        return

    df_records = pd.DataFrame(records)

    st.markdown('<div class="section-header">Historial de Busquedas E-commerce</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("Total Busquedas", len(df_records))
    with col2:
        query_col = next((c for c in df_records.columns if "query" in c.lower()), None)
        if query_col:
            queries_unicas = df_records[query_col].nunique()
            st.metric("Productos Diferentes", queries_unicas)

    display_cols = [c for c in df_records.columns if c.lower() != "datos_json"]
    st.dataframe(df_records[display_cols], use_container_width=True, hide_index=True)

    selected_idx = st.selectbox(
        "Selecciona una busqueda para analizar:",
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
            (c for c in df_records.columns if "datos" in c.lower() and "json" in c.lower()),
            "Datos_JSON",
        )
        json_raw = row.get(json_col, "")
        items = parse_json_cell(str(json_raw))

        if not items:
            st.warning("No se pudo deserializar la celda de datos JSON.")
            return

        df_products = build_dynamic_dataframe(items)

        if df_products.empty:
            st.warning("El DataFrame resultante esta vacio.")
            return

        query_display = row.get('Query_Buscado', row.get('Query_buscado', ''))
        st.markdown("---")
        st.markdown(f"### Analisis: \"{query_display}\"")
        st.caption(f"Fuente: {row.get('URL_Origen', 'N/A')} | Fecha: {row.get('Fecha', 'N/A')}")

        price_col = detect_column(df_products, ["precio", "price"])
        if price_col and not pd.api.types.is_numeric_dtype(df_products[price_col]):
            price_col = None

        title_col = detect_column(df_products, ["titulo", "title", "nombre", "name", "producto"])

        if price_col:
            valid_prices = df_products[price_col].dropna()
            if not valid_prices.empty:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Productos", len(df_products))
                col2.metric("Precio Promedio", f"${valid_prices.mean():,.0f}")
                col3.metric("Mas Barato", f"${valid_prices.min():,.0f}")
                col4.metric("Mas Caro", f"${valid_prices.max():,.0f}")

                tab1, tab2, tab3 = st.tabs(["Distribucion", "Rankings", "Categorias"])

                with tab1:
                    col_left, col_right = st.columns(2)
                    with col_left:
                        fig_hist = px.histogram(
                            df_products, x=price_col, nbins=20,
                            title="Distribucion de Precios",
                            labels={price_col: "Precio"},
                            color_discrete_sequence=[THEME_COLORS["primary"]],
                        )
                        fig_hist.update_layout(height=400)
                        st.plotly_chart(fig_hist, use_container_width=True)

                    with col_right:
                        fig_box = px.box(
                            df_products, y=price_col,
                            title="Rango de Precios (Box Plot)",
                            labels={price_col: "Precio"},
                            color_discrete_sequence=[THEME_COLORS["secondary"]],
                        )
                        fig_box.update_layout(height=400)
                        st.plotly_chart(fig_box, use_container_width=True)

                    if title_col:
                        fig_scatter = px.bar(
                            df_products.dropna(subset=[price_col]).sort_values(price_col).head(20),
                            x=title_col, y=price_col,
                            title="Precios por Producto (Top 20 mas baratos)",
                            labels={title_col: "Producto", price_col: "Precio"},
                            color=price_col,
                            color_continuous_scale="Viridis",
                        )
                        fig_scatter.update_layout(height=500, xaxis_tickangle=-45)
                        st.plotly_chart(fig_scatter, use_container_width=True)

                with tab2:
                    if title_col:
                        col_left, col_right = st.columns(2)
                        with col_left:
                            st.markdown("#### Top 10 - Mas Baratos")
                            top_cheap = df_products.dropna(subset=[price_col]).nsmallest(10, price_col)
                            display = [title_col, price_col]
                            vendor_col = detect_column(df_products, ["vendedor", "vendor", "seller"])
                            if vendor_col:
                                display.append(vendor_col)
                            st.dataframe(top_cheap[display], use_container_width=True, hide_index=True)

                        with col_right:
                            st.markdown("#### Top 10 - Mas Caros")
                            top_expensive = df_products.dropna(subset=[price_col]).nlargest(10, price_col)
                            st.dataframe(top_expensive[display], use_container_width=True, hide_index=True)
                    else:
                        st.dataframe(df_products, use_container_width=True, hide_index=True)

                with tab3:
                    cat_cols = df_products.select_dtypes(include=["object"]).columns.tolist()
                    excluded = {"link", "url", "enlace", "href", "imagen", "image", "img"}
                    cat_cols = [c for c in cat_cols if c.lower() not in excluded and c != title_col]

                    if cat_cols:
                        chosen_cat = st.selectbox(
                            "Agrupar por:", cat_cols, key="cat_group",
                        )
                        counts = df_products[chosen_cat].value_counts().head(15)

                        col_left, col_right = st.columns(2)
                        with col_left:
                            fig_bar = px.bar(
                                x=counts.index, y=counts.values,
                                title=f"Distribucion por: {chosen_cat}",
                                labels={"x": chosen_cat, "y": "Cantidad"},
                                color=counts.values,
                                color_continuous_scale="Viridis",
                            )
                            fig_bar.update_layout(height=400)
                            st.plotly_chart(fig_bar, use_container_width=True)

                        with col_right:
                            fig_pie = px.pie(
                                names=counts.index, values=counts.values,
                                title=f"Proporcion por: {chosen_cat}",
                                color_discrete_sequence=px.colors.qualitative.Set3,
                            )
                            fig_pie.update_layout(height=400)
                            st.plotly_chart(fig_pie, use_container_width=True)

                        if price_col:
                            avg_by_cat = df_products.groupby(chosen_cat)[price_col].mean().sort_values(ascending=False).head(10)
                            fig_avg = px.bar(
                                x=avg_by_cat.index, y=avg_by_cat.values,
                                title=f"Precio Promedio por {chosen_cat}",
                                labels={"x": chosen_cat, "y": "Precio Promedio"},
                                color_discrete_sequence=[THEME_COLORS["warning"]],
                            )
                            fig_avg.update_layout(height=400)
                            st.plotly_chart(fig_avg, use_container_width=True)
                    else:
                        st.info("No se encontraron columnas categoricas para agrupar.")

        else:
            st.metric("Total Productos", len(df_products))
            st.dataframe(df_products, use_container_width=True, hide_index=True)

        with st.expander("Ver datos completos (JSON deserializado)"):
            st.dataframe(df_products, use_container_width=True, hide_index=True)

        with st.expander("Ver JSON crudo"):
            st.json(items[:5])
            if len(items) > 5:
                st.caption(f"... y {len(items) - 5} productos mas")


# ─── Página principal ────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="Pipeline de Scraping - Dashboard",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    inject_custom_css()

    st.markdown('<p class="main-title">Pipeline de Scraping Hibrido</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Telegram + n8n + Google Sheets + Streamlit</p>', unsafe_allow_html=True)

    # Sidebar
    st.sidebar.markdown("### Navegacion")
    page = st.sidebar.radio(
        "Seccion:",
        ["Resumen General", "Scraping Dinamico (E-commerce)", "Scraping Estatico (SEO)"],
        label_visibility="collapsed",
    )

    st.sidebar.markdown("---")
    if st.sidebar.button("Recargar datos", type="primary", use_container_width=True):
        st.cache_resource.clear()
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Comandos del Bot:**")
    st.sidebar.code("/buscar estatico [URL]", language=None)
    st.sidebar.code("/buscar dinamico [URL] [producto]", language=None)
    st.sidebar.code("/reporte", language=None)
    st.sidebar.markdown("Agrega `guardar` al final para persistir datos.")

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"**Fuente:** Google Sheets  \n**Libro:** `{GOOGLE_SHEET_NAME}`"
    )

    # Cargar datos
    with st.spinner("Cargando datos desde Google Sheets..."):
        records_static = normalize_keys(load_sheet_data("Scraping_Estatico"))
        records_dynamic = normalize_keys(load_sheet_data("Scraping_Dinamico"))

    # Renderizar
    if page == "Resumen General":
        render_overview(records_static, records_dynamic)
    elif page == "Scraping Dinamico (E-commerce)":
        render_dynamic_dashboard(records_dynamic)
    else:
        render_static_dashboard(records_static)


if __name__ == "__main__":
    main()
