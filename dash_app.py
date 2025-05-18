import os
import dash
from dash import dcc, html
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go

# ------------------------
# 1) Crear app y exponer el servidor WSGI
# ------------------------
app = dash.Dash(__name__)
server = app.server

# ------------------------
# 2) Leer datos
# ------------------------
BASE_DIR = os.path.dirname(__file__)

# Leer Parquet
parquet_path = os.path.join(BASE_DIR, 'final_dataframe.parquet')
df = pd.read_parquet(parquet_path, engine='pyarrow')

# Cargar GeoJSON
geojson_path = os.path.join(BASE_DIR, 'colombia_departamentos.geojson')
with open(geojson_path, 'r', encoding='utf-8') as f:
    departamentos_geo = json.load(f)

# ------------------------
# 3) Filtrar año 2019
# ------------------------
df_2019 = df[df['AÑO'] == 2019]

# ------------------------
# 4) Generar figuras
# ------------------------

# 4.1 Mapa: muertes totales por Departamento
dept_counts = (
    df_2019
    .groupby('DEPARTAMENTO')
    .size()
    .reset_index(name='Muertes')
)
fig_map = px.choropleth(
    dept_counts,
    geojson=departamentos_geo,
    locations='DEPARTAMENTO',
    featureidkey='properties.NOMBRE_DPT',
    color='Muertes',
    title='Muertes Totales por Departamento (2019)',
    labels={'Muertes': 'Número de Muertes'},
    color_continuous_scale='Reds',
    template='plotly_white'
)
fig_map.update_geos(fitbounds="locations", visible=False)

# 4.2 Línea: muertes por mes
monthly = df_2019.groupby('MES').size().reset_index(name='Muertes')
fig_line = px.line(
    monthly, x='MES', y='Muertes',
    title='Muertes por Mes (2019)',
    labels={'MES': 'Mes', 'Muertes': 'Número de Muertes'},
    template='plotly_white'
)
fig_line.update_xaxes(dtick=1)

# 4.3 Top 5 ciudades más violentas (homicidio)
df_hom = df_2019[df_2019['MANERA_MUERTE'] == 'Homicidio']
top5_hom = (
    df_hom
    .groupby('MUNICIPIO')
    .size()
    .reset_index(name='Homicidios')
    .nlargest(5, 'Homicidios')
)
fig_bar = px.bar(
    top5_hom, x='MUNICIPIO', y='Homicidios',
    title='Top 5 Ciudades Más Violentas (Homicidio)',
    labels={'MUNICIPIO': 'Ciudad', 'Homicidios': 'Número de Homicidios'},
    template='plotly_white'
)

# 4.4 Pie: 10 ciudades con menor mortalidad
city_counts = df_2019.groupby('MUNICIPIO').size().reset_index(name='Muertes')
bottom10 = city_counts.nsmallest(10, 'Muertes')
fig_pie = px.pie(
    bottom10, names='MUNICIPIO', values='Muertes',
    title='10 Ciudades con Menor Mortalidad',
    template='plotly_white', hole=.3
)
fig_pie.update_traces(textinfo='label+percent', textposition='inside')

# 4.5 Tabla: Top 10 causas de muerte
causes = (
    df_2019
    .groupby(['COD_MUERTE', 'Descripción CIE-10'])
    .size()
    .reset_index(name='Total')
    .sort_values('Total', ascending=False)
    .head(10)
)
fig_table = go.Figure(data=[go.Table(
    header=dict(values=['Código CIE-10', 'Descripción CIE-10', 'Total'], fill_color='lightgrey'),
    cells=dict(values=[causes['COD_MUERTE'], causes['Descripción CIE-10'], causes['Total']])
)])
fig_table.update_layout(title='Top 10 Causas de Muerte', template='plotly_white')

# 4.6 Histograma: distribución por edad quinquenal
age_labels = {i: f"{(i-1)*5}-{(i-1)*5+4}" for i in range(1, 18)}
age_labels[18] = '85+'
age_counts = (
    df_2019
    .groupby('GRUPO_EDAD1')
    .size()
    .reset_index(name='Muertes')
)
age_counts['Rango de Edad'] = age_counts['GRUPO_EDAD1'].map(age_labels)
fig_hist = px.bar(
    age_counts, x='Rango de Edad', y='Muertes',
    title='Distribución de Muertes por Edad Quinquenal',
    labels={'Muertes': 'Número de Muertes'},
    template='plotly_white'
)

# 4.7 Barras apiladas: Sexo vs Departamento
sex_dep = (
    df_2019
    .groupby(['DEPARTAMENTO', 'SEXO'])
    .size()
    .reset_index(name='Muertes')
)
fig_stack = px.bar(
    sex_dep, x='DEPARTAMENTO', y='Muertes', color='SEXO',
    title='Muertes por Sexo y Departamento',
    labels={'DEPARTAMENTO': 'Departamento', 'Muertes': 'Número de Muertes'},
    template='plotly_white'
)

# ------------------------
# 5) Definir layout de la app
# ------------------------
app.layout = html.Div([
    html.H1('Dashboard Mortalidad 2019 – Colombia', style={'textAlign': 'center'}),
    dcc.Graph(figure=fig_map),
    dcc.Graph(figure=fig_line),
    dcc.Graph(figure=fig_bar),
    dcc.Graph(figure=fig_pie),
    dcc.Graph(figure=fig_table),
    dcc.Graph(figure=fig_hist),
    dcc.Graph(figure=fig_stack)
], style={'maxWidth': '1200px', 'margin': 'auto'})

# ------------------------
# 6) Ejecutar la app en local (no influye en producción con Gunicorn)
# ------------------------
if __name__ == '__main__':
    app.run_server(debug=True)
