import streamlit as st  
import pandas as pd
import pydeck as pdk
import os
from datetime import datetime

# Set Page Configuration
st.set_page_config(
    page_title="Earthquake Visualization - Philippines",
    page_icon="🌍",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #FF4B4B;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: 500;
        color: #888888;
        margin-bottom: 2rem;
    }
    .stats-card {
        background-color: rgba(255, 75, 75, 0.1);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
    }
    .highlight-text {
        color: #FF4B4B;
        font-weight: 600;
    }
    .map-container {
        border-radius: 0px;
        border: none;
        padding: 0px;
        background-color: transparent;
    }
</style>
""", unsafe_allow_html=True)

# Create main layout
header_col1, header_col2 = st.columns([3, 1])

with header_col2:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    st.markdown(f"<div style='text-align: right;'>Last updated: {current_time}</div>", unsafe_allow_html=True)

st.markdown(
    """
    <h1 class='main-header'>🌍 Earthquake Mapping in the Philippines</h1>
    <p class='sub-header'>
        Interactive visualization of seismic activity across the Philippine archipelago
    </p>
    <div class='description'>
        Explore historical earthquake data with customizable metrics, time-based filters, and geographic analysis tools. 
        This dashboard helps identify patterns and high-risk zones through dynamic mapping and statistical visualization.
    </div>
    """, unsafe_allow_html=True
)

# Load Earthquake Data from Uploaded File
@st.cache_data
def load_data():
    file_path = r"merged_output.csv"

    if not os.path.exists(file_path):
        st.error(f"File not found at path: {file_path}. Please check your file location.")
        return None, None

    df_full = pd.read_csv(file_path)
    df = df_full.copy()

    df.columns = df.columns.str.strip().str.upper()

    required_columns = {"LATITUDE", "LONGITUDE", "DEPTH (KM)", "MAGNITUDE", "TIME"}
    if not required_columns.issubset(df.columns):
        st.error(f"Missing required columns: {required_columns - set(df.columns)}")
        return None, None

    df["LATITUDE"] = pd.to_numeric(df["LATITUDE"], errors="coerce")
    df["LONGITUDE"] = pd.to_numeric(df["LONGITUDE"], errors="coerce")
    df["DEPTH (KM)"] = pd.to_numeric(df["DEPTH (KM)"], errors="coerce")
    df["MAGNITUDE"] = pd.to_numeric(df["MAGNITUDE"], errors="coerce")
    df["TIME"] = pd.to_datetime(df["TIME"], errors="coerce")

    df["DEPTH (KM)"] = -df["DEPTH (KM)"]
    df = df.dropna(subset=["LATITUDE", "LONGITUDE", "DEPTH (KM)", "MAGNITUDE", "TIME"])

    return df, df_full

# Load data
with st.spinner("Loading earthquake data..."):
    df, df_full = load_data()
    
if df is None or df_full is None:
    st.stop()

# Add data sampling controls
st.sidebar.markdown("""
<div style='margin-top: 20px; padding: 10px; background-color: rgba(255, 255, 0, 0.1); border-radius: 5px;'>
    <h4 style='color: #FF9800;'>⚠️ Performance Settings</h4>
    <p style='font-size: 0.8em; color: #888888;'>Adjust these settings if you experience performance issues</p>
