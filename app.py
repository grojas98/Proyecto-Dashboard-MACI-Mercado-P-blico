# -*- coding: utf-8 -*-
"""
Created on Wed Apr  2 23:47:28 2025

@author: groja
"""
# librerías
from __future__ import annotations
import json
import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import Input, Output
import datetime

# cargar base de datos JSON detalles de licitaciones de mercado público
with open('mercado_publico.detalles.json', 'r', encoding='utf-8') as file:
    data_detalles = json.load(file)

# %%

# extraer información tabular desde la sección 'detalle'
rows = []
for entry in data_detalles:
    detalle = entry.get("detalle", {})
    fechas = detalle.get("Fechas", {})
    items = detalle.get("Items", {}).get("Listado", [])
    monto_estimado = detalle.get("MontoEstimado")
    
    # normalizar el campo de monto estimado
    if isinstance(monto_estimado, dict):
        monto_estimado = monto_estimado.get("$numberDouble")
    
    for item in items:
        # si un item está contenido dentro de un dict, extraerlo
        codigo_producto = item.get("CodigoProducto")
        if isinstance(codigo_producto, dict):
            codigo_producto = codigo_producto.get("$numberInt")
        
        unidad_duracion = detalle.get("UnidadTiempoDuracionContrato")
        if isinstance(unidad_duracion, dict):
            unidad_duracion = unidad_duracion.get("$numberInt")

        cantidad_producto = item.get("Cantidad")
        if isinstance(cantidad_producto, dict):
            cantidad_producto = cantidad_producto.get("$numberDouble")
        
        codigo_tipo = detalle.get("CodigoTipo")
        if isinstance(codigo_tipo, dict):
            codigo_tipo = codigo_tipo.get("$numberInt")
        
        comuna_comprador = detalle.get("Comprador")
        if isinstance(comuna_comprador, dict):
            comuna_comprador = comuna_comprador.get("ComunaUnidad")
            
        nombre_unidad = detalle.get("Comprador")
        if isinstance(nombre_unidad, dict):
            nombre_unidad = nombre_unidad.get("NombreUnidad")
        
        # unir los valores a una lista de json
        rows.append({
            "CodigoExterno": detalle.get("CodigoExterno"),
            "NombreLicitacion": detalle.get("Nombre"),
            "Descripcion": detalle.get("Descripcion"),
            "Region": detalle.get("Comprador", {}).get("RegionUnidad"),
            "Organismo": detalle.get("Comprador", {}).get("NombreOrganismo"),
            "Estado": detalle.get("Estado"),
            "MontoEstimado": monto_estimado,
            "FechaPublicacion": fechas.get("FechaPublicacion"),
            "FechaCierre": fechas.get("FechaCierre"),
            "CodigoProducto": codigo_producto,
            "NombreProducto": item.get("NombreProducto"),
            "CantidadProducto": cantidad_producto,
            "Categoria": item.get("Categoria"),
            "TiempoDuracionContrato": detalle.get("TiempoDuracionContrato"),
            "UnidadTiempoDuracionContrato": unidad_duracion,
            "CodigoTipo": codigo_tipo,
            "Tipo": detalle.get("Tipo"),
            "ComunaComprador": comuna_comprador,
            "NombreUnidad": nombre_unidad

        })
# crear un dataframe con la información contenida en el json
df = pd.DataFrame(rows)

