import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from sklearn.preprocessing import MinMaxScaler

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
    page_title="District 5 Importance Index Map",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("District 5 Importance Index")

st.write("""
Adjust the sliders to favor certain demographics over others.
        Areas with many people within the favored demographics
         will appear more red, and areas with few will appear more blue.\n

""")

st.write("""
When adjusting the sliders, you can think of a 0 representing
         a group that you would not want to canvass at all
         and a 1 representing a group you want to reach as much
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
        population_weight = st.slider("Population of Tract", 0.0, 1.0, 0.5)
        income_weight = st.slider("Standardized Median Household Income", 0.0, 1.0, 0.5)
        bachelors_weight = st.slider("Percent Bachelors or Higher", 0.0, 1.0, 0.5)
        pct_owned_weight = st.slider("Percent Homeowners", 0.0, 1.0, 0.5)
        pct_rented_weight = st.slider("Percent Renters", 0.0, 1.0, 0.5)
        pct_18_24_weight = st.slider("Percent Aged 18-24", 0.0, 1.0, 0.5)
        pct_25_34_weight = st.slider("Percent Aged 25-34", 0.0, 1.0, 0.5)
        pct_35_44_weight = st.slider("Percent Aged 35-44", 0.0, 1.0, 0.5)
        pct_45_66_weight = st.slider("Percent Aged 45-66", 0.0, 1.0, 0.5)
        pct_67_plus_weight = st.slider("Percent Aged 67+", 0.0, 1.0, 0.5)

        submit_button = st.form_submit_button(label="Update Map")

if submit_button:

    quant_cols = [
        "population",
        "median_household_income",
        "pct_bachelors_or_higher",
        "pct_owned",
        "pct_rented",
        "pct_18-24",
        "pct_25-34",
        "pct_35-44",
        "pct_45-66",
        "pct_67+",
    ]
    qual_cols = [c for c in tracts_web_mercator.columns if c not in quant_cols]

    scaler = MinMaxScaler(feature_range=(0, 1))
    df_scaled = pd.DataFrame(scaler.fit_transform(tracts_web_mercator[quant_cols]), columns=quant_cols)
    df_scaled = pd.merge(tracts_web_mercator[qual_cols], df_scaled, left_index=True, right_index=True)

    weights = {
        "population": population_weight,
        "median_household_income": income_weight,
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

    for col, w in weights.items():
        df_scaled[col] = df_scaled[col] * w

    df_scaled["importance_index"] = df_scaled[quant_cols].sum(axis=1)
    st.session_state["df_scaled"] = df_scaled

    if "df_scaled" in st.session_state:
        with col2:
                fig, ax = plt.subplots(figsize=(12, 10))
                df_scaled.plot(column="importance_index",
                       legend=True,
                       cmap="coolwarm",
                       alpha=0.7,
                       ax=ax)
                ax.set_title("Importance Index by Census Tract", fontsize=16)
                ax.set_axis_off()
                ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik,
                        zoom=13, crs=df_scaled.crs.to_string())
                st.pyplot(fig)