</div>
""", unsafe_allow_html=True)

use_data_sampling = st.sidebar.checkbox("Enable data sampling", value=True, 
                                       help="Reduces data size to improve performance")

if use_data_sampling:
    max_points = st.sidebar.slider("Maximum data points", 
                                 min_value=100, 
                                 max_value=100000, 
                                 value=2000, 
                                 step=100,
                                 help="Lower values improve performance")
    
    # Apply sampling to the main dataframe if needed
    if len(df) > max_points:
        # Stratified sampling by province to maintain representativeness
        sampled_df = pd.DataFrame()
        provinces = df["PROVINCE"].dropna().unique()
        
        # Calculate points per province
        points_per_province = max(5, int(max_points / len(provinces)))
        
        for province in provinces:
            province_data = df[df["PROVINCE"] == province]
            if len(province_data) > points_per_province:
                # Sample from each province
                province_sample = province_data.sample(n=points_per_province, random_state=42)
                sampled_df = pd.concat([sampled_df, province_sample])
            else:
                # If province has fewer points than allocated, take all
                sampled_df = pd.concat([sampled_df, province_data])
        
        # If we still have too many points, take a random sample
        if len(sampled_df) > max_points:
            sampled_df = sampled_df.sample(n=max_points, random_state=42)
            
        # Use the sampled dataframe
        df = sampled_df
else:
    # Warn if data is very large
    if len(df) > 10000:
        pass

# ✅ Sort Data by Time (Oldest to Newest)
df = df.sort_values("TIME")

# ✅ Create Next Event Connections
df["NEXT_LAT"] = df["LATITUDE"].shift(-1)
df["NEXT_LON"] = df["LONGITUDE"].shift(-1)
df["NEXT_TIME"] = df["TIME"].shift(-1)

# ✅ Compute Time Difference (Hours) Between Earthquakes
df["TIME_DIFF_HOURS"] = (df["NEXT_TIME"] - df["TIME"]).dt.total_seconds() / 3600  # Convert to hours

# ✅ Remove Last Row (Since It Has No Next Earthquake)
df = df.dropna(subset=["NEXT_LAT", "NEXT_LON", "NEXT_TIME", "TIME_DIFF_HOURS"])

# 🎨 Define Arc Colors Based on Time Difference
def get_color(interval):
    if interval < 1:
        return [255, 0, 0, 200]  # Green (Less than 1 hour)

df["COLOR"] = df["TIME_DIFF_HOURS"].apply(get_color)

# Add this after the get_color function
def get_magnitude_color(magnitude):
    # Color scheme based on magnitude ranges
    if magnitude < 1:
        return [255, 255, 255, 180]  # White for barely perceptible
    elif magnitude < 2:
        return [200, 200, 200, 180]  # Light gray for scarcely perceptible
    elif magnitude < 3:
        return [173, 216, 230, 180]  # Light blue for weak
    elif magnitude < 4:
        return [0, 255, 255, 180]  # Cyan for moderately strong
    elif magnitude < 5:
        return [0, 255, 0, 180]  # Green for strong
    elif magnitude < 6:
        return [255, 255, 0, 180]  # Yellow for very strong
    elif magnitude < 7:
        return [255, 165, 0, 180]  # Orange for destructive
    elif magnitude < 8:
        return [255, 69, 0, 180]  # Red-Orange for very destructive
    elif magnitude < 9:
        return [255, 0, 0, 180]  # Red for devastating
    else:
        return [139, 0, 0, 180]  # Dark red for completely devastating

# 🎛 Sidebar Filters
st.sidebar.markdown("<div style='background-color: rgba(255, 75, 75, 0.1); padding: 10px; border-radius: 5px;'><h3>📊 Data Filters</h3></div>", unsafe_allow_html=True)

# Magnitude Filter
st.sidebar.subheader("🔍 Filter by MAGNITUDE")
min_mag, max_mag = df["MAGNITUDE"].min(), df["MAGNITUDE"].max()
selected_mag = st.sidebar.slider("MAGNITUDE Range", min_mag, max_mag, (min_mag, max_mag))

# Province Filter
st.sidebar.markdown("""
<div style='margin-top: 20px; padding: 10px; border-left: 3px solid #FF4B4B; background-color: rgba(255, 75, 75, 0.05);'>
    <h3 style='color: #FF4B4B;'>📍 Province Filter</h3>