# normalización de campos
df["ComunaComprador"] = df["ComunaComprador"].apply(lambda x: "No indica" if not x else x)
df["FechaPublicacion"] = pd.to_datetime(df["FechaPublicacion"], errors="coerce")
df["FechaCierre"] = pd.to_datetime(df["FechaCierre"], errors="coerce")
df["MontoEstimado"] = pd.to_numeric(df["MontoEstimado"], errors="coerce")
df["CantidadProducto"] = pd.to_numeric(df["CantidadProducto"], errors="coerce")
df['UnidadTiempoDuracionContrato'] = df['UnidadTiempoDuracionContrato'].astype(int)
df['TiempoDuracionContrato'] = df['TiempoDuracionContrato'].astype(int)
df["Region"] = df["Region"].str.strip()
df["Organismo"] = df["Organismo"].str.strip()
df['unidad_format'] = df.apply(lambda x: x['TiempoDuracionContrato']/24 if x['UnidadTiempoDuracionContrato'] == 1 else x['TiempoDuracionContrato'],axis=1)
df['unidad_format'] = df.apply(lambda x: x['TiempoDuracionContrato']*7 if x['UnidadTiempoDuracionContrato'] == 3 else x['unidad_format'],axis=1)
df['unidad_format'] = df.apply(lambda x: x['TiempoDuracionContrato']*30 if x['UnidadTiempoDuracionContrato'] == 4 else x['unidad_format'],axis=1)
df['unidad_format'] = df.apply(lambda x: x['TiempoDuracionContrato']*365 if x['UnidadTiempoDuracionContrato'] == 5 else x['unidad_format'],axis=1)
# fecha a nivel mes para series temporales
df["MesPublicacion"] = df["FechaPublicacion"].dt.to_period("M").dt.to_timestamp()
# considerar licitaciones del año 2024-2025
df = df.loc[df['FechaPublicacion']>=datetime.datetime(2024,1,1)]
# %%


"""
Panel Licitaciones Mercado Público

Dashboard interactivo construido con **Dash** para explorar licitaciones del
Mercado Público de Chile.  El código está pensado para que resulte sencillo
agregar nuevos filtros o gráficos sin romper la estructura.

"""

# inicialización de la app

app = dash.Dash(
    __name__,
    title="Panel Licitaciones Mercado Público",
    external_stylesheets=[dbc.themes.SANDSTONE],

)

# Layout

