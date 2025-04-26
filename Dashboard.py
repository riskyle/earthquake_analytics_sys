import streamlit as st

# Set page configuration
st.set_page_config(
    page_title="Earthquake Epicenter Density Heatmap",
    page_icon="🌍",
    layout="wide"
)

# Title and subtitle
st.markdown(
    """
    <h1 style="text-align: center; color: #d9534f;">🌍 Earthquake Epicenter Density Heatmap 🌋</h1>
    <p style="text-align: center; font-size: 18px; color: #5a5a5a;">
        Visualize and analyze the spatial distribution of earthquake epicenters through density heatmaps.
    </p>
    """, unsafe_allow_html=True
)

# Sidebar for navigation
st.sidebar.title("🔍 Explore Data")
st.sidebar.info("Use the filters to analyze earthquake epicenter density patterns across different regions and time periods.")

# Introduction
st.markdown("## 🔎 Overview")
st.info(
    "The Earthquake Epicenter Density Heatmap dashboard provides an interactive visualization of earthquake epicenter concentrations. "
    "This tool enables users to identify areas of high seismic activity by analyzing the spatial density of earthquake epicenters. "
    "Through dynamic heatmap generation, users can explore how earthquake epicenters are distributed across different geographical regions, "
    "time periods, and magnitude ranges. The heatmap visualization helps in identifying seismic hotspots and understanding patterns in "
    "earthquake occurrence. This application utilizes Streamlit to create an intuitive interface for analyzing complex seismic data "
    "through density-based heatmap visualizations."
)

# Feature Section
st.markdown("## ⚡ Key Features")
st.success(
    """
    - **🌋 Epicenter Density Heatmap:** Visualize the concentration of earthquake epicenters across regions.
    - **🎚️ Customizable Parameters:** Adjust heatmap intensity, radius, and color schemes.
    - **⏱️ Temporal Analysis:** Explore how epicenter density changes over time.
    - **📊 Magnitude-based Filtering:** Generate density heatmaps for specific magnitude ranges.
    - **🗺️ Regional Focus:** Zoom into specific areas to analyze local epicenter patterns.
    """
)

# Additional Information
st.markdown("## 📌 How to Use")
st.warning(
    "1. Select your desired time period and magnitude range from the sidebar.\n"
    "2. Choose the region of interest and adjust heatmap parameters.\n"
    "3. Generate the epicenter density heatmap visualization.\n"
    "4. Analyze the patterns to identify areas of high seismic activity.\n"
    "5. Use the interactive features to explore specific areas in detail."
)