</div>
""", unsafe_allow_html=True)

# Add "Select All" option
select_all = st.sidebar.checkbox("Select All Provinces", True)

if select_all:
    selected_provinces = sorted(df["PROVINCE"].dropna().unique().tolist())
else:
    # Multi-select for provinces with default top 5
    top_5_provinces = df["PROVINCE"].value_counts().nlargest(5).index.tolist()
    selected_provinces = st.sidebar.multiselect(
        "Select Provinces",
        sorted(df["PROVINCE"].dropna().unique().tolist()),
        default=top_5_provinces,
        help="You can select multiple provinces to compare"
    )

# Add province count indicator
st.sidebar.markdown(f"""
<div style='margin-top: 10px; padding: 5px; background-color: rgba(255, 75, 75, 0.1); border-radius: 5px;'>
    <p style='margin: 0; color: #FF4B4B;'>Selected: {len(selected_provinces)} provinces</p>
</div>
""", unsafe_allow_html=True)

# ✅ Filter Data Based on Magnitude and Province
filtered_df = df[
    (df["MAGNITUDE"] >= selected_mag[0]) & 
    (df["MAGNITUDE"] <= selected_mag[1]) &
    (df["PROVINCE"].isin(selected_provinces))
]

# Apply magnitude colors to filtered data
filtered_df["COLOR"] = filtered_df["MAGNITUDE"].apply(get_magnitude_color)

# Protect against too large datasets in the map visualization
map_df = filtered_df

# ✅ Prepare Sequential Data for Each Province Separately
def prepare_sequential_data(province_df):
    # Debug info
    if len(province_df) <= 1:
        return pd.DataFrame()  # Return empty dataframe if not enough points
        
    # Sort by time within the province
    province_df = province_df.sort_values("TIME").copy()
    
    # Create connections only within the same province
    province_df["NEXT_LAT"] = province_df["LATITUDE"].shift(-1)
    province_df["NEXT_LON"] = province_df["LONGITUDE"].shift(-1)
    province_df["NEXT_TIME"] = province_df["TIME"].shift(-1)
    province_df["NEXT_MAGNITUDE"] = province_df["MAGNITUDE"].shift(-1)
    province_df["NEXT_PROVINCE"] = province_df["PROVINCE"].shift(-1)
    province_df["NEXT_AREA"] = province_df["AREA"].shift(-1)  # Add next area
    
    # Calculate time differences (just for information)
    province_df["TIME_DIFF_HOURS"] = (
        province_df["NEXT_TIME"] - province_df["TIME"]
    ).dt.total_seconds() / 3600
    
    # Remove last row of each province (no next event)
    # Note: We're not filtering based on time difference anymore
    province_df = province_df.dropna(subset=["NEXT_LAT", "NEXT_LON", "NEXT_TIME"])
    
    # Apply red colors for sequential arcs with intensity based on magnitude
    def get_arc_color(magnitude):
        intensity = min(255, int(magnitude * 30))
        return [255, intensity, intensity, 200]  # Red with varying intensity
    
    # Apply red-based colors for source and target
    province_df["SOURCE_COLOR"] = province_df["MAGNITUDE"].apply(get_arc_color)
    province_df["TARGET_COLOR"] = province_df["NEXT_MAGNITUDE"].apply(get_arc_color)
    
    # Ensure TIME column is preserved
    if "TIME" not in province_df.columns:
        province_df["TIME"] = province_df.index
    
    return province_df

# Modified approach to handle case sensitivity issues
# Create a case-insensitive mapping of provinces
province_map = {p.lower(): p for p in df["PROVINCE"].dropna().unique()}

# Process each province separately and combine
sequential_df = pd.DataFrame()  # Empty DataFrame to store results
processed_provinces = []

# Track provinces with too few events
provinces_with_few_events = []

# Only process provinces that are selected in the filter
for province in selected_provinces:
    # Adjust for case sensitivity if needed
    if province.lower() in province_map:
        actual_province = province_map[province.lower()]
        province_data = filtered_df[filtered_df["PROVINCE"].str.lower() == province.lower()]
    else:
        # If exact match not found, try partial match
        matching_provinces = [p for p in df["PROVINCE"].dropna().unique() 
                             if any(part.lower() in p.lower() for part in province.split())]
        if matching_provinces:
            province_data = filtered_df[filtered_df["PROVINCE"].isin(matching_provinces)]
        else:
            continue  # Skip if no match found
    
    # Skip if there are not enough events
    if len(province_data) < 2:
        provinces_with_few_events.append((province, len(province_data)))
        continue
        
    processed_data = prepare_sequential_data(province_data)
    if not processed_data.empty:
        sequential_df = pd.concat([sequential_df, processed_data])
        processed_provinces.append(actual_province)

# Add a direct emergency override option
st.sidebar.markdown("""
<div style='margin-top: 10px; padding: 10px; background-color: rgba(255, 0, 0, 0.1); border-radius: 5px;'>
    <h4 style='color: #FF0000;'>🚨 Connection Troubleshooting</h4>
