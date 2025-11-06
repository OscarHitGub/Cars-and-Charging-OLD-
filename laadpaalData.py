import streamlit as st
import pandas as pd
import plotly.express as px

import GeodataEnCars as gc

def laadpaal():
    ## DATA INLADEN ##
    laaddata = pd.read_csv("laadpaaldata.csv")
    
    st.set_page_config(layout="wide")
    st.title("⚡Laadpaal Statistieken")
    
    ## DATUMS OMZETTEN NAAR DATETIME ##
    laaddata["Started"] = pd.to_datetime(laaddata["Started"], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    laaddata["Ended"] = pd.to_datetime(laaddata["Ended"], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    laaddata = laaddata.dropna(subset=["Started"])
    laaddata = laaddata.dropna(subset=["Ended"])
    
    # Gooi alles onder 0 chargetime weg want dat klopt niet #
    laaddata = laaddata[laaddata["ChargeTime"] >= 0]
    
    # Voeg een nieuwe kolom toe die zegt of binnen een sessie een auto volledig werdt opgeladen #
    laaddata["FullyCharged?"] = laaddata["ChargeTime"] != laaddata["ConnectedTime"]
    
    ## HEATMAP VAN CORRELATIE ##
    def corr_heat(key):
        st.subheader("Correlatie tussen de kolommen", divider='rainbow')
        laadpaal_corr = laaddata.corr()
        LPHeatmap = px.imshow(laadpaal_corr,
                              labels=dict(color="Correlatie"))
        LPHeatmap.update_xaxes(side="top")
        st.plotly_chart(LPHeatmap, use_container_width=False, key=key)
    
    # Maak wat tabbladen #
    tab1, tab2, tab3 = st.tabs(["🚩 Geodata Laadpalen","🕓 Tijd aan de laadpaal", "⚡Energie Verbruik"])
    
    with tab1:
        gc.lp_map()
    
    with tab2:
        st.subheader("Scatterplot", divider="green")
        
        ## SCATTERPLOT ConnectedTime x ChargeTime ##
        LDscatter = px.scatter(laaddata,
                     y="ConnectedTime",
                     x="ChargeTime",
                     color="FullyCharged?",
                     color_discrete_sequence=['rgb(186, 31, 28)', 'rgb(50, 168, 82)'],
                     opacity=0.75,
                     labels={"ConnectedTime": "Tijd verbonden",
                             "ChargeTime": "Tijd aan het opladen",
                             "FullyCharged?": "Volledig opgeladen?"})
        
        st.plotly_chart(LDscatter)
        
        st.subheader("Histogram", divider="blue")
        
        ## HISTOGRAM ConnectedTime EN ChargeTime ##
        
        # Logaritmische knop #
        st.checkbox("Logaritmische schaal", key='log_scale_hist', value=True)
        
        ld_long = laaddata.melt(value_vars=["ConnectedTime","ChargeTime"],
                                 var_name="Type",
                                 value_name="Time")
        
        LDhist = px.histogram(ld_long,
                              x="Time",
                              color="Type",
                              barmode="overlay",
                              opacity=0.8,
                              labels={"Time": "Tijd in uur"})
        
        # Hierdoor werkt die logaritmische knop #
        LDhist.update_yaxes(type="log" if st.session_state.log_scale_hist else "linear")
        
        st.plotly_chart(LDhist)
        
        ## HOEVEELHEID AUTOS AAN DE LAADPAAL PER DAG ##
        st.subheader("Hoeveel auto's hangen aan de laadpaal?", divider="violet")
        
        # Dagselectie #
        datum_filter = laaddata['Started'].dt.date
        select_date = st.date_input("Kies een datum:",
                                      value= datum_filter.min(),
                                      min_value=datum_filter.min(),
                                      max_value=datum_filter.max())
        
        # Alleen de data van de geselecteerde dag #
        laaddata_dag = laaddata[
            (laaddata['Started'].dt.normalize() == pd.to_datetime(select_date)) |
            (laaddata['Ended'].dt.normalize() == pd.to_datetime(select_date))
        ].copy()
        
        # Afronden op de minuut anders duurt het heel lang #
        laaddata_dag['Started'] = laaddata_dag['Started'].dt.round("min")
        laaddata_dag['Ended'] = laaddata_dag['Ended'].dt.round("min")
        
        laaddata_dag['Minuut'] = laaddata_dag.apply(
            lambda rij: list(pd.date_range(start=rij['Started'], end=rij['Ended'], freq="1min")),
            axis=1
        )
    
        laadpaal_min = (
            laaddata_dag.explode('Minuut')
            .groupby('Minuut')
            .apply(lambda df: df.index.nunique())
            .reset_index(name='Aantal_autos')
        )
        
        # Plot echt alleen de dag die geselecteerd is #
        dag_om_te_plotten = pd.Timestamp(select_date)
        laadpaal_dag = laadpaal_min[(laadpaal_min['Minuut'] >= dag_om_te_plotten) & 
                    (laadpaal_min['Minuut'] < dag_om_te_plotten + pd.Timedelta(days=1))]
    
        aan_laadpaal = px.line(laadpaal_dag,
                               x='Minuut',
                               y='Aantal_autos',
                               color_discrete_sequence=['rgb(102, 40, 166)'],
                               title=f'Aantal aangesloten auto’s op {select_date}',
                               labels={"Minuut": "Tijd",
                                       "Aantal_autos": "Aantal Aangesloten Autos"})
        
        aan_laadpaal.update_layout(yaxis_range=[0,20])
        st.plotly_chart(aan_laadpaal)
        
        corr_heat('LPHeatmap1')
        
    with tab3:
        st.subheader("Scatterplot", divider="red")
        
        laaddata["AC or DC?"] = "DC"
        laaddata.loc[((laaddata["TotalEnergy"]/1000) / laaddata["ChargeTime"]) < 4, "AC or DC?"] = "AC"
        
        # Checkbox die automatisch session_state bijwerkt
        st.checkbox("Trendlijn", key='trendline_LD', value=True)
        
        ## SCATTERPLOT TotalEnergy x ChargeTime ##
        LDscatter = px.scatter(laaddata,
                     x="ChargeTime",
                     y="TotalEnergy",
                     color="AC or DC?",
                     color_discrete_sequence=['rgb(188, 189, 34)', 'rgb(50, 168, 82)'],
                     trendline="ols" if st.session_state.trendline_LD else None,
                     opacity=0.75,
                     labels={"ChargeTime": "Tijd aan het opladen",
                             "TotalEnergy": "Totaal verbruikte<br>energie in Wh",
                             "FullyCharged?": "Volledig opgeladen?",
                             "AC or DC?": "Predicted AC or DC"})
        
        laaddata = laaddata.drop(columns=["AC or DC?"])
        LDscatter.update_yaxes(range=[0,87500])
        st.plotly_chart(LDscatter)
        
        ## BOXPLOTS ##
        st.subheader("Boxplots", divider="orange")
        
        # Verdeel de pagina in drieeën
        col1, col2, col3 = st.columns(3)
        
        with col2:
            # Plot de ChargeTime
            st.subheader("Tijd aan het opladen", divider=False)
            
            # Checkbox die automatisch session_state bijwerkt
            st.checkbox("Logaritmische schaal", key='log_scale_CT', value=True)
            
            fig_CT = px.box(laaddata,
                             y="ChargeTime",
                             color_discrete_sequence=['#1f77b4'],
                             labels={"ChargeTime": "Tijd aan het opladen"}
                             )
            fig_CT.update_yaxes(type="log" if st.session_state.log_scale_CT else "linear")
            fig_CT.update_layout(yaxis=dict(range=[0,None]))
            st.plotly_chart(fig_CT, use_container_width=True)
        
        with col1:
            # Plot de TotalEnergy
            st.subheader("Totaal verbruikte energie in Wh", divider=False)
            
            # Checkbox die automatisch session_state bijwerkt
            st.checkbox("Logaritmische schaal", key='log_scale_TE', value=True)
            
            fig_TE = px.box(laaddata,
                             y="TotalEnergy", 
                             color_discrete_sequence=['#d62728'],
                             labels={"TotalEnergy": "Totaal verbruikte<br>energie in Wh"}  
                             )
            fig_TE.update_yaxes(type="log" if st.session_state.log_scale_TE else "linear")
            fig_TE.update_layout(yaxis=dict(range=[0,None]))
            st.plotly_chart(fig_TE, use_container_width=True)

        with col3:
            # Plot de MaxPower
            st.subheader("Maximaal vermogen in W", divider=False)
            
            # Checkbox die automatisch session_state bijwerkt
            st.checkbox("Logaritmische schaal", key='log_scale_MP', value=True)
            
            fig_MP = px.box(laaddata,
                             y="MaxPower",
                             color_discrete_sequence=['#bcbd22'],
                             labels={"MaxPower": "Maximaal gevraagde<br>vermogen in W"}
                             )
            fig_MP.update_yaxes(type="log" if st.session_state.log_scale_MP else "linear")
            fig_MP.update_layout(yaxis=dict(range=[0,None]))
            st.plotly_chart(fig_MP, use_container_width=True)
        

        corr_heat('LPHeatmap2')
