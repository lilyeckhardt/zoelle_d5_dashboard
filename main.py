import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
import csv

tract_df = pd.read_csv("tracts_df.csv")

#CO and larimer fips codes
state = "08"
county = "069"

gdf_tracts = gpd.read_file("tract.geojson")

# specifying larimer county
gdf_tracts = gdf_tracts[(gdf_tracts["STATEFP"]=="08") & (gdf_tracts["COUNTYFP"]=="069")]


# padding tract and bg keys with zeroes to properly compare with original geo dataframe
gdf_tracts["TRACTCE"] = gdf_tracts["TRACTCE"].astype(str).str.zfill(6)


target = {
    "002300": ["2"],               # Tract 23, BG 2
    "000505": ["2"],               # Tract 5.05, BG 2
    "000504": ["1"],               # Tract 5.04, BG 1
    "000600": ["*"],               # Tract 6, all BGs
    "000700": ["2"],               # Tract 7, BG 2
    "000901": ["1", "3", "4"],     # Tract 9.01, BGs 1,3,4
    "001104": ["*"],               # Tract 11.04, all BGs
    "001110": ["*"],               # Tract 11.10, all BGs
    "001111": ["*"],               # Tract 11.11, all BGs
}

tracts_filtered = gdf_tracts[gdf_tracts["TRACTCE"].isin(target.keys())].copy()

tract_df = tract_df.rename(columns={"tract": "TRACTCE"})
tract_df["TRACTCE"] = tract_df["TRACTCE"].astype(str).str.zfill(6)
tracts_merged = tracts_filtered.merge(
    tract_df,
    on="TRACTCE",
    how="left"
)

tracts_web_mercator = tracts_merged.to_crs(epsg=3857)


st.set_page_config(
    page_title="District 5 Importance Map",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("District 5 Importance Map")

st.write("""
Adjust the sliders to favor certain demographics over others.
        Areas with many people within the favored demographics
         will appear more red, and areas with few will appear more blue.\n

""")

st.write("""
When adjusting the sliders, you can think of a 0 representing
         a group that you would not want to canvass at all
         and a 10 representing a group you want to reach as much
         as possible.\n

""")
st.write("""
When you are ready to generate the map, click "Update Map" 
         at the bottom. NOTE: The app takes a few seconds to generate
         the map.

""")

col1, col2 = st.columns([0.5, 0.5])

with col1:
    st.header("Adjust Weights")

    with st.form(key="weight_form"):
        population_weight = st.slider("Population of Tract", 0, 10, 2)
        income_weight = st.slider("Standardized Median Household Income", 0, 10, 1)
        bachelors_weight = st.slider("Percent Bachelors or Higher", 0, 10, 9)
        pct_owned_weight = st.slider("Percent Homeowners", 0, 10, 1)
        pct_rented_weight = st.slider("Percent Renters", 0, 10, 10)
        pct_18_24_weight = st.slider("Percent Aged 18-24", 0, 10, 1)
        pct_25_34_weight = st.slider("Percent Aged 25-34", 0, 10, 10)
        pct_35_44_weight = st.slider("Percent Aged 35-44", 0, 10, 7)
        pct_45_66_weight = st.slider("Percent Aged 45-66", 0, 10, 1)
        pct_67_plus_weight = st.slider("Percent Aged 67+", 0, 10, 3)

        submit_button = st.form_submit_button(label="Update Map")

if submit_button:

    tracts_web_mercator["median_household_income_scaled"] = (
        (tracts_web_mercator["median_household_income"] - tracts_web_mercator["median_household_income"].min()) /
        (tracts_web_mercator["median_household_income"].max() - tracts_web_mercator["median_household_income"].min())
    ) * 100

    tracts_web_mercator["population_scaled"] = (
        (tracts_web_mercator["population"] - tracts_web_mercator["population"].min()) /
        (tracts_web_mercator["population"].max() - tracts_web_mercator["population"].min())
    ) * 100

    weights = {
        "population_scaled": population_weight,
        "median_household_income_scaled": income_weight,
        "pct_bachelors_or_higher": bachelors_weight,
        "pct_owned": pct_owned_weight,
        "pct_rented": pct_rented_weight,
        "pct_18-24": pct_18_24_weight,
        "pct_25-34": pct_25_34_weight,
        "pct_35-44": pct_35_44_weight,
        "pct_45-66": pct_45_66_weight,
        "pct_67+": pct_67_plus_weight
    }

    total_w = sum(weights.values())
    weights = {k: v / total_w for k, v in weights.items()}

    tracts_web_mercator["importance_score"] = sum(
        tracts_web_mercator[feat] * w for feat, w in weights.items()
    )

    with col2:
        fig, ax = plt.subplots(figsize=(12, 10))
        tracts_web_mercator.plot(column="importance_score",
                                 legend=True,
                                 cmap="coolwarm",
                                 alpha=0.7,
                                 ax=ax)
        ax.set_title("Importance Score by Census Tract", fontsize=16)
        ax.set_axis_off()
        ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik,
                        zoom=13, crs=tracts_web_mercator.crs.to_string())
        st.pyplot(fig)