# App to interactively view lineplots of Energy Access data from the World Bank's MTF Surveys
# This app has three widgets:
# - LDAS variable selector     [Dropdown]
# - District (ubigeo) selector [Dropdown]
# - Offset value               [Slider]

#%%Import packages
#Import packages
import scipy
import pandas as pd
import geopandas as gpd
from pathlib import Path
import json
import matplotlib.pyplot as plt
from shinywidgets import output_widget, render_widget
import ipyleaflet
from branca.colormap import linear
from shiny import ui, render, App, reactive
import matplotlib

#%%Setting base paths
base_path = Path(__file__).parent.parent.parent
data1_path = base_path / "Data" / "Processed" / "Subdivision1_Summary.csv"
data2_path = base_path / "Data" / "Processed" / "Subdivision2_Summary.csv"
country_path = base_path / "Data" / "Raw" / "CountryMaps"

#Reading in Subdivision 2 data
Sub1_df = pd.read_csv(data1_path)
Sub2_df = pd.read_csv(data2_path)

#Reading in coutnry geodatabases
KEN = gpd.read_file(country_path / "gadm41_KEN_2.json")
LBR = gpd.read_file(country_path / "gadm41_LBR_1.json")
NER = gpd.read_file(country_path / "gadm41_NER_2.json")
RWA = gpd.read_file(country_path / "gadm41_RWA_2.json")
ZMB = gpd.read_file(country_path / "gadm41_ZMB_1.json")

#%% Wrangling Kenya
KEN_data = Sub2_df[Sub2_df["Country"] == "Kenya"]

KEN = KEN.dissolve(
    by = 'NAME_1'
)

KEN_gdf = KEN.merge(
    KEN_data, 
    left_on='NAME_1', 
    right_on='Subdivision2', 
    how='left'
)

#KEN_gdf.head()


#%% Wrangling Liberia
LBR_data = Sub1_df[Sub1_df["Country"] == "Liberia"]
#print(LBR_data['Subdivision1'].unique())

LBR = LBR.dissolve(
    by = 'NAME_1'
)

LBR_gdf = LBR.merge(
    LBR_data, 
    left_on='NAME_1', 
    right_on='Subdivision1', 
    how='left'
)
#LBR_gdf.info()
#LBR_gdf.head()

#%% Wrangling Niger
import unicodedata


def remove_accents(text):
  if isinstance(text, str):
    nfkd_form = unicodedata.normalize('NFKD', text)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])
  return text

NER['NAME_2'] = NER['NAME_2'].apply(remove_accents)
NER_data = Sub2_df[Sub2_df["Country"] == "Niger"]

NER = NER.dissolve(
    by = 'NAME_2'
)

NER_gdf = NER.merge(
    NER_data, 
    left_on='NAME_2', 
    right_on='Subdivision2', 
    how='left'
)
#NER_gdf.head()



#%% Wrangling Rwanda
RWA_data = Sub2_df[Sub2_df["Country"] == "Rwanda"]

RWA = RWA.dissolve(
    by = 'NAME_2'
)

RWA_gdf = RWA.merge(
    RWA_data, 
    left_on='NAME_2', 
    right_on='Subdivision2', 
    how='left'
)
#RWA_gdf.head(20)

#%% Wrangling Zambia

ZMB_data = Sub1_df[Sub1_df["Country"] == "Zambia"]

ZMB = ZMB.dissolve(
    by = 'NAME_1'
)

ZMB_gdf = ZMB.merge(
    ZMB_data, 
    left_on='NAME_1', 
    right_on='Subdivision1', 
    how='left'
)
#ZMB_gdf.head(20)

#AI USE DISCLAIMER: The code following here was written with the assistance of AI and code provided by John Fay.

#%% Bringing it together
country_gdfs = {
    "Kenya": KEN_gdf,
    "Liberia": LBR_gdf,
    "Niger": NER_gdf,
    "Rwanda": RWA_gdf,
    "Zambia": ZMB_gdf,
}

# 2. Define the User Interface
app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select(
            "country",
            "Select Country:",
            choices=list(country_gdfs.keys()),
        ),
        ui.input_select(
            "variable",
            "Select Variable of Interest:",
            choices=[],
        ),
    ),
    ui.card(
        ui.card_header("Country Dashboard"),
        ui.output_ui("map_output"),
    ),
    title="MTF Data Dashboard",
)

# 3. Define the Server Logic
def server(input, output, session):
    # Reactive calculation to fetch the currently selected GeoDataFrame
    @reactive.calc
    def selected_gdf():
        return country_gdfs[input.country()]

    # Automatically update variable choices when the selected country changes
    @reactive.effect
    def _update_variables():
        gdf = selected_gdf()
        # Filter for numeric columns (exclude geometry and text IDs)
        numeric_cols = gdf.select_dtypes(include="number").columns.tolist()
        ui.update_select("variable", choices=numeric_cols)

    # Render the interactive map
    @render.ui
    def map_output():
        gdf = selected_gdf()
        var = input.variable()

        # Prevent rendering before the variable dropdown finishes updating
        if not var or var not in gdf.columns:
            return ui.p("Loading map...")

        # Ensure CRS is WGS84 (EPSG:4326) for web map tiles
        if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)

        # Generate an interactive Folium map using GeoPandas .explore()
        m = gdf.explore(
            column=var,
            cmap="viridis",
            legend=True,
            tooltip=True,
            tiles="OpenStreetMap",
        )

        # Convert the Folium map object into HTML for Shiny
        return ui.HTML(m._repr_html_())

app = App(app_ui, server)