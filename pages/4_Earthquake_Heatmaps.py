import streamlit as st
import pandas as pd
import pydeck as pdk
import numpy as np
import time
import plotly.express as px
import json
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from datetime import timedelta

# Set page config must be the first Streamlit command
st.set_page_config(
    page_title="Earthquake Heatmap", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #ff5733;
        text-align: center;
        margin-bottom: 1rem;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }
    .sub-header {
        font-size: 1.8rem;
        color: #ff5733;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .description {
        text-align: center;
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .info-box {
        background-color: rgba(255, 87, 51, 0.1);
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .divider {
        margin: 2rem 0;
        border-bottom: 1px solid #eee;
    }
    /* Custom sidebar styling */
    .sidebar .sidebar-content {
        background-color: #f5f5f5;
    }
</style>
""", unsafe_allow_html=True)

# Create tabs for better organization
tab1, tab2 = st.tabs(["🗾 Earthquake Intensity Heatmap", "🌊 Ripple Animation"])

# Cache data loading function
@st.cache_data
def load_earthquake_data():
    file_path = r"merged_output.csv"
    try:
        df = pd.read_csv(file_path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding="ISO-8859-1")

    # Ensure column names are consistent
    df.columns = df.columns.str.upper()
    
    # Convert category to uppercase if it exists
    if "CATEGORY" in df.columns:
        df["CATEGORY"] = df["CATEGORY"].str.upper()

    # Convert DATE column to datetime
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
    
    # Add date and time column if it doesn't exist
    if "DATE & TIME" not in df.columns:
        df["DATE & TIME"] = df["DATE"]
    else:
        df["DATE & TIME"] = pd.to_datetime(df["DATE & TIME"], errors="coerce")
    
    # Sort by date
    df = df.sort_values("DATE")
    
    # Add year and month for time-based filtering
    df["YEAR"] = df["DATE"].dt.year
    df["MONTH"] = df["DATE"].dt.month
    
    # Add a formatted date column specifically for tooltips
    df["DATE_STR"] = df["DATE & TIME"].dt.strftime("%d %b %Y - %I:%M %p")
    
    return df

# Show loading message
with st.spinner("Loading earthquake data..."):
    try:
        df = load_earthquake_data()
        
        # Ensure required columns exist
        required_columns = {'LATITUDE', 'LONGITUDE', 'MAGNITUDE', 'CATEGORY', 'AREA', 'PROVINCE', 'DATE'}
        if not required_columns.issubset(df.columns):
            missing = required_columns - set(df.columns)
            st.error(f"CSV file missing required columns: {missing}")
            st.stop()
            
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.stop()

# Move Filter Options to Sidebar with better organization
with st.sidebar:
    st.markdown(
        """
        <h2 style='color: #ff5733;'>🎛️ Filter Options</h2>
        <p style='color: gray;'>Select parameters to customize the visualization.</p>
        """, unsafe_allow_html=True
    )
    
    # Create expandable sections for different filter groups
    with st.expander("📍 Location Filters", expanded=True):
        # Get unique areas and provinces
        area_options = [None] + sorted(df["AREA"].unique())
        province_options = [None] + sorted(df["PROVINCE"].unique())
        
        # Add filters to sidebar
        selected_area = st.selectbox("Select Area:", area_options)
        selected_province = st.selectbox("Select Province:", province_options)
        
        # Add epicenter filter with better explanation
        epicenter_options = [None, "Province", "Area"]
        selected_epicenter = st.selectbox(
            "Epicenter Filter:", 
            epicenter_options, 
            help="Filter to show only the strongest earthquake in each province or area"
        )
    
    with st.expander("📅 Time Filters", expanded=True):
        # Date range filter
        date_min, date_max = df["DATE"].min(), df["DATE"].max()
        
        # Date range selection
        date_range_type = st.radio(
            "Select Date Range Type",
            ["Specific Dates", "Year", "Recent Period"],
            horizontal=True
        )
        
        if date_range_type == "Specific Dates":
            selected_date_range = st.date_input(
                "Select Date Range:", 
                [date_min.date(), date_max.date()], 
                min_value=date_min.date(), 
                max_value=date_max.date()
            )
            if len(selected_date_range) == 2:
                start_date, end_date = selected_date_range
            else:
                start_date, end_date = date_min.date(), date_max.date()
                
        elif date_range_type == "Year":
            years = sorted(df["YEAR"].unique())
            selected_year = st.selectbox("Select Year:", years, index=len(years)-1)
            year_df = df[df["YEAR"] == selected_year]
            start_date = year_df["DATE"].min().date()
            end_date = year_df["DATE"].max().date()
            st.info(f"Selected period: {start_date} to {end_date}")
            
        else:  # Recent Period
            period = st.slider("Recent months:", 1, 36, 6)
            end_date = date_max.date()
            start_date = (date_max - pd.DateOffset(months=period)).date()
            st.info(f"Selected period: {start_date} to {end_date}")
    
    with st.expander("🔍 Magnitude & Category Filters", expanded=True):
        # Magnitude range
        mag_min, mag_max = float(df["MAGNITUDE"].min()), float(df["MAGNITUDE"].max())
        magnitude_range = st.slider(
            "Magnitude Range:", 
            min_value=mag_min,
            max_value=mag_max,
            value=(mag_min, mag_max),
            step=0.1
        )
        
        # Category selection
        if "CATEGORY" in df.columns:
            categories = sorted(df["CATEGORY"].unique())
            all_categories = st.checkbox("Select All Categories", value=True)
            if all_categories:
                selected_categories = categories
            else:
                selected_categories = st.multiselect(
                    "Select Earthquake Categories:",
                    categories,
                    default=categories[:3] if len(categories) > 3 else categories
                )
        else:
            selected_categories = None
            st.warning("No category information available in the dataset.")

# Apply filters to create filtered dataset
filtered_df = df.copy()

# Apply location filters
if selected_area is not None:
    filtered_df = filtered_df[filtered_df["AREA"] == selected_area]
if selected_province is not None:
    filtered_df = filtered_df[filtered_df["PROVINCE"] == selected_province]

# Apply date range filter
filtered_df = filtered_df[
    (filtered_df["DATE"].dt.date >= start_date) & 
    (filtered_df["DATE"].dt.date <= end_date)
]

# Apply magnitude filter
filtered_df = filtered_df[
    (filtered_df["MAGNITUDE"] >= magnitude_range[0]) & 
    (filtered_df["MAGNITUDE"] <= magnitude_range[1])
]

# Apply category filter if available
if selected_categories is not None:
    filtered_df = filtered_df[filtered_df["CATEGORY"].isin(selected_categories)]

# Apply epicenter filter (only show strongest earthquake in each area/province)
if selected_epicenter == "Province":
    filtered_df = filtered_df.loc[filtered_df.groupby(["PROVINCE"])["MAGNITUDE"].idxmax()].reset_index(drop=True)
elif selected_epicenter == "Area":
    filtered_df = filtered_df.loc[filtered_df.groupby(["AREA"])["MAGNITUDE"].idxmax()].reset_index(drop=True)

# Format date for display
filtered_df_display = filtered_df.copy()
filtered_df_display["DATE_FORMATTED"] = filtered_df_display["DATE"].dt.strftime("%d %B %Y")

# Also add the DATE_STR column to filtered_df if not already present
if "DATE_STR" not in filtered_df.columns:
    filtered_df["DATE_STR"] = filtered_df["DATE & TIME"].dt.strftime("%d %b %Y - %I:%M %p")

# Add some metrics to the sidebar
with st.sidebar:
    st.markdown("### 📊 Current Selection")
    col1, col2 = st.columns(2)
    col1.metric("Total Records", f"{len(filtered_df):,}")
    col2.metric("Avg Magnitude", f"{filtered_df['MAGNITUDE'].mean():.2f}")
    
# Tab 1: Earthquake Intensity Heatmap
with tab1:
    st.markdown("<h2 class='sub-header'>🗾 Earthquake Intensity Heatmap Visualization</h2>", unsafe_allow_html=True)
    
    # Description
    st.markdown("""
    This heatmap shows the density of earthquake epicenters, with color intensity representing concentration of seismic activity.
    Areas with more frequent earthquakes appear as brighter hotspots on the map.
    """)
    
    # Map view controls section
    st.markdown("<h4 style='color: #ff5733; margin-top: 15px;'>Map View Controls</h4>", unsafe_allow_html=True)

    # Map style selection
    map_style = st.selectbox(
        "Map Style",
        options=[
            "Satellite with Streets",
            "Satellite",
            "Dark",
            "Light",
            "Navigation Day",
            "Navigation Night"
        ],
        index=2
    )
    
    # Map style dictionary for mapbox
    mapbox_styles = {
        "Satellite with Streets": "mapbox://styles/mapbox/satellite-streets-v11",
        "Satellite": "mapbox://styles/mapbox/satellite-v9",
        "Dark": "mapbox://styles/mapbox/dark-v10",
        "Light": "mapbox://styles/mapbox/light-v10",
        "Navigation Day": "mapbox://styles/mapbox/navigation-day-v1",
        "Navigation Night": "mapbox://styles/mapbox/navigation-night-v1"
    }
    
    # Layer controls
    heatmap_col1, heatmap_col2 = st.columns(2)
    
    with heatmap_col1:
        radius = st.slider(
            "Heatmap Radius", 
            min_value=10, 
            max_value=100, 
            value=40,
            help="Adjust the radius of influence for each earthquake point"
        )
    
    with heatmap_col2:
        # Weight by magnitude or just by count
        weight_by = st.radio(
            "Heatmap intensity based on:",
            ["Earthquake Count", "Magnitude Weighted"],
            horizontal=True
        )
    
    # Create and display heatmap
    if len(filtered_df) > 0:
        try:
            # Calculate map center
            center_lat = filtered_df["LATITUDE"].mean()
            center_lon = filtered_df["LONGITUDE"].mean()
            
            # Create view state with angle controls
            view_state = pdk.ViewState(
                latitude=center_lat,
                longitude=center_lon,
                pitch=45,
                bearing=0,
                zoom=5.5
            )
            
            # Create heatmap layer
            heatmap_layer = pdk.Layer(
                "HeatmapLayer",
                data=filtered_df,
                get_position=["LONGITUDE", "LATITUDE"],
                get_weight="MAGNITUDE" if weight_by == "Magnitude Weighted" else 1,
                aggregation="SUM",
                radius_pixels=radius,
                opacity=0.85,
                pickable=True,
                color_range=[
                    # Exact colors matching intensity scale (I-X)
                    [255, 255, 255],    # I - White (Scarcely Perceptible)
                    [204, 229, 255],    # II - Light Blue (Slightly Felt)
                    [0, 255, 255],      # III - Cyan (Weak)
                    [0, 255, 128],      # IV - Green (Moderately Strong)
                    [170, 255, 0],      # V - Light Green/Yellow-Green (Strong)
                    [255, 255, 0],      # VI - Yellow (Very Strong)
                    [255, 170, 0],      # VII - Orange (Destructive)
                    [255, 102, 0],      # VIII - Dark Orange (Very Destructive)
                    [255, 0, 0],        # IX - Red (Devastating)
                    [153, 0, 0]         # X - Dark Red (Completely Devastating)
                ],
                threshold=0.05
            )
            
            # Add invisible scatter plot layer for better hover detection
            # This layer provides points to hover over but is nearly invisible
            scatter_layer = pdk.Layer(
                "ScatterplotLayer",
                data=filtered_df,
                get_position=["LONGITUDE", "LATITUDE"],
                get_radius=1000,  # Small radius
                get_fill_color=[255, 255, 255, 0],  # Completely transparent
                pickable=True,
                opacity=0.0,  # Fully transparent 
                auto_highlight=True,
                highlight_color=[255, 255, 255, 50],  # Very subtle highlight
                stroked=False
            )
            
            # Create and display the mapbox map
            deck = pdk.Deck(
                map_style=mapbox_styles[map_style],
                initial_view_state=view_state,
                layers=[heatmap_layer, scatter_layer],  # Add the scatter layer under the heatmap
                tooltip={
                    "html": """
                    <div style="background-color: rgba(42, 42, 42, 0.95); color: white; 
                         padding: 10px; border-radius: 5px; font-family: Arial; width: 250px;">
                        <div style="font-weight: bold; font-size: 14px;">{PROVINCE}</div>
                        <div style="margin: 5px 0;">
                            <span style="color: #aaa;">Magnitude:</span> {MAGNITUDE}
                        </div>
                        <div style="margin: 5px 0;">
                            <span style="color: #aaa;">Area:</span> {AREA}
                        </div>
                        <div style="margin: 5px 0;">
                            <span style="color: #aaa;">Date/Time:</span> {DATE_STR}
                        </div>
                        <div style="margin: 5px 0;">
                            <span style="color: #aaa;">Category:</span> {CATEGORY}
                        </div>
                    </div>
                    """
                }
            )
            
            # Display the map
            st.pydeck_chart(deck, use_container_width=True)
            st.caption("Hover over the map to see earthquake details. Use the sliders above to adjust the view angle, rotation, and zoom.")
            
            # Add intensity scale legend
            st.markdown("<h4 style='color: #ff5733; margin-top: 15px;'>Earthquake Intensity Scale</h4>", unsafe_allow_html=True)
            
            # Create a legend table matching the image
            intensity_scale_html = """
            <table style="width:100%; border-collapse: collapse; margin-top: 10px;">
                <tr>
                    <th style="padding: 8px; text-align: center; width: 80px; border: 1px solid #ddd; background-color: #f8f8f8;">Intensity Scale</th>
                    <th style="padding: 8px; text-align: center; border: 1px solid #ddd; background-color: #f8f8f8;">Shaking</th>
                </tr>
                <tr>
                    <td style="padding: 8px; text-align: center; border: 1px solid #ddd; background-color: #FFFFFF; color: black; font-weight: bold;">I</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">Scarcely Perceptible</td>
                </tr>
                <tr>
                    <td style="padding: 8px; text-align: center; border: 1px solid #ddd; background-color: #CCEBFF; color: black; font-weight: bold;">II</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">Slightly Felt</td>
                </tr>
                <tr>
                    <td style="padding: 8px; text-align: center; border: 1px solid #ddd; background-color: #00FFFF; color: black; font-weight: bold;">III</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">Weak</td>
                </tr>
                <tr>
                    <td style="padding: 8px; text-align: center; border: 1px solid #ddd; background-color: #00FF80; color: black; font-weight: bold;">IV</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">Moderately Strong</td>
                </tr>
                <tr>
                    <td style="padding: 8px; text-align: center; border: 1px solid #ddd; background-color: #AAFF00; color: black; font-weight: bold;">V</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">Strong</td>
                </tr>
                <tr>
                    <td style="padding: 8px; text-align: center; border: 1px solid #ddd; background-color: #FFFF00; color: black; font-weight: bold;">VI</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">Very Strong</td>
                </tr>
                <tr>
                    <td style="padding: 8px; text-align: center; border: 1px solid #ddd; background-color: #FFAA00; color: black; font-weight: bold;">VII</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">Destructive</td>
                </tr>
                <tr>
                    <td style="padding: 8px; text-align: center; border: 1px solid #ddd; background-color: #FF6600; color: white; font-weight: bold;">VIII</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">Very Destructive</td>
                </tr>
                <tr>
                    <td style="padding: 8px; text-align: center; border: 1px solid #ddd; background-color: #FF0000; color: white; font-weight: bold;">IX</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">Devastating</td>
                </tr>
                <tr>
                    <td style="padding: 8px; text-align: center; border: 1px solid #ddd; background-color: #990000; color: white; font-weight: bold;">X</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">Completely Devastating</td>
                </tr>
            </table>
            """
            
            st.markdown(intensity_scale_html, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Error generating heatmap: {str(e)}")
            st.info("Try adjusting the filters or map settings.")
    else:
        st.warning("No data to display with current filters.")

# Tab 2: Ripple Animation
with tab2:
    st.markdown("<h2 class='sub-header'>🌊 Ripple Animation of Earthquake Epicenters</h2>", unsafe_allow_html=True)
    
    # Description of the animation
    st.markdown("""
    This animation shows earthquake epicenters as rippling circles, with size based on magnitude and color indicating intensity.
    Use the controls below to start and stop the animation.
    """)
    
    # Define color based on category
    def get_color(row):
        # Get category from the row, default to lowest intensity if not available
        category = row.get("CATEGORY", "SCARCELY PERCEPTIBLE") if isinstance(row, dict) else row.get("CATEGORY", "SCARCELY PERCEPTIBLE")
        
        # Map category to color based on intensity scale
        category_color_map = {
            "SCARCELY PERCEPTIBLE": [255, 255, 255, 150],  # White (I)
            "SLIGHTLY FELT": [160, 230, 255, 150],        # Light Blue (II)
            "WEAK": [0, 255, 255, 150],                  # Cyan (III)
            "MODERATELY STRONG": [0, 255, 0, 150],        # Green (IV)
            "STRONG": [176, 255, 0, 150],                # Light Green (V)
            "VERY STRONG": [255, 255, 0, 150],           # Yellow (VI)
            "DESTRUCTIVE": [255, 165, 0, 150],           # Orange (VII)
            "VERY DESTRUCTIVE": [255, 102, 0, 150],      # Dark Orange (VIII)
            "DEVASTATING": [255, 0, 0, 150],             # Red (IX)
            "COMPLETELY DEVASTATING": [153, 0, 0, 150]   # Dark Red (X)
        }
        
        # Return the color based on category, default to white if category not found
        return category_color_map.get(category, [255, 255, 255, 150])
    
    # Add intensity scale legend in the tab
    st.markdown("""
    **🔹 Intensity Scale Legend**  
    - ⚪ **I: Scarcely Perceptible**
    - 🔵 **II: Slightly Felt**
    - 🧊 **III: Weak**
    - 🟢 **IV: Moderately Strong**
    - 🥝 **V: Strong**
    - 🟡 **VI: Very Strong**
    - 🟠 **VII: Destructive**
    - 🔶 **VIII: Very Destructive**
    - 🔴 **IX: Devastating**
    - 🟥 **X: Completely Devastating**
    """)
    
    # Animation controls
    col1, col2 = st.columns(2)
    
    # Initialize session state for animation control if not already set
    if 'animate_ripple' not in st.session_state:
        st.session_state.animate_ripple = False
    
    # Animation function
    def run_ripple_animation():
        # Use filtered data for animation
        animation_df = filtered_df.copy()
        
        # Additional magnitude filter for animation
        show_all = st.checkbox("Show all magnitudes", value=True)
        if not show_all:
            mag_to_filter = st.slider(
                'Minimum magnitude to display', 
                float(animation_df["MAGNITUDE"].min()), 
                float(animation_df["MAGNITUDE"].max()), 
                float(animation_df["MAGNITUDE"].min() + 1.0)
            )
            animation_df = animation_df[animation_df["MAGNITUDE"] >= mag_to_filter]
        
        if len(animation_df) == 0:
            st.warning("No data to animate with current filters.")
            return
            
        # Create animation container
        map_container = st.empty()
        progress_bar = st.progress(0)
        
        # Parameters for animation
        displayed_earthquakes = []
        MAX_DISPLAYED = min(10, len(animation_df))  # Maximum number of earthquakes to display at once
        
        # Run animation while animation state is true
        event_count = len(animation_df)
        try:
            for i, (index, row) in enumerate(animation_df.iterrows()):
                if not st.session_state.animate_ripple:
                    break
                    
                # Update progress
                progress_bar.progress(min(1.0, (i+1)/event_count))
                
                # Add new earthquake
                displayed_earthquakes.append(row)
                
                # Keep only the last MAX_DISPLAYED earthquakes
                if len(displayed_earthquakes) > MAX_DISPLAYED:
                    displayed_earthquakes = displayed_earthquakes[-MAX_DISPLAYED:]
                
                # Animate ripple effect
                for pulse_step in np.linspace(0, 1, num=15):
                    if not st.session_state.animate_ripple:
                        break
                        
                    temp_data = pd.DataFrame(displayed_earthquakes)
                    temp_data["pulse_radius"] = temp_data["MAGNITUDE"] * (3000 + (np.sin(pulse_step * np.pi) * 5000))
                    temp_data["color"] = temp_data.apply(get_color, axis=1)
                    
                    # Create map layers
                    earthquake_layer = pdk.Layer(
                        "ScatterplotLayer",
                        temp_data,
                        get_position=["LONGITUDE", "LATITUDE"],
                        get_radius="pulse_radius",
                        get_fill_color="color",
                        pickable=True,
                        auto_highlight=True,
                        get_line_color=[255, 255, 255],
                        stroked=True,
                        opacity=0.8,
                        radius_min_pixels=2,
                        radius_max_pixels=50,
                    )
                    
                    text_layer = pdk.Layer(
                        "TextLayer",
                        temp_data,
                        get_position=["LONGITUDE", "LATITUDE"],
                        get_text="AREA",
                        get_color=[255, 255, 255],
                        get_size=10,
                        get_angle=0,
                        get_alignment_baseline="'bottom'",
                    )
                    
                    # Calculate center point based on the most recent earthquake
                    view_state = pdk.ViewState(
                        latitude=row["LATITUDE"],
                        longitude=row["LONGITUDE"],
                        zoom=7,
                        pitch=0
                    )
                    
                    # Create and display map
                    map_container.pydeck_chart(pdk.Deck(
                        layers=[earthquake_layer, text_layer],
                        initial_view_state=view_state,
                        tooltip={"text": "Magnitude: {MAGNITUDE}\nArea: {AREA}\nProvince: {PROVINCE}\nDate/Time: {DATE_STR}"},
                        map_style="mapbox://styles/mapbox/satellite-streets-v11"
                    ))
                    
                    time.sleep(0.08)  # Slightly faster animation
            
            st.success("Animation completed!")
            
        except Exception as e:
            st.error(f"Error during animation: {str(e)}")
    
    # Animation control buttons
    with col1:
        if st.button("▶️ Start Ripple Animation", use_container_width=True):
            st.session_state.animate_ripple = True
            run_ripple_animation()
    
    with col2:
        if st.button("⏹️ Stop Animation", use_container_width=True):
            st.session_state.animate_ripple = False
    
    # Show static map if not animating
    if not st.session_state.animate_ripple and len(filtered_df) > 0:
        # Create static map with earthquake points
        static_map_df = filtered_df.copy()
        static_map_df["color"] = static_map_df.apply(get_color, axis=1)
        static_map_df["radius"] = static_map_df["MAGNITUDE"] * 5000
        
        # Create map layers
        earthquake_layer = pdk.Layer(
            "ScatterplotLayer",
            static_map_df,
            get_position=["LONGITUDE", "LATITUDE"],
            get_radius="radius",
            get_fill_color="color",
            pickable=True,
            opacity=0.8,
            stroked=True,
            get_line_color=[255, 255, 255],
            line_width_min_pixels=1
        )
        
        # Calculate map center
        center_lat = static_map_df["LATITUDE"].mean()
        center_lon = static_map_df["LONGITUDE"].mean()
        
        # Create view state
        view_state = pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=5.5,
            pitch=0
        )
        
        # Display static map
        st.pydeck_chart(pdk.Deck(
            layers=[earthquake_layer],
            initial_view_state=view_state,
            tooltip={"text": "Magnitude: {MAGNITUDE}\nArea: {AREA}\nProvince: {PROVINCE}\nDate/Time: {DATE_STR}"},
            map_style="mapbox://styles/mapbox/satellite-streets-v11"
        ))
