# -*- coding: utf-8 -*-
###############################################################################
# Credit Agricole Risk Dashboard
###############################################################################

#==============================================================================
# Initiating
#==============================================================================

# Libraries
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import branca.colormap as cm
import plotly.express as px
import plotly.graph_objs as go
import os


st.set_page_config(layout="wide") 

# Set directory
base_dir = '/streamlit_files'
os.chdir(base_dir)

# Load data
inseedf = pd.read_csv('insee_df.csv')
inseedf['geometry'] = gpd.GeoSeries.from_wkt(inseedf['geometry'])
inseedf['Code INSEE'] = inseedf['Code INSEE'].astype(str).str.strip()


#==============================================================================
# Header
#==============================================================================

def render_header():
    """
    This function render the header of the dashboard with the following items:
        - Title
        - Dashboard description
    """
    
    # Define the columns for layout
    col1, col2, col3 = st.columns([1, 200, 1100]) 
    
    # Add image to col1
    with col1:
        st.markdown(
            """
            <div style='background-color: white; padding: 7px; display: inline-block;'>
                <img src="https://logo-marque.com/wp-content/uploads/2021/03/Credit-Agricole-Logo.png" width="150">
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Add title to col3
    with col3:
        st.title("PréviRisque - Nord Pas De Calais")
        
# Cached function for tab1  
@st.cache_data
def tab1_cache():
    existing_df = pd.read_csv('coul_predictions.csv')
    existing_df['Code INSEE'] = existing_df['Code INSEE'].astype(str).str.strip()
    return existing_df

@st.cache_data
def tab2_cache():
    existing_df = pd.read_csv('rem_predictions.csv')
    existing_df['Code INSEE'] = existing_df['Code INSEE'].astype(str).str.strip()
    return existing_df

@st.cache_data
def tab3_cache():
    existing_df = pd.read_csv('sech_predictions.csv')
    existing_df['Code INSEE'] = existing_df['Code INSEE'].astype(str).str.strip()
    return existing_df
    
@st.cache_data
def load_historical():
    historical_risk_path = 'historical_risk.csv'
    historical_risk = pd.read_csv(historical_risk_path)
    historical_risk['Code INSEE'] = historical_risk['Code INSEE'].astype(str).str.strip()
    historical_risk = historical_risk.groupby('Code INSEE').first().reset_index()
    historical_risk['normalized_historical_risk_score'] = historical_risk['normalized_historical_risk_score'].round(4)
    return historical_risk

@st.cache_data
def inon_events():
    events_df = pd.read_csv('inon_events.csv')
    events_df['dat_deb'] = pd.to_datetime(events_df['dat_deb'])
    events_df['dat_fin'] = pd.to_datetime(events_df['dat_fin'])
    events_df['duration'] = (events_df['dat_fin'] - events_df['dat_deb']).dt.days + 1
    return events_df

@st.cache_data
def sech_events():
    events_df = pd.read_csv('sech_events.csv')
    events_df['dat_deb'] = pd.to_datetime(events_df['dat_deb'])
    events_df['dat_fin'] = pd.to_datetime(events_df['dat_fin'])
    events_df['duration'] = (events_df['dat_fin'] - events_df['dat_deb']).dt.days + 1
    return events_df

@st.cache_data
def cat_events():
    events_df = pd.read_csv('cat_events.csv')
    events_df['dat_deb'] = pd.to_datetime(events_df['dat_deb'])
    return events_df


#==============================================================================
# Tab 1
#==============================================================================
# Function to get the column for the selected year
def get_selected_column(prefix, selected_year):
    return f"{prefix}{selected_year}"

def render_tab1():
    """
    This function renders Tab 1 - Map of risks at INSEE level
    """
    
    existing_df1 = tab1_cache()
    existing_df2 = tab2_cache()
    existing_df3 = tab3_cache()
    historical_risk = load_historical()

    # Identify the year columns
    year_columns = [col for col in existing_df1.columns if col.startswith('event_intensity_coul_')]
    year_options = [col.split('_')[-1] for col in year_columns]

    # Create a select box for the year selection
    selected_year = st.selectbox("Sélectionnez l'année:", options=year_options, key="select_year1")

   # Merge the dataframes with inseedf to get 'Commune' and 'geometry'
    df1 = inseedf.merge(existing_df1[['Code INSEE', get_selected_column('event_intensity_coul_', selected_year)]], on='Code INSEE').rename(columns={get_selected_column('event_intensity_coul_', selected_year): 'risk_coul'})
    df2 = inseedf.merge(existing_df2[['Code INSEE', get_selected_column('event_intensity_rem_', selected_year)]], on='Code INSEE').rename(columns={get_selected_column('event_intensity_rem_', selected_year): 'risk_rem'})
    df3 = inseedf.merge(existing_df3[['Code INSEE', get_selected_column('event_intensity_sech_', selected_year)]], on='Code INSEE').rename(columns={get_selected_column('event_intensity_sech_', selected_year): 'risk_sech'})
    
    # Round the risk scores
    df1['risk_coul'] = df1['risk_coul'].round(4)
    df2['risk_rem'] = df2['risk_rem'].round(4)
    df3['risk_sech'] = df3['risk_sech'].round(4)
    
    # Merge the historical risk data
    df_combined = df1.merge(df2[['Code INSEE', 'risk_rem']], on='Code INSEE').merge(df3[['Code INSEE', 'risk_sech']], on='Code INSEE').merge(historical_risk[['Code INSEE', 'normalized_historical_risk_score']], on='Code INSEE')

    # Create a GeoDataFrame
    gdf = gpd.GeoDataFrame(df_combined, geometry='geometry')
    
    gdf['average_risk'] = gdf[['risk_coul', 'risk_rem', 'risk_sech', 'normalized_historical_risk_score']].mean(axis=1).round(4)

    # Create colormap
    colormap = cm.LinearColormap(colors=['#FFFFB2','#FFD700', '#FFC300','#FFB000', '#FF8C00', '#FF7000', '#FF4500', '#FF2400', '#FF0000', '#CC0000','#8B0000'], vmin=gdf['average_risk'].min(), vmax=gdf['average_risk'].max())

    commune_names = [''] + gdf['Commune'].unique().tolist() 
    selected_commune = st.selectbox("Entrez le nom de la commune:", options=commune_names, key="select_commune1", index=0)
    
    # Create a Folium map
    m = folium.Map(location=[50.6292, 3.0573], zoom_start=8)  
    
    selected_geom = None
    selected_geojson = None

    for _, row in gdf.iterrows():
        geom = row['geometry']
        if geom.is_empty or geom is None:
            continue
        color = colormap(row['average_risk'])
        tooltip_text = (
            f"<div style='font-size: 16px;'><b>INSEE:</b> {row['Code INSEE']}<br><b>Commune:</b> {row['Commune']}<br>"
            f"<b>Risque Inondations et/ou coulées de boue ({selected_year}):</b> {row['risk_coul']}<br>"
            f"<b>Risque Inondations remontée nappe ({selected_year}):</b> {row['risk_rem']}<br>"
            f"<b>Risque Sécheresse ({selected_year}):</b> {row['risk_sech']}<br>"
            f"<b>Risque Historique:</b> {row['normalized_historical_risk_score']}<br>"
            f"<b>Risque Moyen:</b> {row['average_risk']}<br>"
            f"<b>Niveau de risque :</b> 0 (Aucun risque) - (Risque maximum) 1:</div>"
        )
        geojson = folium.GeoJson(
            data=geom,
            tooltip=tooltip_text,
            style_function=lambda x, color=color: {
                'fillColor': color, 'color': 'black', 'weight': 0.5, 'fillOpacity': 0.8
            },
            name=row['Commune']
        ).add_to(m)
        
        if row['Commune'] == selected_commune:
            selected_geom = geom
            selected_geojson = geojson
            folium.GeoJson(
                data=geom,
                style_function=lambda x: {'fillColor': 'orange', 'color': 'black', 'weight': 0.5, 'fillOpacity': 0.6}
            ).add_to(m)
            popup = folium.Popup(tooltip_text, max_width=300)
            marker = folium.Marker(
                location=[geom.centroid.y, geom.centroid.x],
                icon=folium.Icon(icon="info-sign"),
                popup=popup
            ).add_to(m)
    
    if selected_geom:
        bounds = selected_geom.bounds
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
        popup.add_to(marker)
    
    colormap.caption = f'{selected_year}'
    colormap.add_to(m)
    
    
    # Display the Folium map in Streamlit
    st_data = st_folium(m, width=1600, height=600, key="map1")


#==============================================================================
# Tab 2
#==============================================================================

def render_tab2():
    """
    This function renders Tab 2 - historic events
    """
    # Embedded tabs
    tab1, tab2 = st.tabs(["Carte des inondations historiques (2000 - 2023)", "Carte des sécheresses historiques (2000 - 2023)"])

    with tab1:
        # Load the event data
        events_df = inon_events()
        events_df['dat_deb'] = pd.to_datetime(events_df['dat_deb'])
        events_df['dat_fin'] = pd.to_datetime(events_df['dat_fin'])

        # Calculate event duration
        events_df['duration'] = (events_df['dat_fin'] - events_df['dat_deb']).dt.days + 1

        # Calculate number of events and average duration per commune
        event_counts = events_df.groupby('cod_commune').size().reset_index(name='event_count')
        average_duration = events_df.groupby('cod_commune')['duration'].mean().reset_index(name='average_duration')

        event_counts['cod_commune'] = event_counts['cod_commune'].astype(str)
        average_duration['cod_commune'] = average_duration['cod_commune'].astype(str)

        # Merge event counts and average duration with inseedf
        df = inseedf.merge(event_counts, left_on='Code INSEE', right_on='cod_commune', how='left').merge(average_duration, on='cod_commune', how='left')

        # Replace NaN values with 0
        df['event_count'] = df['event_count'].fillna(0).astype(int)
        df['average_duration'] = df['average_duration'].fillna(0).round(2)

        # Create a GeoDataFrame
        gdf = gpd.GeoDataFrame(df, geometry='geometry')

        # Create a select box to toggle between event count and average duration
        display_option = st.selectbox("Sélectionnez::", options=["Nombre d'Inondations", "Durée moyenne annuelle des inondations"], key="event1")

        if display_option == "Nombre d'Inondations":
            colormap = cm.LinearColormap(colors=['#ffffcc', '#41b6c4', '#0c2c84'], vmin=gdf['event_count'].min(), vmax=gdf['event_count'].max())
            selected_column = 'event_count'
        else:
            colormap = cm.LinearColormap(colors=['#ffffcc', '#41b6c4', '#0c2c84'], vmin=gdf['average_duration'].min(), vmax=gdf['average_duration'].max())
            selected_column = 'average_duration'

        # Initialize a Folium map
        m = folium.Map(location=[50.629250, 3.057256], zoom_start=8)

        for _, row in gdf.iterrows():
            geom = row['geometry']
            if geom.is_empty or geom is None:
                continue
            color = colormap(row[selected_column])
            tooltip_text = f"<div style='font-size: 16px;'><b>Commune:</b> {row['Commune']}<br><b>{display_option}:</b> {row[selected_column]}</div>"
            folium.GeoJson(
                data=geom,
                tooltip=tooltip_text,
                style_function=lambda x, color=color: {
                    'fillColor': color, 'color': 'black', 'weight': 0.5, 'fillOpacity': 1
                }
            ).add_to(m)

        colormap.caption = display_option
        colormap.add_to(m)

        # Display the Folium map in Streamlit
        st_data = st_folium(m, width=1600, height=600, key="map4")

    with tab2:
        # Load the event data
        events_df = sech_events()
        events_df['dat_deb'] = pd.to_datetime(events_df['dat_deb'])
        events_df['dat_fin'] = pd.to_datetime(events_df['dat_fin'])

        # Calculate event duration
        events_df['duration'] = (events_df['dat_fin'] - events_df['dat_deb']).dt.days + 1

        # Calculate number of events and average duration per commune
        event_counts = events_df.groupby('cod_commune').size().reset_index(name='event_count')
        average_duration = events_df.groupby('cod_commune')['duration'].mean().reset_index(name='average_duration')

        event_counts = events_df.groupby('cod_commune').size().reset_index(name='event_count')
        average_duration = events_df.groupby('cod_commune')['duration'].mean().reset_index(name='average_duration')

        # Ensure 'Code INSEE' in inseedf and 'cod_commune' in event_counts/average_duration are the same data type
        inseedf['Code INSEE'] = inseedf['Code INSEE'].astype(str).str.strip()
        event_counts['cod_commune'] = event_counts['cod_commune'].astype(str).str.strip()
        average_duration['cod_commune'] = average_duration['cod_commune'].astype(str).str.strip()

        # Merge event counts and average duration with inseedf
        df = inseedf.merge(event_counts, left_on='Code INSEE', right_on='cod_commune', how='left').merge(average_duration, left_on='Code INSEE', right_on='cod_commune', how='left')

        # Replace NaN values with 0
        df['event_count'] = df['event_count'].fillna(0).astype(int)
        df['average_duration'] = df['average_duration'].fillna(0).round(2)

        # Create a GeoDataFrame
        gdf = gpd.GeoDataFrame(df, geometry='geometry')

        # Create a select box to toggle between event count and average duration
        display_option = st.selectbox("Sélectionnez:", options=["Nombre de sécheresses", "Durée moyenne annuelle de la sécheresse"], key="event2")

        if display_option == "Nombre de sécheresses":
            colormap = cm.LinearColormap(colors=['#FFFFB2','#FFD700', '#FFC300','#FFB000', '#FF8C00', '#FF7000', '#FF4500', '#FF2400', '#FF0000', '#CC0000','#8B0000'], vmin=gdf['event_count'].min(), vmax=gdf['event_count'].max())
            selected_column = 'event_count'
        else:
            colormap = cm.LinearColormap(colors=['#FFFFB2','#FFD700', '#FFC300','#FFB000', '#FF8C00', '#FF7000', '#FF4500', '#FF2400', '#FF0000', '#CC0000','#8B0000'], vmin=gdf['average_duration'].min(), vmax=gdf['average_duration'].max())
            selected_column = 'average_duration'

        # Initialize a Folium map
        m = folium.Map(location=[50.629250, 3.057256], zoom_start=8)

        for _, row in gdf.iterrows():
            geom = row['geometry']
            if geom.is_empty or geom is None:
                continue
            color = colormap(row[selected_column])
            tooltip_text = f"<div style='font-size: 16px;'><b>Commune:</b> {row['Commune']}<br><b>{display_option}:</b> {row[selected_column]}</div>"
            folium.GeoJson(
                data=geom,
                tooltip=tooltip_text,
                style_function=lambda x, color=color: {
                    'fillColor': color, 'color': 'black', 'weight': 0.5, 'fillOpacity': 1
                }
            ).add_to(m)

        colormap.caption = display_option
        colormap.add_to(m)

        # Display the Folium map in Streamlit
        st_data = st_folium(m, width=1600, height=600, key="map4")
    

    
    
#==============================================================================
# Tab 3
#==============================================================================

def render_tab3():
     
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Inondations - Top 10 des Communes","Sécheresses - Top 10 des Communes","Inondations par mois","Sécheresses par mois","Nombre d'Événements", "Carte des Sols"])
    
    with tab1:
        # Load the data
        events_df = inon_events()
        
        # Group by commune and date, and count the number of events
        commune_date_counts = events_df.groupby(['lib_commune', 'dat_deb']).size().reset_index(name='event_count')

        # Get the top 10 communes by total number of events
        top_10_communes = commune_date_counts.groupby('lib_commune')['event_count'].sum().nlargest(10).index
        top_10_data = commune_date_counts[commune_date_counts['lib_commune'].isin(top_10_communes)]

        # Pivot the data
        pivot_data = top_10_data.pivot(index='dat_deb', columns='lib_commune', values='event_count')

        # Calculate the cumulative sum for events
        cumulative_data = pivot_data.cumsum()

        # Interpolate to create a continuous line
        cumulative_data = cumulative_data.interpolate(method='linear')

        # Fill NA
        cumulative_data.fillna(0, inplace=True)

        # Plot running total events over time using Plotly
        fig = px.line(cumulative_data, labels={'value': "No.  d'Inondations", 'dat_deb': ''}, title='Inondations (Top 10 des Communes)')
        fig.update_layout(legend_title_text='Commune', plot_bgcolor='white')

        # Display the Plotly chart in Streamlit
        st.plotly_chart(fig, use_container_width=True)
        
    with tab2:
         # Load the data
         events_df = sech_events()
         
         # Group by commune and date, and count the number of events
         commune_date_counts = events_df.groupby(['lib_commune', 'dat_deb']).size().reset_index(name='event_count')

         # Get the top 10 communes by total number of events
         top_10_communes = commune_date_counts.groupby('lib_commune')['event_count'].sum().nlargest(10).index
         top_10_data = commune_date_counts[commune_date_counts['lib_commune'].isin(top_10_communes)]

         # Pivot the data
         pivot_data = top_10_data.pivot(index='dat_deb', columns='lib_commune', values='event_count')

         # Calculate the cumulative sum for events
         cumulative_data = pivot_data.cumsum()

         # Interpolate to create a continuous line
         cumulative_data = cumulative_data.interpolate(method='linear')

         # Fill NA
         cumulative_data.fillna(0, inplace=True)

         # Plot running total events over time using Plotly
         fig = px.line(cumulative_data, labels={'value': 'No. de Sécheresses', 'dat_deb': ''}, title='Sécheresses (Top 10 des Communes)')
         fig.update_layout(legend_title_text='Commune', plot_bgcolor='white')

         # Display the Plotly chart in Streamlit
         st.plotly_chart(fig, use_container_width=True)

    with tab3:
        # Load data
        inon_events_df = inon_events()
        
        # Extract month
        inon_events_df['month'] = inon_events_df['dat_deb'].dt.month
        
        # Aggregate total events per month
        monthly_totals = inon_events_df.groupby('month').size().reset_index(name='events')
        
        # Plotting 
        fig = px.bar(monthly_totals, x='month', y='events', labels={'month': '', 'events': 'Total des événements'}, title='Inondations totales par mois')
        
        # Set x values
        fig.update_layout(
            xaxis=dict(
                tickmode='array',
                tickvals=list(range(1, 13)),
                ticktext=['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
                tickangle=45
            ),
            yaxis_title='Total Events',
            plot_bgcolor='white',
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    with tab4:
        # Load data
        sech_events_df = sech_events()
        
        # Extract month
        sech_events_df['month'] = sech_events_df['dat_deb'].dt.month
        
        # Aggregate total events per month
        monthly_totals = sech_events_df.groupby('month').size().reset_index(name='events')
        
        # Plotting 
        fig = px.bar(monthly_totals, x='month', y='events', labels={'month': '', 'events': 'Total des événements'}, title='Sécheresses totales par mois')
        
        # Set x values
        fig.update_layout(
            xaxis=dict(
                tickmode='array',
                tickvals=list(range(1, 13)),
                ticktext=['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
                tickangle=45
            ),
            yaxis_title='Total Events',
            plot_bgcolor='white',
        )
        
        st.plotly_chart(fig, use_container_width=True)


         
    with tab5:
        catnat = cat_events()

        # Filter after 2000
        catnat = catnat[catnat['dat_deb'].dt.year > 2000]

        # Group by date and disaster name
        cat_counts = catnat.groupby(['dat_deb', 'lib_risque_jo']).size().unstack(fill_value=0)

       
        # Select relevant columns
        selected_columns = ['Sécheresse', 'Inondations et/ou coulées de boue', 'Inondations remontée nappe']
        cat_counts = cat_counts[selected_columns]

        # Plot the disasters over time using Plotly
        fig = go.Figure()
        for col in selected_columns:
            fig.add_trace(go.Scatter(x=cat_counts.index, y=cat_counts[col], mode='lines', name=col))

        fig.update_layout(
            title="Nombre d'Événements (After 2000)",
            xaxis_title='Date',
            yaxis_title="Nombre d'Événements",
            legend_title="Type d'Événement",
            plot_bgcolor='white',
            xaxis=dict(
                tickformat='%Y',
                dtick='M48',  
                tickangle=-45
            ),
            yaxis=dict(
                dtick=50  
            )
        )

        # Display the Plotly chart in Streamlit
        st.plotly_chart(fig, use_container_width=True)
        
    with tab6:
        
        html_file_path = 'sol_map.html'
        # Read the content of the HTML file
        with open(html_file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        st.components.v1.html(html_content, width=1200, height=600, scrolling=True)

# Main body
render_header()

# Render the tabs
tab1, tab2, tab3 = st.tabs(["Carte des risques","Cartes d'événements historiques",  "Exploration des données"])
with tab1:
    render_tab1()
with tab2:
    render_tab2()
with tab3:
    render_tab3()







# Customize the dashboard with CSS 
st.markdown(
    """
    <style>
        .stApp {
            background: #006f4e; 
        }
        .header {
            padding: 5px;
            display: flex;
            align-items: center; /* Center vertically */
            justify-content: center; /* Center horizontally */
            background-color: #333333;
            width: 100%;
        }
        .title {
            color: white; /* Adjust the title color */
            margin: 0; /* Reset margin to remove any default margin */
            font-size: 38px;
        }
        section.main > div {
            max-width:95rem
            }
        
        
    </style>
    """,
    unsafe_allow_html=True,
)


###############################################################################
# END
###############################################################################
