import streamlit as st 
import pandas as pd
import time
import plotly.express as px
import numpy as np
from datetime import timedelta
import plotly.graph_objects as go

# Set page config must be the first Streamlit command
st.set_page_config(
    page_title="Earthquake Time Series Animation", 
    page_icon="📈",
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
    .metric-container {
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        padding: 1rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #ff5733;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #666;
    }
    .chart-container {
        background-color: white;
        border-radius: 0.5rem;
        padding: 1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
    /* Custom sidebar styling */
    .sidebar .sidebar-content {
        background-color: #f5f5f5;
    }
    /* Divider style */
    .divider {
        margin: 2rem 0;
        border-bottom: 1px solid #eee;
    }
</style>
""", unsafe_allow_html=True)

# Improved header with better styling
st.markdown(
    """
    <h1 class='main-header'>📈 Earthquake Time Series Animation</h1>
    <p class='description'>
        Interactive animated visualization of earthquake data over time with customizable metrics and filters.
    </p>
    """, unsafe_allow_html=True
)

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
    df["DATE"] = pd.to_datetime(df["DATE"], dayfirst=True, errors="coerce")
    
    # Check if TIME column exists and merge with DATE
    if "TIME" in df.columns:
        df["TIME"] = df["TIME"].fillna("00:00:00")  # Default missing times to midnight
        df["DATETIME"] = pd.to_datetime(df["DATE"].astype(str) + " " + df["TIME"], errors="coerce")
    else:
        df["DATETIME"] = df["DATE"]  # Use DATE if no TIME column
    
    # Remove invalid dates and sort
    df = df.dropna(subset=["DATETIME"])
    df = df.sort_values("DATETIME")
    
    # Add year and month columns for time-based analysis
    df["YEAR"] = df["DATETIME"].dt.year
    df["MONTH"] = df["DATETIME"].dt.month
    df["MONTH_NAME"] = df["DATETIME"].dt.strftime("%b")
    df["DAY"] = df["DATETIME"].dt.day
    
    return df

# Show loading message
with st.spinner("Loading earthquake data..."):
    try:
        df = load_earthquake_data()
        
        # Check required columns
        required_columns = ['DATETIME', 'MAGNITUDE']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            st.error(f"CSV file missing required columns: {missing}")
            st.stop()
            
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.stop()

# Move filter options to sidebar with better organization
with st.sidebar:
    st.markdown(
        """
        <h2 style='color: #ff5733;'>🎛️ Filter Options</h2>
        <p style='color: gray;'>Customize your earthquake data visualization.</p>
        """, unsafe_allow_html=True
    )
    
    # Create expandable sections for different filter groups
    with st.expander("📍 Location Filters", expanded=True):
        # Get unique provinces
        province_options = ["All"] + sorted(df["PROVINCE"].dropna().unique().tolist())
        
        # Add province filter
        province_selected = st.selectbox("Select Province:", province_options)
        
        # Filter areas based on selected province
        if province_selected == "All":
            area_options = ["All"] + sorted(df["AREA"].dropna().unique().tolist())
        else:
            # Get only areas that belong to the selected province
            province_areas = df[df["PROVINCE"] == province_selected]["AREA"].dropna().unique().tolist()
            area_options = ["All"] + sorted(province_areas)
        
        # Add area filter
        area_selected = st.selectbox("Select Area:", area_options)
    
    with st.expander("📅 Time Filters", expanded=True):
        # Date range filter with more options
        min_date, max_date = df["DATETIME"].min(), df["DATETIME"].max()
        
        # Date range selection
        date_range_type = st.radio(
            "Select Date Range Type",
            ["Specific Dates", "Year", "Recent Period"],
            horizontal=True
        )
        
        if date_range_type == "Specific Dates":
            selected_date_range = st.date_input(
                "Select Date Range:", 
                [min_date.date(), max_date.date()], 
                min_value=min_date.date(), 
                max_value=max_date.date()
            )
            if len(selected_date_range) == 2:
                start_date, end_date = selected_date_range
            else:
                start_date, end_date = min_date.date(), max_date.date()
                
        elif date_range_type == "Year":
            years = sorted(df["YEAR"].unique())
            selected_year = st.selectbox("Select Year:", years, index=len(years)-1)
            year_df = df[df["YEAR"] == selected_year]
            start_date = year_df["DATETIME"].min().date()
            end_date = year_df["DATETIME"].max().date()
            st.info(f"Selected period: {start_date} to {end_date}")
            
        else:  # Recent Period
            period = st.slider("Recent months:", 1, 36, 6)
            end_date = max_date.date()
            start_date = (max_date - pd.DateOffset(months=period)).date()
            st.info(f"Selected period: {start_date} to {end_date}")
    
    with st.expander("📊 Data Metrics", expanded=True):
        # Available metrics for plotting
        available_metrics = ["MAGNITUDE"]
        if "DEPTH (KM)" in df.columns:
            available_metrics.append("DEPTH (KM)")
        if "INTENSITY" in df.columns:
            available_metrics.append("INTENSITY")
            
        # Set default metric to MAGNITUDE
        selected_metric = "MAGNITUDE"
        
        # Animation speed control
        animation_speed = st.slider(
            "Animation Speed:", 
            min_value=0.01, 
            max_value=0.2, 
            value=0.05, 
            step=0.01,
            help="Adjust how fast the time series animation plays"
        )

# Apply filters to create filtered dataset
filtered_df = df.copy()

# Apply date range filter
filtered_df = filtered_df[
    (filtered_df["DATETIME"].dt.date >= start_date) & 
    (filtered_df["DATETIME"].dt.date <= end_date)
]

# Apply location filters
if province_selected != "All":
    filtered_df = filtered_df[filtered_df["PROVINCE"] == province_selected]
if area_selected != "All":
    filtered_df = filtered_df[filtered_df["AREA"] == area_selected]

# Time Series Visualization
st.markdown("<h2 class='sub-header'>📈 Earthquake Time Series Animation</h2>", unsafe_allow_html=True)

# Check if filtered data is available
if not filtered_df.empty:
    # Description
    st.markdown(f"""
    <div class='info-box'>
        Visualizing {selected_metric} trends over time from {start_date} to {end_date}.
        This animated chart shows how earthquake {selected_metric.lower()} changed over the selected period.
    </div>
    """, unsafe_allow_html=True)
    
    # Create container for animated chart
    chart_container = st.container()
    
    # Progress bar and status
    progress_col1, progress_col2 = st.columns([3, 1])
    with progress_col1:
        progress_bar = st.progress(0)
    with progress_col2:
        status_text = st.empty()
    
    # Add animation controls
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        start_button = st.button("▶️ Start Animation", use_container_width=True)
    with col2:
        reset_button = st.button("🔄 Reset", use_container_width=True)
    with col3:
        show_static = st.checkbox("Show full chart without animation", value=False)
    
    # Create modern interactive Plotly time series chart (static version)
    if show_static:
        fig = px.line(
            filtered_df, 
            x="DATETIME", 
            y=selected_metric,
            line_shape="linear",
            title=f"Earthquake {selected_metric} Over Time",
            color_discrete_sequence=["#00bfff"]  # Light blue color
        )
        
        # Update layout for dark theme appearance
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title=selected_metric,
            hovermode="closest",
            plot_bgcolor="#121212",  # Dark background
            paper_bgcolor="#121212", # Dark background
            font=dict(
                family="Arial, sans-serif",
                color="white"  # White text
            ),
            showlegend=False,
            height=500,
            margin=dict(l=10, r=10, t=40, b=10),
            title={
                'font': {'color': 'white', 'size': 20},
                'x': 0.05,
                'xanchor': 'left'
            }
        )
        
        # Add grid lines
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(255, 255, 255, 0.1)",
            tickformat="%I %p",  # Hour AM/PM format
            tickangle=0,
            color="white"
        )
        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(255, 255, 255, 0.1)",
            color="white"
        )
        
        # Update the line appearance
        fig.update_traces(
            line=dict(width=1.5),
            hovertemplate=f"<b>{selected_metric}:</b> %{{y:.2f}}<br>" +
                         "<b>Date:</b> %{x|%d %b %Y %I:%M %p}<br>" +
                         "<extra></extra>"
        )
        
        # Display static chart
        chart_container.plotly_chart(fig, use_container_width=True)
        progress_bar.empty()
        status_text.empty()
        
    else:
        # Initialize the chart with first data point
        chart_placeholder = chart_container.empty()
        chart = chart_placeholder.line_chart(
            filtered_df.iloc[:1].set_index("DATETIME")[[selected_metric]],
            height=500
        )
        
        # Create animation function
        def animate_chart():
            # Reset progress
            progress_bar.progress(0)
            
            # Get total records for animation
            total_records = len(filtered_df)
            
            # Animate the data points
            for i in range(2, total_records + 1):
                # Add new data point
                new_data = filtered_df.iloc[i-1:i].set_index("DATETIME")[[selected_metric]]
                chart.add_rows(new_data)
                
                # Update progress
                progress = min(1.0, i / total_records)
                progress_bar.progress(progress)
                status_text.markdown(f"**{progress * 100:.0f}%** Complete")
                
                # Sleep for animation effect
                time.sleep(animation_speed)
            
            # Animation complete
            status_text.markdown("**100%** Complete")
        
        # Start animation if button clicked
        if start_button:
            animate_chart()
        
        # Reset chart if reset button clicked
        if reset_button:
            # Clear old chart and create a new one
            chart_placeholder.empty()
            chart = chart_placeholder.line_chart(
                filtered_df.iloc[:1].set_index("DATETIME")[[selected_metric]],
                height=500
            )
            progress_bar.progress(0)
            status_text.markdown("**0%** Reset Complete")
else:
    st.warning("No data available for the selected filters. Please adjust your filter criteria.")