import pandas as pd
import plotly.express as px
import streamlit as st
import altair as alt
import numpy as np
from datetime import timedelta
import plotly.graph_objects as go
import time
from scipy.stats import gaussian_kde

# Set page configuration
st.set_page_config(page_title="Earthquake Data Analysis", page_icon="📊", layout="wide")

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
</style>
""", unsafe_allow_html=True)

# Add a title with better styling
st.markdown("<h1 class='main-header'>Earthquake Data Analysis Dashboard</h1>", unsafe_allow_html=True)

# Add description
st.markdown("""
<p class='description'>
    Advanced analysis tools for earthquake data, including trend analysis and monthly distribution comparisons.
    Use the filters in the sidebar to customize your view and explore earthquake patterns.
</p>
""", unsafe_allow_html=True)

# Load the dataset
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
    df["DATE_ONLY"] = df["DATETIME"].dt.date
    
    return df

# Load data
with st.spinner("Loading earthquake data..."):
    try:
        df = load_earthquake_data()
        
        # Check required columns
        required_columns = ['DATETIME', 'MAGNITUDE', 'PROVINCE']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            st.error(f"CSV file missing required columns: {missing}")
            st.stop()
            
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.stop()

# Sidebar filters
with st.sidebar:
    st.markdown("""
    <h2 style='color: #ff5733;'>🎛️ Filter Options</h2>
    <p style='color: gray;'>Customize your earthquake data visualization.</p>
    """, unsafe_allow_html=True)
    
    # Create expandable sections for different filter groups
    with st.expander("📍 Location Filters", expanded=True):
        # Get unique provinces and sort them alphabetically
        unique_provinces = sorted(df["PROVINCE"].unique())
        
        # Add "Select All" option
        select_all = st.checkbox("Select All Provinces", False)
        
        if select_all:
            selected_provinces = unique_provinces
        else:
            # Default to top 5 provinces by earthquake count
            top_provinces = df["PROVINCE"].value_counts().head(5).index.tolist()
            selected_provinces = st.multiselect(
                "Select Provinces to Compare", 
                unique_provinces, 
                default=top_provinces
            )
    
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
            
        # Select metric to plot
        selected_metric = st.selectbox("Select Data to Plot:", available_metrics)
        
        # Category filter if available
        if "CATEGORY" in df.columns:
            st.markdown("### 🏷️ Category Filter")
            categories = sorted(df["CATEGORY"].unique())
            selected_categories = st.multiselect(
                "Select Categories", 
                categories,
                default=categories
            )
        else:
            selected_categories = None

# Filter data based on selections
filtered_df = df.copy()

# Apply date range filter
filtered_df = filtered_df[
    (filtered_df["DATETIME"].dt.date >= start_date) & 
    (filtered_df["DATETIME"].dt.date <= end_date)
]

# Apply province filter
filtered_df = filtered_df[filtered_df["PROVINCE"].isin(selected_provinces)]

# Apply category filter if available
if selected_categories is not None and "CATEGORY" in df.columns:
    filtered_df = filtered_df[filtered_df["CATEGORY"].isin(selected_categories)]

# Add metrics to the sidebar
with st.sidebar:
    st.markdown("### 📊 Current Selection")
    
    # Calculate metrics
    record_count = len(filtered_df)
    avg_magnitude = filtered_df["MAGNITUDE"].mean() if record_count > 0 else 0
    max_magnitude = filtered_df["MAGNITUDE"].max() if record_count > 0 else 0
    date_range_days = (end_date - start_date).days
    
    # Display metrics in a grid
    col1, col2 = st.columns(2)
    col1.metric("Total Records", f"{record_count:,}")
    col2.metric("Avg Magnitude", f"{avg_magnitude:.2f}")
    
    col3, col4 = st.columns(2)
    col3.metric("Max Magnitude", f"{max_magnitude:.2f}")
    col4.metric("Date Range", f"{date_range_days} days")

# Main content area with tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Magnitude by Category", 
    "📅 Monthly Distribution",
    "📈 Trend Analysis",
    "📊 Earthquake Magnitude Distribution"
])

# Tab 1: Magnitude by Category (keeping original functionality)
with tab1:
    if "CATEGORY" in filtered_df.columns:
        # Group by category and province, then compute average magnitude
        province_magnitude_category = filtered_df.groupby(["CATEGORY", "PROVINCE"]).agg({"MAGNITUDE": "mean"}).reset_index()

        # Create a bar chart comparing magnitude by category
        fig2 = px.bar(
            province_magnitude_category, 
            x="CATEGORY", 
            y="MAGNITUDE", 
            color="PROVINCE", 
            title="Average Earthquake Magnitude by Category and Province",
            labels={"MAGNITUDE": "Average Magnitude", "CATEGORY": "Earthquake Category"},
            barmode="group",
            template="plotly_dark"  # Add dark theme template
        )
        
        # Improve chart layout with dark theme
        fig2.update_layout(
            legend_title="Province",
            xaxis_title="Earthquake Category",
            yaxis_title="Average Magnitude",
            height=500,
            paper_bgcolor="#111111",
            plot_bgcolor="#111111",
            font=dict(family="Arial, sans-serif", color="white"),
            title_font=dict(size=20, color="white"),
            title_x=0.5
        )
        
        # Add grid lines with appropriate color for dark background
        fig2.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(255, 255, 255, 0.1)",
            tickangle=45,
            title_font=dict(size=14, color="white"),
            tickfont=dict(size=12, color="white")
        )
        fig2.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(255, 255, 255, 0.1)",
            title_font=dict(size=14, color="white"),
            tickfont=dict(size=12, color="white")
        )

        # Display the chart
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("Category information not available in the dataset.")

# Tab 2: Monthly Distribution
with tab2:
    st.markdown("<h2 class='sub-header'>📅 Monthly Distribution Analysis</h2>", unsafe_allow_html=True)
    
    if not filtered_df.empty:
        # Group data by month
        monthly_df = filtered_df.copy()
        
        # Allow the user to select which province to analyze
        province_for_monthly = st.selectbox(
            "Select Province for Monthly Analysis:", 
            ["All Provinces"] + selected_provinces
        )
        
        if province_for_monthly != "All Provinces":
            monthly_df = monthly_df[monthly_df["PROVINCE"] == province_for_monthly]
        
        monthly_counts = monthly_df.groupby(["YEAR", "MONTH", "MONTH_NAME"]).size().reset_index(name="COUNT")
        monthly_avg_mag = monthly_df.groupby(["YEAR", "MONTH", "MONTH_NAME"])[selected_metric].mean().reset_index(name="AVG_MAGNITUDE")
        
        # Merge the datasets
        monthly_data = pd.merge(monthly_counts, monthly_avg_mag, on=["YEAR", "MONTH", "MONTH_NAME"])
        
        # Sort by year and month for proper ordering
        monthly_data = monthly_data.sort_values(["YEAR", "MONTH"])
        
        # Create year selector for monthly distribution
        years = sorted(monthly_data["YEAR"].unique())
        selected_years = st.multiselect(
            "Select Years to Compare:", 
            options=years,
            default=years[-1:] if years else [],
            help="Choose one or more years to compare monthly earthquake patterns"
        )
        
        if not selected_years:
            st.warning("Please select at least one year to display monthly distribution.")
        else:
            # Filter data for selected years
            year_filtered_data = monthly_data[monthly_data["YEAR"].isin(selected_years)]
            
            # Create two columns for the charts
            col1, col2 = st.columns(2)
            
            with col1:
                # Monthly earthquake count chart
                fig1 = px.bar(
                    year_filtered_data,
                    x="MONTH_NAME",
                    y="COUNT",
                    color="YEAR",
                    barmode="group",
                    title=f"Monthly Earthquake Count ({province_for_monthly})",
                    labels={"COUNT": "Number of Earthquakes", "MONTH_NAME": "Month", "YEAR": "Year"},
                    text_auto=True,
                    color_discrete_sequence=px.colors.qualitative.Bold,
                    template="plotly_dark"  # Add dark theme
                )
                
                # Fix color scale when only one year is selected
                if len(selected_years) == 1:
                    # For single year, use a solid color instead of a gradient
                    year_val = selected_years[0]
                    fig1.update_traces(marker_color="#E377C2")  # Use a solid pink color
                    # Update legend to show just the year without decimals
                    fig1.data[0].name = str(int(year_val))
                    # Completely hide the legend for a cleaner look
                    fig1.update_layout(showlegend=False)
                else:
                    # For multiple years, make sure legend is prominent and visible
                    # Convert all year values to integers in the legend
                    for i, trace in enumerate(fig1.data):
                        if isinstance(trace.name, (int, float)):
                            fig1.data[i].name = str(int(trace.name))
                    
                    # Set legend to a visible position that doesn't overlap with bars
                    fig1.update_layout(
                        legend=dict(
                            orientation="v",  # Vertical orientation
                            yanchor="top",
                            y=0.99,
                            xanchor="right",
                            x=0.99,
                            bgcolor="rgba(17, 17, 17, 0.8)",
                            bordercolor="rgba(255, 255, 255, 0.3)",
                            borderwidth=1,
                            font=dict(size=14, color="white"),
                            title_font=dict(size=16, color="white")
                        ),
                        showlegend=True  # Explicitly show legend
                    )
                
                # Update layout with dark theme
                fig1.update_layout(
                    xaxis=dict(
                        categoryorder="array",
                        categoryarray=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                        gridcolor="rgba(255, 255, 255, 0.1)",
                        tickfont=dict(color="white")
                    ),
                    yaxis=dict(
                        gridcolor="rgba(255, 255, 255, 0.1)",
                        tickfont=dict(color="white")
                    ),
                    yaxis_title="Earthquake Count",
                    xaxis_title="Month",
                    legend_title="Year",
                    height=500,
                    paper_bgcolor="#111111",
                    plot_bgcolor="#111111",
                    font=dict(family="Arial, sans-serif", color="white"),
                    title_font=dict(size=18, color="white"),
                    title_x=0.5,
                    coloraxis_showscale=False  # Hide color scale when redundant
                )
                
                # Improve legend visibility for multiple years
                if len(selected_years) > 1:
                    fig1.update_layout(
                        legend=dict(
                            orientation="v",
                            yanchor="top",
                            y=0.99,
                            xanchor="right",
                            x=0.99,
                            bgcolor="rgba(17, 17, 17, 0.8)",
                            bordercolor="rgba(255, 255, 255, 0.3)",
                            borderwidth=1,
                            font=dict(size=14, color="white"),
                            title_font=dict(size=16, color="white")
                        ),
                        showlegend=True  # Explicitly show legend for multiple years
                    )
                
                # Display the chart
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # Monthly average magnitude chart
                fig2 = px.line(
                    year_filtered_data,
                    x="MONTH_NAME",
                    y="AVG_MAGNITUDE",
                    color="YEAR",
                    markers=True,
                    title=f"Monthly Average {selected_metric} ({province_for_monthly})",
                    labels={"AVG_MAGNITUDE": f"Avg. {selected_metric}", "MONTH_NAME": "Month", "YEAR": "Year"},
                    color_discrete_sequence=px.colors.qualitative.Bold,
                    template="plotly_dark"  # Add dark theme
                )
                
                # Fix color scale when only one year is selected
                if len(selected_years) == 1:
                    # For single year, use a solid color instead of a gradient
                    year_val = selected_years[0]
                    fig2.update_traces(line_color="#E377C2", marker_color="#E377C2")  # Use a solid pink color
                    # Update legend to show just the year without decimals
                    fig2.data[0].name = str(int(year_val))
                    # Completely hide the legend for a cleaner look
                    fig2.update_layout(showlegend=False)
                
                # Update layout with dark theme
                fig2.update_layout(
                    xaxis=dict(
                        categoryorder="array",
                        categoryarray=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                        gridcolor="rgba(255, 255, 255, 0.1)",
                        tickfont=dict(color="white")
                    ),
                    yaxis=dict(
                        gridcolor="rgba(255, 255, 255, 0.1)",
                        tickfont=dict(color="white")
                    ),
                    yaxis_title=f"Average {selected_metric}",
                    xaxis_title="Month",
                    legend_title="Year",
                    height=500,
                    paper_bgcolor="#111111",
                    plot_bgcolor="#111111",
                    font=dict(family="Arial, sans-serif", color="white"),
                    title_font=dict(size=18, color="white"),
                    title_x=0.5,
                    coloraxis_showscale=False  # Hide color scale when redundant
                )
                
                # Improve legend visibility for multiple years
                if len(selected_years) > 1:
                    fig2.update_layout(
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="center",
                            x=0.5,
                            bgcolor="rgba(17, 17, 17, 0.7)",
                            bordercolor="rgba(255, 255, 255, 0.2)",
                            borderwidth=1,
                            font=dict(size=12, color="white"),
                            title_font=dict(size=14, color="white")
                        ),
                        showlegend=True  # Explicitly show legend for multiple years
                    )
                
                # Ensure years are displayed as integers in the legend
                for trace in fig2.data:
                    if isinstance(trace.name, (int, float)):
                        trace.name = str(int(trace.name))
                
                # Display the chart
                st.plotly_chart(fig2, use_container_width=True)
            
            # Show summary statistics
            st.markdown("<h3 class='sub-header'>📊 Yearly Comparison</h3>", unsafe_allow_html=True)
            
            # Create yearly summary statistics
            yearly_summary = monthly_data[monthly_data["YEAR"].isin(selected_years)].groupby("YEAR").agg({
                "COUNT": "sum",
                "AVG_MAGNITUDE": "mean"
            }).reset_index()
            
            yearly_summary.columns = ["Year", "Total Earthquakes", "Average Magnitude"]
            
            # Calculate percentage change from previous year if multiple years selected
            if len(selected_years) > 1 and len(yearly_summary) > 1:
                yearly_summary = yearly_summary.sort_values("Year")
                yearly_summary["% Change in Count"] = yearly_summary["Total Earthquakes"].pct_change() * 100
                yearly_summary["% Change in Magnitude"] = yearly_summary["Average Magnitude"].pct_change() * 100
                
                # Format percentage columns
                yearly_summary["% Change in Count"] = yearly_summary["% Change in Count"].apply(
                    lambda x: f"{x:+.1f}%" if not pd.isna(x) else "N/A"
                )
                yearly_summary["% Change in Magnitude"] = yearly_summary["% Change in Magnitude"].apply(
                    lambda x: f"{x:+.1f}%" if not pd.isna(x) else "N/A"
                )
            
            # Display yearly summary
            st.dataframe(
                yearly_summary.sort_values("Year", ascending=False),
                use_container_width=True,
                hide_index=True
            )

# Tab 3: Trend Analysis (from Earthquake_Plotting.py)
with tab3:
    st.markdown("<h2 class='sub-header'>📊 Earthquake Trend Analysis</h2>", unsafe_allow_html=True)
    
    if not filtered_df.empty:
        # Create control settings for visualization
        st.markdown("### Visualization Controls")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Create rolling average settings
            rolling_window = st.slider(
                "Rolling Average Window (days):", 
                min_value=1, 
                max_value=90, 
                value=7,
                help="Number of days to use for calculating moving average"
            )
        
        with col2:
            # Point opacity control
            point_opacity = st.slider(
                "Point Opacity:", 
                min_value=0.1, 
                max_value=1.0, 
                value=0.6,
                step=0.1,
                help="Control the transparency of data points"
            )
            
            # Point size control
            point_size = st.slider(
                "Point Size:", 
                min_value=2, 
                max_value=10, 
                value=6,
                help="Control the size of data points"
            )
        
        with col3:
            # Line width control
            line_width = st.slider(
                "Line Width:", 
                min_value=1, 
                max_value=5, 
                value=3,
                help="Control the width of trend lines"
            )
            
            # Show data points option
            show_points = st.checkbox("Show Data Points", value=True, 
                                     help="Toggle to show/hide individual earthquake data points")
        
        # Additional controls for better visualization
        st.markdown("### Filter Controls")
        col1, col2 = st.columns(2)
        
        with col1:
            # Filter by magnitude option
            min_magnitude = filtered_df["MAGNITUDE"].min()
            max_magnitude = filtered_df["MAGNITUDE"].max()
            magnitude_range = st.slider(
                "Magnitude Range:", 
                min_value=float(min_magnitude), 
                max_value=float(max_magnitude),
                value=(float(min_magnitude), float(max_magnitude)),
                step=0.1
            )
        
        with col2:
            # Option to limit number of points for better performance
            limit_points = st.checkbox("Limit Data Points for Better Performance", value=False)
            if limit_points:
                max_points = st.slider(
                    "Maximum Points per Province:", 
                    min_value=100, 
                    max_value=5000, 
                    value=1000,
                    step=100
                )
        
        # Add explanation
        st.info("📝 **Tip:** Use the controls above to adjust how the trend analysis is displayed. Reducing opacity or limiting data points can help clarify patterns in dense data.")
        
        # Calculate rolling average
        # First, set datetime as index for rolling calculation
        trend_df = filtered_df.set_index("DATETIME").sort_index()
        trend_df[f"{selected_metric}_Rolling_Avg"] = trend_df[selected_metric].rolling(f"{rolling_window}D").mean()
        trend_df = trend_df.reset_index()
        
        # Apply magnitude filter
        trend_df = trend_df[(trend_df[selected_metric] >= magnitude_range[0]) & 
                           (trend_df[selected_metric] <= magnitude_range[1])]
        
        # Create trend visualization using Plotly
        fig = go.Figure()
        
        # Create separate traces for each province
        for province in selected_provinces:
            province_data = trend_df[trend_df["PROVINCE"] == province]
            
            # Optionally limit points for better performance
            if limit_points and len(province_data) > max_points:
                # Sampling strategy that preserves temporal distribution
                province_data = province_data.sort_values("DATETIME")
                step = len(province_data) // max_points
                indices = np.arange(0, len(province_data), step)
                province_data = province_data.iloc[indices].copy()
            
            # Add scatter plot for province data points if enabled
            if show_points:
                fig.add_trace(
                    go.Scatter(
                        x=province_data["DATETIME"],
                        y=province_data[selected_metric],
                        mode="markers",
                        name=f"{province}",
                        marker=dict(
                            size=point_size,
                            opacity=point_opacity
                        ),
                        hovertemplate="<b>Date:</b> %{x|%d %b %Y}<br>" +
                                    f"<b>{selected_metric}:</b> %{{y:.2f}}<br>" +
                                    "<b>Province:</b> " + province + "<br>" +
                                    "<extra></extra>"
                    )
                )
            
            # Add rolling average line for the province
            fig.add_trace(
                go.Scatter(
                    x=province_data["DATETIME"],
                    y=province_data[f"{selected_metric}_Rolling_Avg"],
                    mode="lines",
                    name=f"{province} (Avg)",
                    line=dict(width=line_width),
                    hovertemplate="<b>Date:</b> %{x|%d %b %Y}<br>" +
                                f"<b>{rolling_window}-Day Avg:</b> %{{y:.2f}}<br>" +
                                "<b>Province:</b> " + province + "<br>" +
                                "<extra></extra>"
                )
            )
        
        # Update layout for better appearance with dark theme
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#111111",
            plot_bgcolor="#111111",
            title=f"{selected_metric} Trend Analysis",
            title_font=dict(size=20, color="white"),
            title_x=0.5,
            xaxis_title="Date",
            yaxis_title=selected_metric,
            font=dict(family="Arial, sans-serif", color="white"),
            hovermode="closest",
            height=600,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1.0,
                xanchor="right",
                x=1.1,
                font=dict(size=10, color="white"),
                itemsizing="constant",
                traceorder="grouped"
            ),
            margin=dict(r=150)  # Add right margin for legend
        )
        
        # Add subtitle for rolling average information
        fig.add_annotation(
            text=f"Using {rolling_window}-Day Rolling Average",
            xref="paper",
            yref="paper",
            x=0.5,
            y=1.05,
            showarrow=False,
            font=dict(size=14, color="white"),
            opacity=0.8
        )
        
        # Add grid lines
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(255, 255, 255, 0.1)",
            tickangle=45,
            title_font=dict(size=14),
            tickfont=dict(size=12)
        )
        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(255, 255, 255, 0.1)",
            title_font=dict(size=14),
            tickfont=dict(size=12)
        )
        
        # Display the trend chart
        st.plotly_chart(fig, use_container_width=True)
        
        # Add descriptive statistics
        st.markdown("<h3 class='sub-header'>📊 Statistical Analysis</h3>", unsafe_allow_html=True)
        
        # Calculate statistics
        stats_df = filtered_df.copy()
        
        # Group by year-month for trend analysis
        stats_df["YearMonth"] = stats_df["DATETIME"].dt.strftime("%Y-%m")
        monthly_stats = stats_df.groupby(["PROVINCE", "YearMonth"]).agg({
            selected_metric: ["count", "mean", "median", "min", "max", "std"]
        }).reset_index()
        
        # Rename columns for clarity
        monthly_stats.columns = ["Province", "Year-Month", "Count", "Average", "Median", "Minimum", "Maximum", "Std Dev"]
        
        # Display statistics table
        st.markdown("### Monthly Statistics by Province")
        
        # Province selector for detailed statistics
        province_for_stats = st.selectbox("Select Province for Detailed Statistics:", selected_provinces)
        province_stats = monthly_stats[monthly_stats["Province"] == province_for_stats]
        
        st.dataframe(
            province_stats.sort_values("Year-Month", ascending=False),
            use_container_width=True,
            hide_index=True
        )

# Tab 4: Magnitude Distribution
with tab4:
    st.markdown("<h2 class='sub-header'>📊 Earthquake Magnitude Distribution</h2>", unsafe_allow_html=True)
    
    if not filtered_df.empty:
        # Distribution visualization with Plotly
        
        # Magnitude histogram
        fig1 = go.Figure()
        
        for province in selected_provinces:
            province_data = filtered_df[filtered_df["PROVINCE"] == province]
            
            fig1.add_trace(
                go.Histogram(
                    x=province_data["MAGNITUDE"],
                    name=province,
                    opacity=0.7,
                    bingroup="group",
                    nbinsx=20
                )
            )
        
        # Update layout with dark theme
        fig1.update_layout(
            template="plotly_dark",
            paper_bgcolor="#111111",
            plot_bgcolor="#111111",
            title="Magnitude Distribution",
            title_font=dict(size=20, color="white"),
            title_x=0.5,
            xaxis_title="Magnitude",
            yaxis_title="Frequency",
            barmode="overlay",
            font=dict(family="Arial, sans-serif", color="white"),
            height=500,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=12, color="white")
            )
        )
        
        # Add grid lines
        fig1.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(255, 255, 255, 0.1)",
            title_font=dict(size=14),
            tickfont=dict(size=12)
        )
        fig1.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(255, 255, 255, 0.1)",
            title_font=dict(size=14),
            tickfont=dict(size=12)
        )
        
        st.plotly_chart(fig1, use_container_width=True)
        
        # KDE plot option
        if st.checkbox("Show Kernel Density Estimation (KDE)"):
            fig2 = go.Figure()
            
            for province in selected_provinces:
                province_data = filtered_df[filtered_df["PROVINCE"] == province]
                
                # Use numpy to create KDE
                if len(province_data) > 5:  # Need sufficient data for KDE
                    magnitude_data = province_data["MAGNITUDE"].values
                    kde_x = np.linspace(magnitude_data.min(), magnitude_data.max(), 1000)
                    kde = gaussian_kde(magnitude_data)
                    kde_y = kde(kde_x)
                    
                    fig2.add_trace(
                        go.Scatter(
                            x=kde_x,
                            y=kde_y,
                            name=province,
                            mode="lines",
                            line=dict(width=2)
                        )
                    )
            
            # Update layout with dark theme
            fig2.update_layout(
                template="plotly_dark",
                paper_bgcolor="#111111",
                plot_bgcolor="#111111",
                title="Magnitude Density Estimation (KDE)",
                title_font=dict(size=20, color="white"),
                title_x=0.5,
                xaxis_title="Magnitude",
                yaxis_title="Density",
                font=dict(family="Arial, sans-serif", color="white"),
                height=500,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    font=dict(size=12, color="white")
                )
            )
            
            # Add grid lines
            fig2.update_xaxes(
                showgrid=True,
                gridwidth=1,
                gridcolor="rgba(255, 255, 255, 0.1)",
                title_font=dict(size=14),
                tickfont=dict(size=12)
            )
            fig2.update_yaxes(
                showgrid=True,
                gridwidth=1,
                gridcolor="rgba(255, 255, 255, 0.1)",
                title_font=dict(size=14),
                tickfont=dict(size=12)
            )
            
            st.plotly_chart(fig2, use_container_width=True)

# Add a footer with information
st.markdown("""
<div class="divider"></div>
<p style="text-align: center; color: #666; font-size: 0.8rem;">
    Earthquake Data Analysis Dashboard | Data source: Philippine Seismological Network
</p>
""", unsafe_allow_html=True)