</div>
""", unsafe_allow_html=True)

force_connections = st.sidebar.checkbox("Force connections (emergency override)", value=False, 
                                       help="Use this if no connections are showing despite having data")

# Force creation of simple connections if needed
if force_connections and not filtered_df.empty:
    # Create a simplified version with direct province-based connections
    if len(filtered_df) >= 2:
        # Sort all filtered data by time
        temp_df = filtered_df.sort_values("TIME").copy()
        
        # Create connections
        temp_df["NEXT_LAT"] = temp_df["LATITUDE"].shift(-1)
        temp_df["NEXT_LON"] = temp_df["LONGITUDE"].shift(-1)
        temp_df["NEXT_TIME"] = temp_df["TIME"].shift(-1)
        temp_df["NEXT_MAGNITUDE"] = temp_df["MAGNITUDE"].shift(-1)
        temp_df["NEXT_PROVINCE"] = temp_df["PROVINCE"].shift(-1)
        temp_df["NEXT_AREA"] = temp_df["AREA"].shift(-1)
        
        # Calculate time differences
        temp_df["TIME_DIFF_HOURS"] = (temp_df["NEXT_TIME"] - temp_df["TIME"]).dt.total_seconds() / 3600
        temp_df["TIME_DIFF_HOURS_DISPLAY"] = temp_df["TIME_DIFF_HOURS"].round(1)
        
        # Remove last row (no next event)
        temp_df = temp_df.dropna(subset=["NEXT_LAT", "NEXT_LON", "NEXT_TIME", "TIME_DIFF_HOURS"])
        
        # Add red color for all connections
        temp_df["SOURCE_COLOR"] = [[255, 0, 0, 200] for _ in range(len(temp_df))]  # Bright red for source
        temp_df["TARGET_COLOR"] = [[255, 0, 0, 200] for _ in range(len(temp_df))]  # Bright red for target
        
        # Use this as our sequential data
        sequential_df = temp_df.copy()
    else:
        st.sidebar.error("Not enough data points to create connections.")

# Convert TIME and NEXT_TIME to string for tooltip display
if not sequential_df.empty:
    sequential_df["TIME_STR"] = sequential_df["TIME"].dt.strftime("%Y-%m-%d %H:%M")
    sequential_df["NEXT_TIME_STR"] = sequential_df["NEXT_TIME"].dt.strftime("%Y-%m-%d %H:%M")

# Directly modify the Sequential ArcLayer
layer_options = {
    "Scatterplot (Earthquakes)": pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position=["LONGITUDE", "LATITUDE"],
        get_color="COLOR",  # Use the magnitude-based color
        get_radius="MAGNITUDE * 10000",
        pickable=True,
        opacity=0.8,
        stroked=True,
        filled=True,
        line_width_min_pixels=1,
        radius_min_pixels=3,
        radius_max_pixels=30,
        get_line_color=[255, 255, 255],
    ),
    "3D Bars": pdk.Layer(
        "ColumnLayer",
        data=map_df,
        get_position=["LONGITUDE", "LATITUDE"],
        get_elevation="MAGNITUDE * 1000",
        elevation_scale=20,
        radius=3000,
        get_fill_color="COLOR",  # Use the magnitude-based color
        pickable=True,
        auto_highlight=True,
        extruded=True,
        coverage=1,
        get_line_color=[255, 255, 255],
        line_width_min_pixels=1,
        line_width_max_pixels=3,
    ),
    "Heat Map": pdk.Layer(
        "HeatmapLayer",
        data=map_df,
        get_position=["LONGITUDE", "LATITUDE"],
        get_weight="MAGNITUDE",
        aggregation="MEAN",
        pickable=False,
        opacity=0.8,
        threshold=0.1,
        radius_pixels=50,
    ),
    "Text Labels": pdk.Layer(
        "TextLayer",
        data=map_df.sample(n=min(200, len(map_df)), random_state=42),  # Limit text labels
        get_position=["LONGITUDE", "LATITUDE"],
        get_text="MAGNITUDE",
        get_size=16,
        get_color=[255, 255, 255],
        get_alignment_baseline="'bottom'",
        get_angle=0,
        text_background=True,
        get_text_background_color=[0, 0, 0, 200],
        get_pixel_offset=[0, -10],
        font_family="'Roboto', 'Arial', sans-serif",
        font_weight="bold",
        pickable=True,
        text_border_width=2,
        text_border_color=[0, 0, 0, 200],
        collision_filter=True,
        get_text_anchor="'middle'",
        size_min_pixels=10,
        size_max_pixels=20,
    ),
    "Sequential ArcLayer (Time-Based)": pdk.Layer(
        "ArcLayer",
        data=sequential_df if not sequential_df.empty else map_df,  # Fallback to any data
        get_source_position=["LONGITUDE", "LATITUDE"],
        get_target_position=["NEXT_LON", "NEXT_LAT"] if not sequential_df.empty else ["LONGITUDE", "LATITUDE"],  # Fallback
        get_source_color="COLOR",  # Use the same magnitude-based color as points
        get_target_color="COLOR",  # Use the same magnitude-based color as points
        auto_highlight=True,
        get_width="MAGNITUDE * 1",
        width_min_pixels=1,
        width_max_pixels=10,
        pickable=True,
        get_height=0.7,
        highlight_color=[255, 255, 255, 255],
    )
}

# Add a custom layer selector with descriptions
st.sidebar.markdown("""
<div style='margin-top: 10px; padding: 5px;'>
    <h4 style='color: #FF4B4B;'>⚙️ Layer Configuration</h4>
