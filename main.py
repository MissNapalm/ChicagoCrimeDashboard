import folium
import sqlite3
import pandas as pd
from folium.plugins import HeatMap, MarkerCluster
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import calendar

def load_data():
    conn = sqlite3.connect('homicides.db')
    query = """
        SELECT *, 
        strftime('%w', Date) as day_of_week,
        strftime('%H', Date) as hour_of_day,
        strftime('%m', Date) as month
        FROM homicides 
        WHERE Latitude IS NOT NULL AND Longitude IS NOT NULL
    """
    data = pd.read_sql_query(query, conn)
    conn.close()
    
    # Convert date string to datetime
    data['Date'] = pd.to_datetime(data['Date'])
    
    # Add derived columns
    data['day_name'] = data['Date'].dt.day_name()
    data['hour'] = data['Date'].dt.hour
    data['month_name'] = data['Date'].dt.month_name()
    data['season'] = data['Date'].dt.month.map(lambda x: 
        'Winter' if x in [12, 1, 2] else
        'Spring' if x in [3, 4, 5] else
        'Summer' if x in [6, 7, 8] else 'Fall')
    
    return data

def initialize_map():
    return folium.Map(location=[41.8781, -87.6298], zoom_start=11)

def create_layers(data, map_object):
    year_layers = {}
    heatmap_layers = {}
    cluster_layers = {}
    
    for year in range(2020, 2025):
        cluster_layer = folium.FeatureGroup(name=f'cluster_year_{year}')
        marker_cluster = MarkerCluster()
        
        year_data = data[data['Year'] == year]
        
        for _, row in year_data.iterrows():
            folium.Marker(
                location=[row['Latitude'], row['Longitude']],
                popup=f"Case Number: {row['Case Number']}<br>Date: {row['Date']}<br>Description: {row['Description']}",
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(marker_cluster)
        
        marker_cluster.add_to(cluster_layer)
        
        heatmap_layer = folium.FeatureGroup(name=f'heatmap_year_{year}')
        heat_data = [[row['Latitude'], row['Longitude']] for _, row in year_data.iterrows()]
        HeatMap(heat_data, radius=15).add_to(heatmap_layer)
        
        cluster_layer.add_to(map_object)
        heatmap_layer.add_to(map_object)
        
        map_object.get_root().html.add_child(folium.Element(
            f"""
            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    document.querySelector('input[type="checkbox"][layername="heatmap_year_{year}"]').click();
                }});
            </script>
            """
        ))
        
        cluster_layers[str(year)] = cluster_layer
        heatmap_layers[str(year)] = heatmap_layer
    
    return cluster_layers, heatmap_layers

def create_analytics_html(data):
    # Define color scheme
    colors = {
        'primary': '#1f77b4',
        'secondary': '#ff7f0e',
        'accent': '#2ca02c',
        'background': '#f8f9fa',
        'text': '#2c3e50'
    }
    
    # 1. Day of Week Analysis
    dow_counts = data['day_name'].value_counts().reindex([
        'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
    ])
    
    fig_dow = go.Figure()
    fig_dow.add_trace(go.Bar(
        x=dow_counts.index,
        y=dow_counts.values,
        marker_color='rgba(31, 119, 180, 0.7)',
        hovertemplate='<b>%{x}</b><br>Homicides: %{y}<extra></extra>'
    ))
    fig_dow.update_layout(
        title={'text': 'Homicides by Day of Week', 'x': 0.5, 'xanchor': 'center'},
        paper_bgcolor='white',
        plot_bgcolor='white',
        height=400
    )

    # 2. Location Type Analysis
    location_counts = data['Location Description'].value_counts().head(10)
    
    fig_location = go.Figure()
    fig_location.add_trace(go.Bar(
        x=location_counts.values,
        y=location_counts.index,
        orientation='h',
        marker_color='rgba(255, 127, 14, 0.7)',
        hovertemplate='<b>%{y}</b><br>Homicides: %{x}<extra></extra>'
    ))
    fig_location.update_layout(
        title={'text': 'Top 10 Location Types', 'x': 0.5, 'xanchor': 'center'},
        paper_bgcolor='white',
        plot_bgcolor='white',
        height=400,
        margin=dict(l=200)  # Add left margin for location labels
    )

    # 3. Time of Day Analysis
    hour_counts = data['hour'].value_counts().sort_index()
    hour_labels = [f"{str(h%12 or 12)} {'AM' if h<12 else 'PM'}" for h in range(24)]
    hour_counts.index = hour_labels

    fig_time = go.Figure()
    fig_time.add_trace(go.Scatter(
        x=hour_counts.index,
        y=hour_counts.values,
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.2)',
        line=dict(color='rgb(31, 119, 180)', width=2),
        mode='lines+markers',
        hovertemplate='<b>%{x}</b><br>Homicides: %{y}<extra></extra>'
    ))
    fig_time.update_layout(
        title={'text': 'Homicides by Time of Day', 'x': 0.5, 'xanchor': 'center'},
        paper_bgcolor='white',
        plot_bgcolor='white',
        height=400,
        xaxis_tickangle=45
    )

    # 4. Seasonal Analysis
    season_counts = data['season'].value_counts()
    season_colors = ['#2980b9', '#27ae60', '#e74c3c', '#f39c12']
    
    fig_season = go.Figure()
    fig_season.add_trace(go.Pie(
        labels=season_counts.index,
        values=season_counts.values,
        marker=dict(colors=season_colors),
        textinfo='label+percent',
        hole=0.4
    ))
    fig_season.update_layout(
        title={'text': 'Homicides by Season', 'x': 0.5, 'xanchor': 'center'},
        paper_bgcolor='white',
        height=400
    )

    # Convert plots to HTML
    return f"""
    <div style="padding: 20px; background-color: #f5f5f5;">
        <h2 style="text-align: center; color: #2c3e50; font-size: 32px; margin-bottom: 30px;">
            Chicago Homicides Analytics Dashboard
        </h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 25px; margin-top: 20px;">
            <div style="background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                {fig_dow.to_html(full_html=False, include_plotlyjs=False)}
            </div>
            <div style="background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                {fig_location.to_html(full_html=False, include_plotlyjs=False)}
            </div>
            <div style="background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                {fig_time.to_html(full_html=False, include_plotlyjs=False)}
            </div>
            <div style="background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                {fig_season.to_html(full_html=False, include_plotlyjs=False)}
            </div>
        </div>
    </div>
    """

