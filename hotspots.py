import folium
import sqlite3
import pandas as pd
import geopandas as gpd
import numpy as np
from folium import plugins
from branca.colormap import LinearColormap
import json
import requests
from shapely.geometry import Point

def load_chicago_neighborhoods():
    """Load Chicago community areas boundary data"""
    # Download Chicago community areas GeoJSON
    url = "https://data.cityofchicago.org/api/geospatial/cauq-8yn6?method=export&format=GeoJSON"
    try:
        response = requests.get(url)
        neighborhoods = gpd.GeoDataFrame.from_features(response.json()["features"])
        neighborhoods.crs = "EPSG:4326"  # Set coordinate reference system
        return neighborhoods
    except Exception as e:
        print(f"Error loading neighborhood data: {e}")
        return None

def load_crime_data():
    """Load crime data from SQLite database"""
    try:
        conn = sqlite3.connect('homicides.db')
        query = """
            SELECT Latitude, Longitude, Date, Year, "Case Number"
            FROM homicides 
            WHERE Latitude IS NOT NULL AND Longitude IS NOT NULL
        """
        crime_data = pd.read_sql_query(query, conn)
        conn.close()
        
        # Convert to GeoDataFrame
        geometry = [Point(xy) for xy in zip(crime_data.Longitude, crime_data.Latitude)]
        crime_gdf = gpd.GeoDataFrame(crime_data, geometry=geometry, crs="EPSG:4326")
        return crime_gdf
    except Exception as e:
        print(f"Error loading crime data: {e}")
        return None

def create_chloropleth_map():
    """Create chloropleth map of crime hotspots"""
    # Load data
    print("Loading neighborhood boundaries...")
    neighborhoods = load_chicago_neighborhoods()
    
    print("Loading crime data...")
    crime_data = load_crime_data()
    
    if neighborhoods is None or crime_data is None:
        print("Error: Could not load required data")
        return
    
    # Count crimes per neighborhood
    print("Analyzing crime patterns...")
    neighborhoods['crime_count'] = 0
    for idx, neighborhood in neighborhoods.iterrows():
        crime_count = sum(crime_data.geometry.within(neighborhood.geometry))
        neighborhoods.at[idx, 'crime_count'] = crime_count
    
    # Calculate crime rate per 1000 residents
    neighborhoods['crime_density'] = neighborhoods['crime_count'] / neighborhoods.geometry.area * 1e7
    
    # Create base map
    print("Creating chloropleth map...")
    m = folium.Map(
        location=[41.8781, -87.6298],
        zoom_start=11,
        tiles='cartodbpositron'
    )
    
    # Create color scale
    colors = ['#fee5d9', '#fcae91', '#fb6a4a', '#de2d26', '#a50f15']
    color_map = LinearColormap(
        colors=colors,
        vmin=neighborhoods['crime_density'].min(),
        vmax=neighborhoods['crime_density'].max(),
        caption='Crime Density (incidents per area)'
    )
    
    # Add chloropleth layer
    folium.GeoJson(
        neighborhoods,
        name='Crime Density',
        style_function=lambda feature: {
            'fillColor': color_map(feature['properties']['crime_density']),
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.7
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['community', 'crime_count', 'crime_density'],
            aliases=['Neighborhood:', 'Total Incidents:', 'Crime Density:'],
            localize=True,
            sticky=False,
            labels=True,
            style="""
                background-color: #F0EFEF;
                border: 2px solid black;
                border-radius: 3px;
                box-shadow: 3px;
            """
        )
    ).add_to(m)
    
    # Add color map to the map
    color_map.add_to(m)
    
    # Add custom legend
    legend_html = """
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 150px;
                    border:2px solid grey; z-index:9999; font-size:14px;
                    background-color:white;
                    padding: 10px;
                    border-radius: 5px;">
        <p style="margin-top: 0; margin-bottom: 5px;"><b>Crime Density</b></p>
        <p style="margin: 0;">
        Very High<br>
        High<br>
        Medium<br>
        Low<br>
        Very Low
        </p>
        </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add heatmap layer
    print("Adding heatmap layer...")
    heat_data = [[row['Latitude'], row['Longitude']] for idx, row in crime_data.iterrows()]
    plugins.HeatMap(heat_data, radius=15, blur=10).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Save map
    output_file = 'chicago_crime_hotspots.html'
    m.save(output_file)
    print(f"Map saved as {output_file}")
    
    # Print statistics
    print("\nCrime Statistics by Neighborhood:")
    stats = neighborhoods.nlargest(10, 'crime_count')[['community', 'crime_count', 'crime_density']]
    print("\nTop 10 Neighborhoods by Crime Count:")
    print(stats.to_string(index=False))

def main():
    try:
        print("Starting hotspot analysis...")
        create_chloropleth_map()
        print("\nAnalysis complete! Open chicago_crime_hotspots.html in your web browser to view the map.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main()