def serve_layout() -> html.Div:
    # obtener valores para filtros
    regions = sorted(df["Region"].dropna().unique())
    estados = sorted(df["Estado"].dropna().unique())
    organismos = sorted(df["Organismo"].dropna().unique())
    categorias = sorted(df["Categoria"].dropna().unique())
    min_date = df["FechaPublicacion"].min().date()
    max_date = df["FechaPublicacion"].max().date()

    # sidebar con filtros
    sidebar = dbc.Col(
        [
            html.H2("Bienvenido al Dashboard Analítico de Mercado Público",style={"marginBottom": "30px","fontWeight": "bold"}), # titulo de sidebar
            # introducción del sidebar
            html.P(
                "Este panel interactivo permite explorar licitaciones del Mercado Público chileno por región, organismo, categoría, estado y fechas. Use los filtros para comenzar.",
                className="mb-4",
                style={"fontSize": "1.1rem", "color": "white","textAlign": "justify","marginBottom": "30px"},
            ),
            html.H4("Filtros",style={"marginBottom": "30px","fontWeight": "bold"}),
            
            # dropdown de filtro región
            html.Label("Región"),
            dcc.Dropdown(
                id="region-dd",
                options=[{"label": r, "value": r} for r in regions], # opciones a escoger
                value=[],
                placeholder="Filtrar por Región",
                multi=True,
                className="mb-3",
                style={"color": "black"}
            ),
            # dropdown de filtro Estado
            html.Label("Estado"),
            dcc.Dropdown(
                id="estado-dd",
                options=[{"label": r, "value": r} for r in estados],
                value=[],
                placeholder="Filtrar por Estado",
                multi=True,
                className="mb-3",
                style={"color": "black"}
            ),
            # dropdown de filtro Organismo
            html.Label("Organismo"),
            dcc.Dropdown(
                id="org-dd",
                options=[{"label": o, "value": o} for o in organismos],
                value=[],
                placeholder="Filtrar por Organismo",
                multi=True,
                className="mb-3",
                style={"color": "black"}
            ),
            # dropdown de filtro Categoría
            html.Label("Categoría"),
            dcc.Dropdown(
                id="cat-dd",
                options=[{"label": o, "value": o} for o in categorias],
                value=[],
                placeholder="Filtrar por Categoría",
                multi=True,
                className="mb-3",
                style={"color": "black"}
            ),
            # filtro de rango de fechas
            html.Div([
            html.Label("Rango de fechas", style={"display": "block"}),
            dcc.DatePickerRange(
                id="date-range",
                min_date_allowed=min_date,
                max_date_allowed=max_date,
                start_date=min_date,
                end_date=max_date,
                display_format="YYYY-MM-DD",
                className="mb-3"
            ),
        ])


        ],
        # estilo adicional para el sidebar (colores, fuente, etc)
        width=2,
        style={
            "color": "white", 
            "position": "fixed",
            "top": 0,
            "left": 0,
            "bottom": 0,
            "padding": "2rem 1rem",
            "background-color": "#3239A1",
            "height": "100vh",
            "overflow-y": "auto",
        },
    )

    # contenido principal
    main_content = dbc.Col(
        width={"size": 10, "offset": 2},
        style={"padding": "2rem","background-color": "#FCFCFC",}, # estilo del contenido
        children=[
            html.H1("Panel Licitaciones Mercado Público", className="text-center my-4"), # título del dashboard
            # información adicional y objetivo del dashboard
            html.P(
                "Dashboard interactivo con métricas clave derivadas de la información pública disponible en la plataforma de Mercado Público. El objetivo es facilitar el análisis de datos de compras del Estado para toma de decisiones estratégicas, estudios de mercado, evaluación de oportunidades y seguimiento de comportamiento de compra.",
                className="text-center mb-4",
                style={"fontSize": "1.1rem"}
            ),
            # añadir los gráficos por fila (Row)
            dbc.Row(
                [
                    # separar la información en columnas (Col)
                    dbc.Col( 
                        # añadir gráfico en una Carta (diseño)
                        dbc.Card(
                            [
                                # header de la carta
                                dbc.CardHeader("Número de licitaciones por Región"),
                                # gráfico
                                dbc.CardBody(dcc.Graph(id="bar-region", style={"height": "350px"})),
                            ],
                            # nombre de clase para que las cartas tengan sombra
                            className="shadow-sm rounded",
                        ),
                        md=4,
                    ),
                    dbc.Col(
                        # añadir gráfico en una Carta (diseño)
                        dbc.Card(
                            [
                                # header de la carta
                                dbc.CardHeader("Monto de licitación por mes"),
                                # gráfico
                                dbc.CardBody(dcc.Graph(id="line-monto", style={"height": "350px"})),
                            ],
                            className="shadow-sm rounded",
                        ),
                        md=4,
                    ),
                    dbc.Col(
                        # añadir gráfico en una Carta (diseño)
                        dbc.Card(
                            [
                                # header de la carta
                                dbc.CardHeader("Evolución de cantidad de licitaciones"),
                                # gráfico
                                dbc.CardBody(dcc.Graph(id="line-time", style={"height": "350px"})),
                            ],
                            className="shadow-sm rounded",
                        ),
                        md=4,
                    ),
                ],
                className="mb-4",
            ),
            # siguiente fila del dashboard (Row)
            dbc.Row(
                [
                    # separar la información en columnas (Col)
                    dbc.Col(
                        # añadir gráfico en una Carta (diseño)
                        dbc.Card(
                            [
                                # header de la carta
                                dbc.CardHeader("Duración del Contrato vs Monto Estimado"),
                                # gráfico
                                dbc.CardBody(dcc.Graph(id="scatter-plot", style={"height": "593px"})),
                            ],
                            className="shadow-sm rounded",
                        ),
                        md=4,
                    ),
                    dbc.Col(
                        # añadir gráfico en una Carta (diseño)
                        dbc.Card(
                            [
                                # header de la carta
                                dbc.CardHeader("Distribución por Tipo"),
                                # body adicional para añadir toggles dentro de la carta del gráfico
                                dbc.CardBody(
                                    [
                                        dcc.RadioItems(
                                            id='tipo-toggle',
                                            options=[
                                                {'label': 'Público vs Privado', 'value': 'grupo'},
                                                {'label': 'Solo Privado', 'value': 'privado'},
                                                {'label': 'Solo Público', 'value': 'publico'}
                                            ],
                                            value='grupo',
                                            labelStyle={'display': 'inline-block', 'margin-right': '15px'},
                                            className="mb-3"
                                        ),
                                        dcc.Graph(id="pie-chart", style={"height": "550px"})
                                    ]
                                ),
                            ],
                            className="shadow-sm rounded",
                        ),
                        md=4,
                    ),
                    dbc.Col(
                        # añadir gráfico en una Carta (diseño)
                        dbc.Card(
                            [
                                # header de la carta
                                dbc.CardHeader("Mapa de Monto Estimado por Región"),
                                # gráfico
                                dbc.CardBody(dcc.Graph(id="world-map", style={"height": "1000px"})),
                            ],
                        ),
                        md=4,
                    ),
                ]
            ),
        ],
    )
    # retornar el layout
    return html.Div(
        [
            dcc.Location(id="url"),
            dbc.Container(
                fluid=True,
                children=dbc.Row([sidebar, main_content])
            )
        ]
    )


