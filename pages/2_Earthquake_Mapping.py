import streamlit as st  
import pandas as pd
import pydeck as pdk
import os
import datetime
import plotly.express as px

# Set Page Configuration with a different title and icon
st.set_page_config(
    page_title="Seismic Activity Analyzer", 
    page_icon="🔍",
    layout="wide"
)

# Different CSS styling theme
st.markdown("""
<style>
    .page-title {
        font-size: 2.8rem;
        color: #3366cc;
        text-align: center;
        margin-bottom: 1.5rem;
        font-family: 'Georgia', serif;
    }
    .section-header {
        font-size: 1.6rem;
        color: #3366cc;
        margin: 1.2rem 0;
        border-bottom: 2px solid #e0e0e0;
        padding-bottom: 0.4rem;
    }
    .info-container {
        background-color: rgba(51, 102, 204, 0.1);
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .legend-container {
        display: flex;
        align-items: center;
        margin: 8px 0;
    }
    .legend-marker {
        width: 18px;
        height: 18px;
        border-radius: 50%;
        margin-right: 12px;
    }
    .stat-box {
        background-color: #f8f8f8;
        padding: 12px;
        border-radius: 8px;
        margin: 8px 0;
        border-left: 4px solid #3366cc;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# New header layout with tabs
st.markdown("<h1 class='page-title'>🔍 Seismic Activity Analyzer - Philippines</h1>", unsafe_allow_html=True)

# Create tabs for different sections
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🌍 Interactive Map", "📈 Analytics"])

with tab1:
    # Introduction section with a different layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        <div class="info-container">
            <h3>Welcome to the Seismic Activity Analyzer</h3>
            <p>This advanced tool visualizes earthquake data throughout the Philippines region. 
            Customize your analysis using various filters available in the control panel.</p>
            <p>The visualization helps identify patterns in seismic activity, frequency, and intensity across different regions.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Add a small chart or image here
        st.image("https://cdn-icons-png.flaticon.com/512/2377/2377860.png", width=150)
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        st.markdown(f"<p style='text-align:right;'><small>Last data refresh: {current_time}</small></p>", unsafe_allow_html=True)

# Sidebar with a different title and organization
with st.sidebar:
    st.markdown("<h2 style='text-align:center; color:#3366cc'>Analysis Controls</h2>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # Add expandable sections for better organization
    with st.expander("ℹ️ About This Tool", expanded=False):
        st.markdown("""
        The Seismic Activity Analyzer provides comprehensive visualization of earthquake data.
        Use the filters below to customize your view and analyze patterns across different regions and time periods.
        """)
    
    # Data sampling controls moved outside of cached function
    st.markdown("### 📉 Data Sampling Controls")
    
    col1, col2 = st.columns(2)
    with col1:
        sample_percent = st.slider("Sample %", 5, 100, 25, 
                                   help="Adjust to reduce data size")
    with col2:
        max_points = st.number_input("Max Records", 
                                     min_value=1000, 
                                     max_value=50000, 
                                     value=10000)

# Load Earthquake Data with the same functionality but different variable names
@st.cache_data
def import_seismic_data(sample_pct, max_pts):
    csv_path = r"merged_output.csv"

    if not os.path.exists(csv_path):
        st.error(f"Data file not found at: {csv_path}. Please verify the file location.")
        return None

    seismic_df = pd.read_csv(csv_path)
    seismic_df.columns = seismic_df.columns.str.strip().str.upper()

    needed_columns = {"LATITUDE", "LONGITUDE", "DEPTH (KM)", "MAGNITUDE", "TIME"}
    if not needed_columns.issubset(seismic_df.columns):
        st.error(f"Required columns missing: {needed_columns - set(seismic_df.columns)}")
        return None

    seismic_df["LATITUDE"] = pd.to_numeric(seismic_df["LATITUDE"], errors="coerce")
    seismic_df["LONGITUDE"] = pd.to_numeric(seismic_df["LONGITUDE"], errors="coerce")
    seismic_df["DEPTH (KM)"] = pd.to_numeric(seismic_df["DEPTH (KM)"], errors="coerce")
    seismic_df["MAGNITUDE"] = pd.to_numeric(seismic_df["MAGNITUDE"], errors="coerce")
    
    # Process date and time fields
    if "DATE & TIME" in seismic_df.columns:
        seismic_df["DISPLAY_TIME"] = seismic_df["DATE & TIME"]
        seismic_df["TIME"] = pd.to_datetime(seismic_df["DATE & TIME"], errors="coerce")
    else:
        if "DATE" in seismic_df.columns and "TIME" in seismic_df.columns:
            seismic_df["DISPLAY_TIME"] = seismic_df["DATE"] + " " + seismic_df["TIME"]
            seismic_df["TIME"] = pd.to_datetime(seismic_df["DATE"] + " " + seismic_df["TIME"], errors="coerce")
        else:
            seismic_df["TIME"] = pd.to_datetime(seismic_df["TIME"], errors="coerce")
            seismic_df["DISPLAY_TIME"] = seismic_df["TIME"].dt.strftime("%d %B %Y - %I:%M %p")

    # Convert depth to negative for visual representation
    seismic_df["DEPTH (KM)"] = -seismic_df["DEPTH (KM)"]
    seismic_df = seismic_df.dropna(subset=["LATITUDE", "LONGITUDE", "DEPTH (KM)", "MAGNITUDE", "TIME"])
    
    # Track total count before sampling
    total_count = len(seismic_df)
    
    # Apply sampling logic but using the parameters passed in
    if sample_pct < 100:
        seismic_df = seismic_df.sample(frac=sample_pct/100, random_state=42)
    
    if len(seismic_df) > max_pts:
        seismic_df = seismic_df.sample(n=max_pts, random_state=42)
    
    # Return both the dataframe and the total count
    return seismic_df, total_count

# Load data with a loading spinner with different text
with st.spinner('Importing seismic data, please wait...'):
    seismic_data, total_count = import_seismic_data(sample_percent, max_points)
    
if seismic_data is None:
    st.stop()

# Show sampling statistics in sidebar
with st.sidebar:
    display_count = len(seismic_data)
    percent_shown = (display_count / total_count) * 100
    
    st.markdown(f"""
    <div style='background-color:rgba(51,102,204,0.1); padding:10px; border-radius:5px; margin:10px 0;'>
        <b>Data Overview:</b> Showing {display_count:,} of {total_count:,} records ({percent_shown:.1f}%)
    </div>
    """, unsafe_allow_html=True)

# Prioritize significant events
seismic_data = seismic_data.sort_values("MAGNITUDE", ascending=False).reset_index(drop=True)

# Dashboard metrics in a different layout
with tab1:
    # Key metrics in a 2x2 grid instead of a single row
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)
    
    event_count = len(seismic_data)
    avg_mag = seismic_data["MAGNITUDE"].mean()
    max_mag = seismic_data["MAGNITUDE"].max()
    date_span = f"{seismic_data['TIME'].min().date()} to {seismic_data['TIME'].max().date()}"
    
    with col1:
        st.metric("Total Seismic Events", f"{event_count:,}")
    with col2:
        st.metric("Average Magnitude", f"{avg_mag:.2f}")
    with col3:
        st.metric("Peak Magnitude", f"{max_mag:.2f}")
    with col4:
        st.metric("Time Range", date_span)
    
    # Add a quick histogram
    st.markdown("<h3 class='section-header'>Magnitude Distribution</h3>", unsafe_allow_html=True)
    fig = px.histogram(seismic_data, x="MAGNITUDE", nbins=30,
                     color_discrete_sequence=["#3366cc"],
                     title="Distribution of Earthquake Magnitudes")
    fig.update_layout(bargap=0.1)
    st.plotly_chart(fig, use_container_width=True)

# Process data for visualization with different variable names
seismic_data = seismic_data.sort_values("TIME")

# Create temporal connections
seismic_data["NEXT_LATITUDE"] = seismic_data["LATITUDE"].shift(-1)
seismic_data["NEXT_LONGITUDE"] = seismic_data["LONGITUDE"].shift(-1)
seismic_data["NEXT_TIME"] = seismic_data["TIME"].shift(-1)
seismic_data["HOURS_BETWEEN"] = (seismic_data["NEXT_TIME"] - seismic_data["TIME"]).dt.total_seconds() / 3600

# Remove last row with no next event
seismic_data = seismic_data.dropna(subset=["NEXT_LATITUDE", "NEXT_LONGITUDE", "NEXT_TIME", "HOURS_BETWEEN"])

# Color mapping function with a different approach
def time_color_mapping(hours):
    if hours < 2:  # Changed time threshold
        return [50, 150, 255, 200]  # Blue (changed color)
    elif hours < 24:  # Changed time threshold
        return [50, 180, 50, 200]  # Green (changed color)
    else:
        return [200, 100, 50, 200]  # Orange (changed color)

seismic_data["LINE_COLOR"] = seismic_data["HOURS_BETWEEN"].apply(time_color_mapping)

# Sidebar filters with different organization
with st.sidebar:
    st.markdown("### 📊 Data Filters")
    
    # Magnitude filter with different design
    st.markdown("#### Magnitude Range")
    mag_min, mag_max = seismic_data["MAGNITUDE"].min(), seismic_data["MAGNITUDE"].max()
    mag_range = st.slider("", 
                         mag_min, 
                         mag_max, 
                         (mag_min, mag_max),
                         help="Filter events by magnitude")
    
    # Region filter with a different approach
    st.markdown("#### Region Selection")
    filter_mode = st.radio("Selection Mode:", ["All Regions", "Select Specific Regions"])
    
    if filter_mode == "All Regions":
        selected_regions = sorted(seismic_data["PROVINCE"].dropna().unique().tolist())
    else:
        # Show top regions by event count with different defaults
        top_regions = seismic_data["PROVINCE"].value_counts().nlargest(3).index.tolist()
        selected_regions = st.multiselect(
            "Select Regions to Show:",
            sorted(seismic_data["PROVINCE"].dropna().unique().tolist()),
            default=top_regions
        )
    
    # Date filter with a different layout
    st.markdown("#### Time Period")
    date_min, date_max = seismic_data["TIME"].min().date(), seismic_data["TIME"].max().date()
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From", date_min, min_value=date_min, max_value=date_max)
    with col2:
        end_date = st.date_input("To", date_max, min_value=date_min, max_value=date_max)

# Apply filters to create filtered dataset
filtered_data = seismic_data[
    (seismic_data["MAGNITUDE"] >= mag_range[0]) & 
    (seismic_data["MAGNITUDE"] <= mag_range[1]) &
    (seismic_data["PROVINCE"].isin(selected_regions)) &
    (seismic_data["TIME"].dt.date >= start_date) & 
    (seismic_data["TIME"].dt.date <= end_date)
]

# Show region statistics with different design
with st.sidebar:
    st.markdown("### 📋 Region Statistics")
    
    # Create a container for better styling
    stats_container = st.container()
    
    with stats_container:
        # Add a search box to filter regions (optional)
        if len(selected_regions) > 5:
            search_term = st.text_input("🔍 Filter regions", placeholder="Type to search...")
            display_regions = [r for r in selected_regions if search_term.lower() in r.lower()] if search_term else selected_regions
        else:
            display_regions = selected_regions
        
        # Show summary of all regions
        total_events = sum(len(filtered_data[filtered_data["PROVINCE"] == region]) for region in selected_regions)
        avg_all_mag = filtered_data["MAGNITUDE"].mean() if not filtered_data.empty else 0
        max_all_mag = filtered_data["MAGNITUDE"].max() if not filtered_data.empty else 0
        
        st.markdown(f"""
        <div style='background-color:rgba(51,102,204,0.1); padding:10px; border-radius:5px; margin:10px 0;'>
            <b>Summary</b>: {len(selected_regions)} regions | {total_events:,} events<br>
            Avg Magnitude: {avg_all_mag:.2f} | Max: {max_all_mag:.2f}
        </div>
        """, unsafe_allow_html=True)
        
        # Create better looking statistics cards for each region
        for i, region in enumerate(display_regions):
            region_data = filtered_data[filtered_data["PROVINCE"] == region]
            if not region_data.empty:
                event_count = len(region_data)
                avg_mag = region_data["MAGNITUDE"].mean()
                max_mag = region_data["MAGNITUDE"].max()
                
                # Calculate a color gradient based on event count or magnitude
                intensity = min(1.0, event_count / (total_events * 0.5 + 1)) if total_events > 0 else 0.1
                red = int(50 + intensity * 150)
                green = int(100 + intensity * 50) 
                blue = int(200 - intensity * 50)
                
                # Create a card with colored border based on intensity
                st.markdown(f"""
                <div style='background-color: white; 
                           padding: 12px; 
                           border-radius: 6px; 
                           margin: 8px 0;
                           border-left: 5px solid rgb({red},{green},{blue});
                           box-shadow: 0 1px 3px rgba(0,0,0,0.1);'>
                    <div style='display: flex; justify-content: space-between;'>
                        <span style='font-weight: bold; color: #3366cc;'>{region}</span>
                        <span style='color: #666; font-size: 0.9em;'>{event_count:,} events</span>
                    </div>
                    <div style='display: flex; justify-content: space-between; margin-top: 5px; font-size: 0.9em;'>
                        <span style='color: #666;'>Avg: {avg_mag:.2f}</span>
                        <span style='color: #666;'>Max: {max_mag:.2f}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # Show message if no regions match search
        if not display_regions:
            st.info("No regions match your search criteria.")
            
        # Add a note about the colors if there are many regions
        if len(selected_regions) > 3:
            st.caption("Color intensity indicates relative seismic activity level")

# Process sequential data by region with a different implementation
def create_sequential_connections(region_data):
    temp_df = region_data.sort_values("TIME").copy()
    
    # Create connections within same region
    temp_df["NEXT_LATITUDE"] = temp_df["LATITUDE"].shift(-1)
    temp_df["NEXT_LONGITUDE"] = temp_df["LONGITUDE"].shift(-1)
    temp_df["NEXT_TIME"] = temp_df["TIME"].shift(-1)
    
    # Time differences
    temp_df["HOURS_BETWEEN"] = (temp_df["NEXT_TIME"] - temp_df["TIME"]).dt.total_seconds() / 3600
    
    # Remove incomplete rows and color
    temp_df = temp_df.dropna(subset=["NEXT_LATITUDE", "NEXT_LONGITUDE", "HOURS_BETWEEN"])
    temp_df["LINE_COLOR"] = temp_df["HOURS_BETWEEN"].apply(time_color_mapping)
    
    return temp_df

# Process each region
sequential_data = pd.DataFrame()
for region in selected_regions:
    region_subset = filtered_data[filtered_data["PROVINCE"] == region]
    processed = create_sequential_connections(region_subset)
    sequential_data = pd.concat([sequential_data, processed])

# Create map layers with different configurations
with tab2:
    st.markdown("<h3 class='section-header'>Seismic Activity Map</h3>", unsafe_allow_html=True)
    
    # Show filtered count
    st.markdown(f"""
    <div style='margin:10px 0; background-color:rgba(51,102,204,0.1); padding:8px; border-radius:5px; display:inline-block;'>
        Currently displaying <b>{len(filtered_data):,}</b> seismic events
    </div>
    """, unsafe_allow_html=True)
    
    # Layer configuration with different options
    map_layers = {
        "Events (Circle)": pdk.Layer(
            "ScatterplotLayer",
            data=filtered_data,
            get_position=["LONGITUDE", "LATITUDE"],
            get_color=[220, 100, 100, 180],  # Changed color
            get_radius="MAGNITUDE * 12000",  # Changed scaling
            pickable=True,
            opacity=0.7,
            auto_highlight=True,
            highlight_color=[250, 250, 50, 180],
        ),
        "Density Heatmap": pdk.Layer(
            "HeatmapLayer",  # Changed from HexagonLayer
            data=filtered_data,
            get_position=["LONGITUDE", "LATITUDE"],
            get_weight="MAGNITUDE",
            aggregation="SUM",
            radius=35000,  # Changed radius
            opacity=0.7,
            pickable=True,
        ),
        "Magnitude Labels": pdk.Layer(
            "TextLayer",
            data=filtered_data,
            get_position=["LONGITUDE", "LATITUDE"],
            get_text="MAGNITUDE",
            get_size=16,
            get_color=[255, 255, 255],
            get_angle=0,
            get_alignment_baseline="'bottom'",
            pickable=False,
        ),
        "Event Sequence": pdk.Layer(
            "ArcLayer",
            data=sequential_data,
            get_source_position=["LONGITUDE", "LATITUDE"],
            get_target_position=["NEXT_LONGITUDE", "NEXT_LATITUDE"],
            get_source_color="LINE_COLOR",
            get_target_color="LINE_COLOR",
            auto_highlight=True,
            get_width="MAGNITUDE * 1.5",  # Changed scaling
            width_min_pixels=1.5,  # Changed
            width_max_pixels=15,  # Changed
            pickable=True,
        ),
    }
    
    # Layer selection with a different UI
    col1, col2 = st.columns(2)
    active_layers = []
    
    with col1:
        for i, (name, layer) in enumerate(list(map_layers.items())[:2]):
            if st.checkbox(name, True, key=f"layer_{i}"):
                active_layers.append(layer)
    
    with col2:
        for i, (name, layer) in enumerate(list(map_layers.items())[2:], start=2):
            if st.checkbox(name, True, key=f"layer_{i}"):
                active_layers.append(layer)
    
    # Map view settings with different defaults and options
    map_view = pdk.ViewState(
        latitude=12.8797,  
        longitude=121.7740,
        zoom=5.5,    
        pitch=35,  # Changed
        bearing=15  # Changed
    )
    
    # Map configuration with more compact UI
    col1, col2, col3 = st.columns(3)
    
    with col1:
        style = st.selectbox(
            "Map Base Style",
            options=[
                "mapbox://styles/mapbox/satellite-streets-v11",  # Changed
                "mapbox://styles/mapbox/dark-v10",
                "mapbox://styles/mapbox/light-v10",
                "mapbox://styles/mapbox/outdoors-v11",
            ],
            index=0
        )
    
    with col2:
        angle = st.slider("View Angle", 0, 60, 35)  # Changed default
    
    with col3:
        map_zoom = st.slider("Zoom Level", 3, 11, 5)  # Changed range
    
    # Update view settings
    map_view.pitch = angle
    map_view.zoom = map_zoom
    
    # Create and display map
    if active_layers:
        map_deck = pdk.Deck(
            map_style=style,
            initial_view_state=map_view,
            layers=active_layers,
            tooltip={
                "html": """
                <div style="background-color: rgba(42, 42, 42, 0.95); color: white; 
                     padding: 10px; border-radius: 5px; font-family: Arial; width: 280px;">
                    <div style="font-weight: bold; font-size: 14px;">{PROVINCE}</div>
                    <div style="margin: 5px 0;">
                        <span style="color: #aaa;">Magnitude:</span> {MAGNITUDE}
                    </div>
                    <div style="margin: 5px 0;">
                        <span style="color: #aaa;">Depth:</span> {DEPTH (KM)} km
                    </div>
                    <div style="margin: 5px 0;">
                        <span style="color: #aaa;">When:</span> {DISPLAY_TIME}
                    </div>
                </div>
                """
            }
        )
        
        st.pydeck_chart(map_deck, use_container_width=True)
        st.caption("Hover over events to see details. Use mouse wheel to zoom and drag to pan.")
    else:
        st.error("Please select at least one map layer to display.")

# Legend and information with different design
with tab2:
    st.markdown("<h3 class='section-header'>Map Legend & Information</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div style='background-color:#f8f8f8; padding:15px; border-radius:8px;'>
            <h4 style='color:#3366cc;'>Time Between Events</h4>
            <div class='legend-container'>
                <div class='legend-marker' style='background-color: rgba(50, 150, 255, 0.8);'></div>
                <div>Less than 2 hours</div>
            </div>
            <div class='legend-container'>
                <div class='legend-marker' style='background-color: rgba(50, 180, 50, 0.8);'></div>
                <div>2 - 24 hours</div>
            </div>
            <div class='legend-container'>
                <div class='legend-marker' style='background-color: rgba(200, 100, 50, 0.8);'></div>
                <div>More than 24 hours</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style='background-color:#f8f8f8; padding:15px; border-radius:8px;'>
            <h4 style='color:#3366cc;'>Earthquake Magnitude Scale</h4>
            <p>The size of circles on the map represents the magnitude of each earthquake.</p>
            <ul>
                <li><b>Minor:</b> 2.0 - 3.9</li>
                <li><b>Light:</b> 4.0 - 4.9</li>
                <li><b>Moderate:</b> 5.0 - 5.9</li>
                <li><b>Strong:</b> 6.0 - 6.9</li>
                <li><b>Major:</b> 7.0 or greater</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# Analytics tab with new content
with tab3:
    st.markdown("<h3 class='section-header'>Seismic Activity Analysis</h3>", unsafe_allow_html=True)
    
    # Monthly trend chart
    filtered_data["Month"] = filtered_data["TIME"].dt.strftime("%Y-%m")
    monthly_data = filtered_data.groupby("Month").agg({
        "MAGNITUDE": ["count", "mean", "max"]
    }).reset_index()
    monthly_data.columns = ["Month", "Events", "Avg_Magnitude", "Max_Magnitude"]
    
    st.markdown("#### Monthly Seismic Activity Trends")
    fig = px.line(monthly_data, x="Month", y=["Events", "Avg_Magnitude", "Max_Magnitude"],
                 title="Seismic Activity by Month",
                 labels={"value": "Value", "variable": "Metric"},
                 color_discrete_sequence=["#3366cc", "#ff9900", "#dc3912"])
    st.plotly_chart(fig, use_container_width=True)
    
    # Distribution by region
    region_data = filtered_data["PROVINCE"].value_counts().reset_index()
    region_data.columns = ["Province", "Event_Count"]
    region_data = region_data.sort_values("Event_Count", ascending=False).head(10)
    
    st.markdown("#### Top 10 Seismically Active Regions")
    fig = px.bar(region_data, x="Province", y="Event_Count", 
                color="Event_Count", color_continuous_scale="Blues",
                labels={"Province": "Region", "Event_Count": "Number of Events"})
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)