def add_control_panel(map_object):
    js_code = """
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        var isHeatmapMode = false;
        
        function toggleViewMode() {
            isHeatmapMode = !isHeatmapMode;
            var selectedYear = document.getElementById('yearSelect').value;
            updateLayers(selectedYear);
            
            document.getElementById('toggleButton').textContent = 
                isHeatmapMode ? 'Switch to Cluster View' : 'Switch to Heatmap View';
        }
        
        function updateLayers(selectedYear) {
            var layers = document.querySelectorAll('.leaflet-control-layers-overlays label');
            
            layers.forEach(function(layer) {
                var layerName = layer.querySelector('span').textContent.trim();
                var checkbox = layer.querySelector('input[type="checkbox"]');
                var isHeatmapLayer = layerName.startsWith('heatmap_');
                var isClusterLayer = layerName.startsWith('cluster_');
                var yearMatch = selectedYear === 'all' || layerName.endsWith(selectedYear);
                
                var shouldBeVisible = yearMatch && (
                    (isHeatmapMode && isHeatmapLayer) || 
                    (!isHeatmapMode && isClusterLayer)
                );
                
                if (shouldBeVisible && !checkbox.checked) {
                    checkbox.click();
                } else if (!shouldBeVisible && checkbox.checked) {
                    checkbox.click();
                }
            });
        }
        
        function filterByYear() {
            var selectedYear = document.getElementById('yearSelect').value;
            updateLayers(selectedYear);
        }
        
        window.filterByYear = filterByYear;
        window.toggleViewMode = toggleViewMode;
        
        filterByYear();
    });
    </script>
    """

    control_panel_html = """
    <div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); z-index: 1000; background-color: white; padding: 10px; border-radius: 5px; box-shadow: 0px 0px 10px rgba(0,0,0,0.1);">
        <div style="margin-bottom: 10px;">
            <label for="yearSelect">Select Year:</label>
            <select id="yearSelect">
                <option value="all">All Years</option>
                <option value="2020">2020</option>
                <option value="2021">2021</option>
                <option value="2022">2022</option>
                <option value="2023">2023</option>
                <option value="2024">2024</option>
            </select>
            <button onclick="filterByYear()">Update Year</button>
        </div>
        <div>
            <button id="toggleButton" onclick="toggleViewMode()">Switch to Heatmap View</button>
        </div>
    </div>
    """

    map_object.get_root().html.add_child(folium.Element(js_code + control_panel_html))

def save_dashboard(map_object, analytics_html, filename="chicago_homicides_dashboard.html"):
    map_html = map_object.get_root().render()
    
    dashboard_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chicago Homicides Dashboard</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: Arial, sans-serif;
            }}
            #map-container {{
                position: relative;
                height: 600px;
                width: 100%;
                margin-bottom: 20px;
                z-index: 1;
            }}
            #map {{
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
            }}
            #analytics-container {{
                position: relative;
                z-index: 2;
                background-color: #f5f5f5;
            }}
        </style>
    </head>
    <body>
        <div id="map-container">
            {map_html}
        </div>
        <div id="analytics-container">
            {analytics_html}
        </div>
    </body>
    </html>
    """
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(dashboard_html)
    
    print(f"Dashboard has been saved as {filename}")

def main():
    # Load and process data
    print("Loading data...")
    data = load_data()
    
    # Create map
    print("Creating map...")
    chicago_map = initialize_map()
    cluster_layers, heatmap_layers = create_layers(data, chicago_map)
    folium.LayerControl().add_to(chicago_map)
    add_control_panel(chicago_map)
    
    # Create analytics
    print("Creating analytics...")
    analytics_html = create_analytics_html(data)
    
    # Save complete dashboard
    print("Saving dashboard...")
    save_dashboard(chicago_map, analytics_html)
    print("Done! Open chicago_homicides_dashboard.html in your web browser to view the dashboard.")

if __name__ == "__main__":
    main()