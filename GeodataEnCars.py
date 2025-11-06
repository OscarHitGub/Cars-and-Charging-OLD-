import pandas as pd
import numpy as np 
import requests
import plotly.express as px
import folium
#from ipywidgets import interact, Dropdown
from folium.plugins import MarkerCluster
import streamlit as st
import re
from streamlit_folium import st_folium
#import numpy as np
import plotly.graph_objects as go

# --- Data inladen ---
@st.cache_data
def load_data():
    cars = pd.read_pickle('cars.pkl')
    cars['datum_eerste_toelating'] = pd.to_datetime(cars['datum_eerste_toelating'], errors='coerce')
    cars['jaar_maand'] = cars['datum_eerste_toelating'].dt.to_period('M').astype(str)
    return cars

cars = load_data()

def car_data():
    st.title("🚗 Auto Dashboard")

    # --- Totale aantallen per merk ---
    totaal_per_merk = cars.groupby('merk').size().sort_values(ascending=False)
    top5 = totaal_per_merk.nlargest(5).index
    top10 = totaal_per_merk.nlargest(10).index

    autos_per_merk_per_maand = (
        cars.groupby(['jaar_maand', 'merk'])
            .size()
            .reset_index(name='aantal_autos')
    )

    # --- Normalisatie-functie voor model ---
    def normalize_model(name):
        if pd.isna(name):
            return None
        name = name.upper().strip()
        match = re.match(r'(MODEL [A-Z0-9]+)', name)
        if match:
            return match.group(1)
        match = re.match(r'(ID\.?\s*\d)', name)
        if match:
            return match.group(1).replace(' ', '').upper()
        match = re.match(r'(E[-\s]?\d+)', name)
        if match:
            return match.group(1).replace(' ', '').upper()
        return name.split()[0]

    cars['model_basis'] = cars['handelsbenaming'].apply(normalize_model)

    # --- Functies voor grafieken ---
    def plot_top_merks(top_labels, titel):
        filtered = autos_per_merk_per_maand[autos_per_merk_per_maand['merk'].isin(top_labels)]
        fig = px.scatter(
            filtered,
            x='jaar_maand',
            y='aantal_autos',
            color='merk',
            title=titel,
        )
        fig.update_traces(mode='lines+markers', marker=dict(size=6, opacity=0.7), line=dict(width=0.5))
        fig.update_layout(template='plotly_white', xaxis=dict(categoryorder='category ascending'), 
                          xaxis_title='Maand', yaxis_title='Aantal auto\'s')
        st.plotly_chart(fig, use_container_width=True)

    def plot_merk_trends(merknaam):
        merk_df = cars[cars['merk'].str.upper() == merknaam.upper()]
        if merk_df.empty:
            st.warning(f"⚠️ Geen resultaten gevonden voor merk: {merknaam}")
            return

        per_model_per_maand = (
            merk_df.groupby(['jaar_maand', 'model_basis'])
                .size()
                .reset_index(name='aantal_autos')
        )

        fig = px.scatter(
            per_model_per_maand,
            x='jaar_maand',
            y='aantal_autos',
            color='model_basis',
            title=f"Aantal auto's per model van {merknaam} door de maanden heen",
        )
        fig.update_traces(mode='lines+markers', marker=dict(size=6, opacity=0.7), line=dict(width=0.5))
        fig.update_layout(template='plotly_white', xaxis=dict(categoryorder='category ascending'),
                          xaxis_title='Maand', yaxis_title='Aantal auto\'s')
        st.plotly_chart(fig, use_container_width=True)

    # --- Keuze tussen Top 5 / 10 ---
    keuze = st.radio(
        "📊 Kies welke merken te tonen:",
        ["Top 5 merken", "Top 10 merken"],
        horizontal=True
    )

    if keuze == "Top 5 merken":
        plot_top_merks(top5, "📈 Aantal auto's per merk (Top 5) door de maanden heen")
    else:
        plot_top_merks(top10, "📈 Aantal auto's per merk (Top 10) door de maanden heen")

    # --- Modeltrends sectie ---
    st.markdown("---")
    st.markdown("### 🔍 Modeltrends per merk")

    merk_opties = sorted(cars['merk'].dropna().unique())
    merk_naam = st.selectbox("Selecteer een merk om modeltrends te bekijken:", merk_opties, index=0)
    plot_merk_trends(merk_naam)

    # --- Extra visualisatie: Inrichting ---
    st.markdown("---")
    st.markdown("### 🚘 Aantal auto's per inrichting (carrosserie)")

    # ✅ Checkbox voor log-schaal
    log_scale = st.checkbox("Logaritmische schaal gebruiken", value=True)

    fig_inrichting = px.histogram(
        cars,
        x='inrichting',
        color='inrichting',
        title="Aantal auto’s per inrichting",
        log_y=log_scale
    )
    fig_inrichting.update_layout(
        xaxis_title='Carrosserie',
        yaxis_title="Aantal auto's (log)" if log_scale else "Aantal auto's",
        template='plotly_white'
    )
    st.plotly_chart(fig_inrichting, use_container_width=True)

    # Breedte en lengte naar numeriek
    cars['breedte'] = pd.to_numeric(cars['breedte'], errors='coerce')
    cars['lengte'] = pd.to_numeric(cars['lengte'], errors='coerce')

    # Filter geldige rijen
    cars_filtered = cars[(cars['breedte'] > 0) & (cars['lengte'] > 0)]
    cars_sorted = cars_filtered.sort_values(by=['breedte', 'lengte'])

    # Bereken trendline met numpy
    x = cars_sorted['breedte'].values
    y = cars_sorted['lengte'].values
    coeffs = np.polyfit(x, y, 1)  # lineaire fit
    trendline = np.polyval(coeffs, x)

    st.markdown("---")
    st.markdown("### 🚘 Vergelijking lengte en breedte van auto's")

    # Maak scatterplot
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode='markers', name='Auto\'s'))
    fig.add_trace(go.Scatter(x=x, y=trendline, mode='lines', name='Trendline', line=dict(color='red')))

    fig.update_layout(
        title="Lengte vs Breedte van auto's",
        xaxis_title='Breedte',
        yaxis_title='Lengte'
    )

    st.plotly_chart(fig, use_container_width=True)