# aplicar layout
app.layout = serve_layout

# callbacks, definir inputs (filtros) y outputs (gráficos)

@app.callback(
    Output("bar-region", "figure"),
    Output("line-monto", "figure"),
    Output("line-time", "figure"),
    Output("scatter-plot", "figure"),
    Output("pie-chart", "figure"),
    Output("world-map", "figure"),
    Input("region-dd", "value"),
    Input("estado-dd", "value"),
    Input("org-dd", "value"),
    Input("cat-dd", "value"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
    Input("tipo-toggle", "value"),
)

def update_graphs(region_sel, estado_sel, org_sel, cat_sel, start_date, end_date, tipo_toggle):
    # cargar el geojson de regiones
    with open("regiones.json", "r", encoding="utf-8") as f:
        chile_geojson = json.load(f)
    import datetime
    
    # diccionarios con mapeos para gráficos particulares (Tipo y región)
    tipo_map = {
    "L1": "LP <100 UTM",
    "LE": "LP 100‑1k",
    "LP": "LP 1k‑2k",
    "LQ": "LP 2k‑5k",
    "LR": "LP >5k",
    "E2": "LPriv <100",
    "CO": "LPriv 100‑1k",
    "B2": "LPriv 1k‑2k",
    "H2": "LPriv 2k‑5k",
    "I2": "LPriv >5k",
    "LS": "LP Serv. pers.",
    }
    mapeo_regiones = {
        "Región de la Araucanía": "Región de La Araucanía",
        "Región Metropolitana de Santiago": "Región Metropolitana de Santiago",
        "Región de Coquimbo": "Región de Coquimbo",
        "Región del Maule": "Región del Maule",
        "Región Aysén del General Carlos Ibáñez del Campo": "Región de Aysén del Gral.Ibañez del Campo",
        "Región de Tarapacá": "Región de Tarapacá",
        "Región de Atacama": "Región de Atacama",
        "Región de Valparaíso": "Región de Valparaíso",
        "Región de Magallanes y de la Antártica": "Región de Magallanes y Antártica Chilena",
        "Región del Biobío": "Región del Bío-Bío",
        "Región del Libertador General Bernardo O´Higgins": "Región del Libertador Bernardo O'Higgins",
        "Región de Los Ríos": "Región de Los Ríos",
        "Región del Ñuble": "Región de Ñuble",
        "Región de los Lagos": "Región de Los Lagos",
        "Región de Antofagasta": "Región de Antofagasta",
        "Región de Arica y Parinacota": "Región de Arica y Parinacota"
    }
    region_roman = {
    "Región de Arica y Parinacota": "XV",
    "Región de Tarapacá": "I",
    "Región de Antofagasta": "II",
    "Región de Atacama": "III",
    "Región de Coquimbo": "IV",
    "Región de Valparaíso": "V",
    "Región Metropolitana de Santiago": "RM",
    "Región del Libertador General Bernardo O´Higgins": "VI",
    "Región del Maule": "VII",
    "Región de Ñuble": "XVI",
    "Región del Biobío": "VIII",
    "Región de la Araucanía": "IX",
    "Región de Los Ríos": "XIV",
    "Región de los Lagos": "X",
    "Región de Aysén del General Carlos Ibáñez del Campo": "XI",
    "Región de Magallanes y de la Antártica": "XII",
    }
    
    # filtra el dataframe según los controles y devuelve las figuras
    data_region = df.copy()
    data = df.copy()
    data_map = data.copy()
    data = data.loc[data['FechaPublicacion']>= datetime.datetime(2025,1,1)]

    # condicionales si es que se selecciona algún filtro
    if region_sel:
        data = data.loc[data["Region"].isin(region_sel)]
    if estado_sel:
        data = data[data["Estado"].isin(estado_sel)]
        data_region = data_region[data_region["Estado"].isin(estado_sel)]
    if org_sel:
        data = data[data["Organismo"].isin(org_sel)]
    if cat_sel:
        data = data[data["Categoria"].isin(cat_sel)]
    if start_date and end_date:
        data = data[(data["FechaPublicacion"] >= start_date) & (data["FechaPublicacion"] <= end_date)]

    # Gráfico 1: Nº licitaciones por región
    # agrupar data por región
    region_counts = (
        data_region.groupby("Region", dropna=False)
        .size()
        .reset_index(name="Licitaciones")
        .sort_values("Licitaciones", ascending=False)
    )
    # mapear n de región
    region_counts["RegionRoman"] = region_counts["Region"].map(region_roman)
    # mostrar el nombre al hover del mouse
    region_counts["CustomHover"] = (
        "Región=" + region_counts["Region"] + "<br>Nº licitaciones=" + region_counts["Licitaciones"].astype(str)
    )
    # graficar
    fig_region = px.bar(
        region_counts,
        x="RegionRoman",
        y="Licitaciones",
        labels={"RegionRoman": "Región", "Licitaciones": "Nº licitaciones"},
        custom_data=["CustomHover"]
    )
    fig_region.update_traces(
        hovertemplate="%{customdata[0]}"
    )
    fig_region.update_layout(
        xaxis_title="",
        yaxis_title=""
    )

    # Gráfico 2: Monto total por mes
    monto_mensual = (
    data.dropna(subset=["MontoEstimado"])
    .groupby("MesPublicacion")["MontoEstimado"]
    .sum()
    .reset_index()
    )
    
    # agrega columna con nombre de mes
    monto_mensual["MesTexto"] = monto_mensual["MesPublicacion"].dt.strftime("%B %Y")

    # graficar
    fig_monto = px.bar(
    monto_mensual,
    x="MesTexto",
    y="MontoEstimado",
    labels={"MesTexto": "Mes", "MontoEstimado": "Monto (CLP)"},
    )
    fig_monto.update_yaxes(tickprefix="$", separatethousands=True)
    
    # Gráfico 3: Cantidad de licitaciones por día
    # agrupar por día
    licitaciones_por_dia = data.groupby(data['FechaPublicacion'].dt.date).size().reset_index(name='Cantidad')

    # graficar
    fig_licitaciones = px.line(licitaciones_por_dia, x='FechaPublicacion', y='Cantidad',
                  labels={'Fecha': 'Fecha', 'Cantidad': 'Cantidad de licitaciones'})
    
    fig_licitaciones.update_layout(xaxis_title='FechaPublicacion',
                      yaxis_title='Cantidad de licitaciones',
                      xaxis=dict(tickangle=45),
                      template='plotly_white')
    
    # Gráfico 4: Relación Monto estimado v/s duración del contrato
    df_validos = data.copy()
    df_validos = data[(data['MontoEstimado'] > 0) & (data['unidad_format'] > 0)]

    # crear el scatter plot
    fig_scatter = px.scatter(
        df_validos,
        x='unidad_format',
        y='MontoEstimado',
        hover_data=['NombreLicitacion', 'Organismo', 'Categoria'],
        title='Scatterplot',
        labels={
            'unidad_format': 'Duración del contrato (días)',
            'MontoEstimado': 'Monto Estimado (CLP)'
        }
    )
    fig_scatter.update_layout(template='plotly_white')
    
    
    # Gráfico 5: Distribución de tipo de licitaciones
    
    data_pie = data.copy()
    # añadir condicionales de toggle
    # graficar toggle por grupo
    if tipo_toggle == "grupo":
        def clasificar_tipo(codigo):
            if codigo in ["L1", "LE", "LP", "LQ", "LR", "LS"]:
                return "Público"
            elif codigo in ["E2", "CO", "B2", "H2", "I2"]:
                return "Privado"
            else:
                return "Otro"
    
        data_pie["Grupo"] = data_pie["Tipo"].apply(clasificar_tipo)
        conteo_grupo = data_pie["Grupo"].value_counts().reset_index()
        conteo_grupo.columns = ["Grupo", "Cantidad"]
        fig_pie = px.pie(
            conteo_grupo,
            names="Grupo",
            values="Cantidad",
            title="Distribución de Licitaciones: Público vs Privado",
            hole=0.4
        )
    # graficar toggle por tipo de licitación privada
    elif tipo_toggle == "privado":
        privados = ["E2", "CO", "B2", "H2", "I2"]
        data_pie = data_pie[data_pie["Tipo"].isin(privados)]
        data_pie["Tipo_desc"] = data_pie["Tipo"].map(tipo_map).fillna("Otro")
        conteo_tipos = data_pie["Tipo_desc"].value_counts().reset_index()
        conteo_tipos.columns = ["Tipo_desc", "Cantidad"]
    
        fig_pie = px.pie(
            conteo_tipos,
            names="Tipo_desc",
            values="Cantidad",
            title="Distribución de Licitaciones Privadas",
            hole=0.4
        )
    # graficar toggle por tipo de licitación pública
    elif tipo_toggle == "publico":
        publicos = ["L1", "LE", "LP", "LQ", "LR", "LS"]
        data_pie = data_pie[data_pie["Tipo"].isin(publicos)]
        data_pie["Tipo_desc"] = data_pie["Tipo"].map(tipo_map).fillna("Otro")
        conteo_tipos = data_pie["Tipo_desc"].value_counts().reset_index()
        conteo_tipos.columns = ["Tipo_desc", "Cantidad"]
    
        fig_pie = px.pie(
            conteo_tipos,
            names="Tipo_desc",
            values="Cantidad",
            title="Distribución de Licitaciones Públicas",
            hole=0.4
        )
    fig_pie.update_layout(template='plotly_white')

    # Gráfico 6: Mapa de monto estimado por región en Chile
    # limpieza
    data_map["Region"] = data_map["Region"].str.strip()
    data_map["Organismo"] = data_map["Organismo"].str.strip()
    data_map = data_map.dropna(subset=['Region', 'MontoEstimado'])

    # fecha a nivel mes para series temporales
    data_map["MesPublicacion"] = data_map["FechaPublicacion"].dt.to_period("M").dt.to_timestamp()  
    # mapear regiones con nombre en geojson
    data_map["Region"] = data_map["Region"].map(mapeo_regiones).fillna(data_map["Region"])


    # agrupar datos por región y sumar monto
    data_map_html = data_map.groupby("Region", as_index=False)["MontoEstimado"].sum()
    
    # normalizar
    data_map_html["Region"] = data_map_html["Region"].astype(str)
    data_map_html["Region"] = data_map_html["Region"].str.strip()
    data_map_html["NOMBRE"] = data_map_html["Region"]  # copiar la columna con el nombre correcto
    # graficar
    fig_mapbox = px.choropleth_mapbox(
        data_map_html,
        geojson=chile_geojson,
        locations="Region",              # debe coincidir con feature.properties.Region del geojson
        featureidkey="properties.Region",  # este es el campo dentro del geojson
        color="MontoEstimado",
        color_continuous_scale="YlGnBu",
        range_color=(data_map_html["MontoEstimado"].min(), data_map_html["MontoEstimado"].max()),
        mapbox_style="carto-positron",
        center={"lat": -35.6751, "lon": -71.5430},
        zoom=4.5,
        opacity=0.7,
        labels={"ColorValue": "Monto estimado (escala 0-100)"}
    )
    
    fig_mapbox.update_layout(
        margin={"r":0,"t":30,"l":0,"b":0}
    )
    # retornar gráficos para mostrar en dashboard
    return fig_region, fig_monto, fig_licitaciones,fig_scatter,fig_pie,fig_mapbox


# main, ejecutar código
if __name__ == "__main__":
    app.run(debug=True, port=8051)