</div>
""", unsafe_allow_html=True)

# More informative layer selection
layer_descriptions = {
    "Scatterplot (Earthquakes)": "Shows earthquakes as points with size based on magnitude",
    "3D Bars": "Visualizes earthquakes as 3D columns with height based on magnitude",
    "Heat Map": "Displays earthquake density with intensity based on magnitude",
    "Text Labels": "Adds magnitude labels to earthquake points",
    "Sequential ArcLayer (Time-Based)": "Connects sequential earthquakes with arcs"
}

# Add a map style selector
st.sidebar.markdown("### 🎨 Map Style")
map_style = st.sidebar.selectbox(
    "Select base map style",
    options=[
        "mapbox://styles/mapbox/dark-v10",
        "mapbox://styles/mapbox/light-v10",
        "mapbox://styles/mapbox/satellite-v9",
        "mapbox://styles/mapbox/satellite-streets-v11",
        "mapbox://styles/mapbox/navigation-night-v1"
    ],
    index=3
)

# Add view controls
st.sidebar.markdown("### 🔍 Map View")
initial_pitch = st.sidebar.slider("3D Pitch", 0, 60, 40)
initial_zoom = st.sidebar.slider("Zoom Level", 3, 10, 5)

# Layer selection code
selected_layers = []
for name, layer in layer_options.items():
    col1, col2 = st.sidebar.columns([1, 3])
    with col1:
        is_selected = st.checkbox("", value=True, key=f"layer_{name}")
    with col2:
        st.markdown(f"""
        <div style='margin-bottom: 5px;'>
            <span style='color: #FF4B4B; font-weight: 500;'>{name}</span>
            <div style='font-size: 0.8em; color: #AAAAAA;'>{layer_descriptions[name]}</div>
            </div>
            """, unsafe_allow_html=True)

    if is_selected:
        selected_layers.append(layer)

# Add alternative view of connections with LineLayer
if not sequential_df.empty and "Sequential Lines" not in layer_options:
    layer_options["Sequential Lines"] = pdk.Layer(
        "LineLayer",
        data=sequential_df,
        get_source_position=["LONGITUDE", "LATITUDE"],
        get_target_position=["NEXT_LON", "NEXT_LAT"],
        get_color=[255, 0, 0, 200],  # Red lines
        get_width="MAGNITUDE * 5",
        width_min_pixels=4,
        width_max_pixels=30,
        pickable=True,
    )
    
    layer_descriptions["Sequential Lines"] = "Connects sequential earthquakes with direct lines (alternative to arcs)"

# 🌍 Define Map View with updated controls
view_state = pdk.ViewState(
    latitude=12.8797,
    longitude=121.7740,
    zoom=initial_zoom,
    pitch=initial_pitch,
    bearing=0,
    height=600
)

# Main map container
st.markdown("### Interactive Earthquake Map")

# Add information about data density
if not filtered_df.empty:
    pass

# Ensure TIME_DIFF_HOURS_DISPLAY exists in filtered_df and map_df for tooltip compatibility
if "TIME_DIFF_HOURS_DISPLAY" not in filtered_df.columns:
    filtered_df["TIME_DIFF_HOURS_DISPLAY"] = "N/A"
else:
    filtered_df["TIME_DIFF_HOURS_DISPLAY"] = filtered_df["TIME_DIFF_HOURS_DISPLAY"].replace('', 'N/A')
if "TIME_DIFF_HOURS_DISPLAY" not in map_df.columns:
    map_df["TIME_DIFF_HOURS_DISPLAY"] = "N/A"
else:
    map_df["TIME_DIFF_HOURS_DISPLAY"] = map_df["TIME_DIFF_HOURS_DISPLAY"].replace('', 'N/A')

# 🗺️ Render Map with enhanced tooltip
if selected_layers:
    st.pydeck_chart(pdk.Deck(
        map_style=map_style,
        initial_view_state=view_state,
        layers=selected_layers,
        tooltip={
            "html": """
            <div style=\"background-color: rgba(0, 0, 0, 0.8); color: white; border-radius: 4px; padding: 6px; font-family: 'Arial', sans-serif; font-size: 12px; max-width: 200px;\">
                <div style=\"color: #FF4B4B; font-weight: bold; margin-bottom: 3px;\">{AREA}</div>
                <div style=\"display: flex; justify-content: space-between; margin-bottom: 2px;\">
                    <span>Mag:</span>
                    <span>{MAGNITUDE}</span>
                </div>
                <div style=\"display: flex; justify-content: space-between; margin-bottom: 2px;\">
                    <span>Depth:</span>
                    <span>{DEPTH (KM)} km</span>
                </div>
                <div style=\"border-top: 1px solid rgba(255, 255, 255, 0.2); margin: 3px 0; padding-top: 3px;\">
                    <div style=\"display: flex; justify-content: space-between; margin-bottom: 2px;\">
                        <span>From:</span>
                        <span>{AREA}</span>
                    </div>
                    <div style=\"display: flex; justify-content: space-between; margin-bottom: 2px;\">
                        <span>To:</span>
                        <span>{NEXT_AREA}</span>
                    </div>
                </div>
            </div>
            """,
            "style": {
                "backgroundColor": "transparent",
                "color": "white"
            }
        }
    ))
else:
    st.error("Please select at least one layer.")