def lp_map():
    data_openchargemap = requests.get("https://api.openchargemap.io/v3/poi/?output=json&countrycode=NL&maxresults=10000&compact=true&verbose=false&key=5d087822-ce71-42b0-a231-67209f0900a2")

    Laadpalen = pd.json_normalize(data_openchargemap.json())

    df = pd.json_normalize(Laadpalen.Connections)
    df2 = pd.json_normalize(df[0])
    Laadpalen = pd.concat([Laadpalen, df2], axis=1)

    st.markdown("Bekijk de locaties van laadpalen in Nederland, gefilterd per provincie.")


    # 📍 Coördinaten van provincies
    provincie_locaties = {
        "Alle provincies": {"center": [52.2129919, 5.2793703], "zoom": 7},   # Midden Nederland
        "Groningen": {"center": [53.2194, 6.5665], "zoom": 10},
        "Friesland": {"center": [53.1642, 5.7818], "zoom": 10},
        "Drenthe": {"center": [52.9480, 6.6231], "zoom": 10},
        "Overijssel": {"center": [52.4380, 6.5010], "zoom": 10},
        "Flevoland": {"center": [52.5279, 5.5953], "zoom": 10},
        "Gelderland": {"center": [52.0452, 5.8718], "zoom": 10},
        "Utrecht": {"center": [52.0907, 5.1214], "zoom": 11},
        "Noord-Holland": {"center": [52.5200, 4.7885], "zoom": 9},
        "Zuid-Holland": {"center": [51.9961, 4.5597], "zoom": 10},
        "Zeeland": {"center": [51.4940, 3.8490], "zoom": 10},
        "Noord-Brabant": {"center": [51.4827, 5.2322], "zoom":10},
        "Limburg": {"center": [51.4427, 6.0600], "zoom": 9}
    }

    # Filter de Laadpalen DataFrame op geldige coördinaten
    Laadpaal_locatie = Laadpalen[[
        "AddressInfo.AddressLine1",
        "AddressInfo.Latitude",
        "AddressInfo.Longitude",
        "PowerKW"
    ]].dropna(subset=["AddressInfo.Latitude", "AddressInfo.Longitude"])

    # Dropdown voor provincies
    provincie = st.selectbox(
        "📍 Kies een provincie:",
        options=list(provincie_locaties.keys()),
        index=0
    )

    # Kaart functie
    def maak_kaart(provincie):
        loc = provincie_locaties.get(provincie, provincie_locaties["Alle provincies"])
        m = folium.Map(location=loc["center"], zoom_start=loc["zoom"], tiles="CartoDB positron")

        cluster = MarkerCluster().add_to(m)

        # Voeg alle laadpalen toe
        for _, r in Laadpaal_locatie.iterrows():
            folium.CircleMarker(
                location=[r["AddressInfo.Latitude"], r["AddressInfo.Longitude"]],
                radius=3,
                color="blue",
                fill=True,
                fill_opacity=0.7,
                popup=f"{r['AddressInfo.AddressLine1']}<br>Vermogen: {r['PowerKW']} kW"
            ).add_to(cluster)

        return m

    # Toon kaart in Streamlit
    m = maak_kaart(provincie)
    st_folium(m, width=1200, height=700)
