from datetime import datetime
import streamlit as st
import webbrowser
from src.queries import Queries
from src.utils import vertical_space
import emoji
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

queries = Queries()

def open_url_in_new_page(url):
    webbrowser.open_new_tab(url)

@st.cache_data
def get_ranking_data():
    return queries.get_users_ranking()

@st.cache_data
def get_card_data(card_number):
    df_daily, df_weekly, df_monthly = queries.get_temporal_usage(card_number)
    usage_dataframe = {"Daily": df_daily, "Weekly": df_weekly, "Monthly": df_monthly}
    df_daily, df_weekly, df_monthly = queries.get_temporal_returns(card_number)
    returns_dataframe = {"Daily": df_daily, "Weekly": df_weekly, "Monthly": df_monthly}
    return usage_dataframe, returns_dataframe

@st.cache_data
def get_all_data():
    df_daily, df_weekly, df_monthly = queries.get_all_temporal_usage()
    total_usage_dataframe = {"Daily": df_daily, "Weekly": df_weekly, "Monthly": df_monthly}
    df_daily, df_weekly, df_monthly = queries.get_all_temporal_returns()
    total_returns_dataframe = {"Daily": df_daily, "Weekly": df_weekly, "Monthly": df_monthly}
    return total_usage_dataframe, total_returns_dataframe

def prepare_ranking_to_show(all_ranking, drop_email=True):

    cols = ['ID', 'User Name', 'Drinks', 'Returns', "Impact", "Drinking"]

    if drop_email:
        aux = all_ranking.drop(columns=["user_email"]).copy()
        cols = ['ID', 'User Name', 'Drinks', 'Returns', "Impact", "Drinking"]
    else:
        aux = all_ranking.copy()
        cols = ['ID', 'User Name', 'User Email', 'Drinks', 'Returns', "Impact", "Drinking"]
   
    aux.columns = cols
    aux = aux.sort_values(by='Impact', ascending = False).reset_index(drop=True).reset_index().rename(columns={"index": "Ranking"})
    
    aux["Ranking"] = aux["Ranking"].apply(lambda x: x+1)
    aux["User Name"] = aux["User Name"].replace("-999", "--------")
    aux["Drinks"] = aux["Drinks"].astype(int)
    aux["Returns"] = aux["Returns"].astype(int)
    aux["Impact"] = aux["Impact"].astype(float).apply(lambda x: str(round(x,1)))

    aux["Drinking"] = aux["Drinking"].replace(False, emoji.emojize(":red_circle:"))
    aux["Drinking"] = aux["Drinking"].replace(False, emoji.emojize(":green_circle:"))

    aux["Ranking"] = aux["Ranking"].replace(1, emoji.emojize(":1st_place_medal:"))
    aux["Ranking"] = aux["Ranking"].replace(2, emoji.emojize(":2nd_place_medal:"))
    aux["Ranking"] = aux["Ranking"].replace(3, emoji.emojize(":3rd_place_medal:"))

    return aux

st.set_page_config(
    page_title="Loopack",
    page_icon="src/resources/icon.png", 
    initial_sidebar_state="collapsed"
)

all_ranking = get_ranking_data()

col1, _ = st.columns(2)
col1.image("src/resources/logo.png", use_column_width=True)

vertical_space(2)

if st.button("Something Wrong? Tell Us!"):
    url_to_open = "https://loopack.pt"
    open_url_in_new_page(url_to_open)

vertical_space(1)

filter_dashboard_btn = None
tab1, tab2, tab3, tab4 = st.tabs([":first_place_medal: Leaderboard", "My Dashboard", "FEUP", ":bust_in_silhouette: Register My Card"])

with tab1:

    if "go_submitted" not in st.session_state:
        st.session_state["go_submitted"] = False

    vertical_space(1)
    st.text("Account ID / User Name")

    col21, col22 = st.columns(2)
    card_number_filter = col21.text_input("Account ID / User Name", label_visibility="collapsed", key="leaderboard")

    vertical_space(1)
    filter_btn = col22.button("Filter")

    col211, _, col213, _ = st.columns(4)

    col211.markdown("## Ranking")

    update_btn = col213.button("Update", type="secondary")
    if update_btn:
        st.cache_resource.clear()
        st.cache_data.clear()
        st.rerun()

    aux = prepare_ranking_to_show(all_ranking)

    try:
        aux = aux.loc[(aux['ID'].str.contains(card_number_filter, case=False))|(aux['User Name'].str.contains(card_number_filter, case=False))][:15]
    except:
        aux = pd.DataFrame()

    # s1 = dict(selector='th', props=[('text-align', 'center')])
    # s2 = dict(selector='td', props=[('text-align', 'center')])
    # table = aux.style.set_table_styles([s1,s2]).hide(axis=0).to_html()   
        
    vertical_space(2)

    if len(aux) > 0:
        aux = aux[["Ranking", "ID", "User Name", "Drinking", "Impact", "Drinks", "Returns"]]
        st.dataframe(aux.rename(columns={"Ranking": "Rank"}), hide_index=True)
        #st.write(f'{table}', unsafe_allow_html=True, )
    else:
        st.error("No data to show!")

with tab2:

    if "card_submitted" not in st.session_state:
        st.session_state["card_submitted"] = False

    vertical_space(1)
    st.text("Account ID / User Email")

    col31, col32 = st.columns(2)
    card_input = col31.text_input("Account ID", label_visibility="collapsed", key="my_card")
    my_card_go_btn = col32.button("Go")

    if my_card_go_btn or st.session_state["card_submitted"]:

        st.session_state["card_submitted"] = True

        aux = prepare_ranking_to_show(all_ranking, drop_email=False)

        try:
            aux = aux.loc[(aux['ID']==card_input)|(aux['User Email']==card_input)]
        except:
            aux = pd.DataFrame()

        card_info = aux.copy()

        if "@" in card_input:
            card_input = card_info["ID"].item()

        usage_dataframe, returns_dataframe = get_card_data(card_input)

        # the other information and gauge plots

        if len(card_info) == 0 or len(usage_dataframe["Daily"]) == 0 or len(usage_dataframe["Weekly"]) == 0 or len(usage_dataframe["Monthly"]) == 0:
            st.error("Card not found or never used!")
        else:        
            user_name = card_info["User Name"].item()
            vertical_space(5)
            st.markdown(f"### {user_name}")

            col311, col312, col313 = st.columns(3)

            # Gauge plot for 'Drinks'
            with col311:
                fig_drinks = go.Figure(go.Indicator(
                                mode = "number+delta",
                                value = int(round(float(card_info["Returns"].item()))),
                                title = {"text": "Drinks<br><span style='font-size:0.8em;color:gray'>Number of cups</span><br>"},
                                domain = {'row': 0, 'column': 1}))
                st.plotly_chart(fig_drinks, use_container_width=True)

            # Gauge plot for 'Returns'
            with col312:
                fig_returns = go.Figure(go.Indicator(
                                mode = "number+delta",
                                value = int(round(float(card_info["Returns"].item()))),
                                title = {"text": "Returns<br><span style='font-size:0.8em;color:gray'>Number of cups</span><br>"},
                                domain = {'row': 0, 'column': 1}))
                st.plotly_chart(fig_returns, use_container_width=True)

            # Gauge plot for 'Impact'
            with col313:
                fig_impact = go.Figure(go.Indicator(
                                mode = "number+delta",
                                value = int(round(float(card_info["Impact"].item()))),
                                title = {"text": "Impact<br><span style='font-size:0.8em;color:gray'>kg of CO2</span><br>"},
                                domain = {'row': 0, 'column': 1}))

                st.plotly_chart(fig_impact, use_container_width=True)

            col41, col42 = st.columns(2, gap="large")
            timeframe = col42.radio(label=" ", options=["Daily", "Weekly", "Monthly"], label_visibility="collapsed", horizontal=True, index=0, key="2")
            col41.markdown("##### Drinks consumption")

            if timeframe == "Weekly":
                frequency ='W-Sat'
            elif timeframe == "Monthly":
                frequency = 'MS'
            else:
                frequency = 'D'

            df = usage_dataframe[timeframe]
            df = df.rename(columns={"event_time": "Event Time"})
            all_dates_df = pd.DataFrame({"Event Time": pd.date_range(start=df["Event Time"].min(), end=datetime.today(), freq=frequency)})
            df = df.merge(all_dates_df, on="Event Time", how='right').fillna(0)
            fig = px.line(df, x="Event Time", y="num_drinks", line_shape="linear", labels={"num_drinks": "Number of Drinks"})
            fig.update_traces(fill='tozeroy', line=dict(color='#76d783'), fillcolor='rgba(118, 215, 131, 0.3)')
            fig.update_layout(yaxis=dict(range=[0, max(df['num_drinks']) + 1]))
            fig.update_layout(clickmode='none')
            fig.update_yaxes(fixedrange=True)
            fig.update_xaxes(fixedrange=True)
            fig.update_layout(clickmode='none', autosize=True, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

            st.divider()

            vertical_space(1)

            col51, col52 = st.columns(2, gap="large")
            timeframe2 = col52.radio(label=" ", options=["Daily", "Weekly", "Monthly"], label_visibility="collapsed", horizontal=True, index=0, key="4")
            col51.markdown("##### Cups returns")

            if timeframe2 == "Weekly":
                frequency ='W-Sat'
            elif timeframe2 == "Monthly":
                frequency = 'MS'
            else:
                frequency = 'D'

            df = returns_dataframe[timeframe2]
            df = df.rename(columns={"event_time": "Event Time"})
            all_dates_df = pd.DataFrame({"Event Time": pd.date_range(start=df["Event Time"].min(), end=datetime.today(), freq=frequency)})
            df = df.merge(all_dates_df, on="Event Time", how='right').fillna(0)
            fig = px.line(df, x="Event Time", y="num_drinks", line_shape="linear", labels={"num_drinks": "Number of Returns"})
            fig.update_traces(fill='tozeroy', line=dict(color='#76d783'), fillcolor='rgba(118, 215, 131, 0.3)')
            fig.update_layout(yaxis=dict(range=[0, max(df['num_drinks']) + 1]))
            fig.update_yaxes(fixedrange=True)
            fig.update_xaxes(fixedrange=True)
            fig.update_layout(clickmode='none', autosize=True, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

with tab3:

    aux = prepare_ranking_to_show(all_ranking)
    total_usage_dataframe, total_returns_dataframe = get_all_data()
    
    if len(total_usage_dataframe["Daily"]) == 0 or len(total_usage_dataframe["Weekly"]) == 0 or len(total_usage_dataframe["Monthly"]) == 0:
        st.error("No data")
    else:        
        vertical_space(2)
        st.markdown(f"### Overall Metrics")
        vertical_space(2)

        col311, col312, col313 = st.columns(3)

        # Gauge plot for 'Drinks'
        with col311:
            fig_drinks = go.Figure(go.Indicator(
                            mode = "number+delta",
                            value = int(aux["Returns"].sum()),
                            title = {"text": "Drinks<br><span style='font-size:0.8em;color:gray'>Number of cups</span><br>"},
                            domain = {'row': 0, 'column': 1}))
            st.plotly_chart(fig_drinks, use_container_width=True)

        # Gauge plot for 'Returns'
        with col312:
            fig_returns = go.Figure(go.Indicator(
                            mode = "number+delta",
                            value = int(aux["Returns"].sum()),
                            title = {"text": "Returns<br><span style='font-size:0.8em;color:gray'>Number of cups</span><br>"},
                            domain = {'row': 0, 'column': 1}))
            st.plotly_chart(fig_returns, use_container_width=True)

        # Gauge plot for 'Impact'
        with col313:
            fig_impact = go.Figure(go.Indicator(
                            mode = "number+delta",
                            value = int(round(float(aux["Impact"].astype(float).sum()))),
                            title = {"text": "Impact<br><span style='font-size:0.8em;color:gray'>kg of CO2</span><br>"},
                            domain = {'row': 0, 'column': 1}))

            st.plotly_chart(fig_impact, use_container_width=True)

        col41, col42 = st.columns(2, gap="large")
        timeframe = col42.radio(label=" ", options=["Daily", "Weekly", "Monthly"], label_visibility="collapsed", horizontal=True, index=0, key="5")
        col41.markdown("##### Drinks consumption")

        if timeframe == "Weekly":
            frequency ='W-Sat'
        elif timeframe == "Monthly":
            frequency = 'MS'
        else:
            frequency = 'D'

        df = total_usage_dataframe[timeframe]
        df = df.rename(columns={"event_time": "Event Time"})
        all_dates_df = pd.DataFrame({"Event Time": pd.date_range(start=df["Event Time"].min(), end=datetime.today(), freq=frequency)})
        df = df.merge(all_dates_df, on="Event Time", how='right').fillna(0)
        fig = px.line(df, x="Event Time", y="num_drinks", line_shape="linear", labels={"num_drinks": "Number of Drinks"})
        fig.update_traces(fill='tozeroy', line=dict(color='#76d783'), fillcolor='rgba(118, 215, 131, 0.3)')
        fig.update_layout(yaxis=dict(range=[0, max(df['num_drinks']) + 1]))
        fig.update_yaxes(fixedrange=True)
        fig.update_xaxes(fixedrange=True)
        fig.update_layout(clickmode='none', autosize=True, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        vertical_space(1)

        col51, col52 = st.columns(2, gap="large")
        timeframe2 = col52.radio(label=" ", options=["Daily", "Weekly", "Monthly"], label_visibility="collapsed", horizontal=True, index=0, key="6")
        col51.markdown("##### Cups returns")

        if timeframe2 == "Weekly":
            frequency ='W-Sat'
        elif timeframe2 == "Monthly":
            frequency = 'MS'
        else:
            frequency = 'D'

        df = total_returns_dataframe[timeframe2]
        df = df.rename(columns={"event_time": "Event Time"})
        all_dates_df = pd.DataFrame({"Event Time": pd.date_range(start=df["Event Time"].min(), end=datetime.today(), freq=frequency)})
        df = df.merge(all_dates_df, on="Event Time", how='right').fillna(0)
        fig = px.line(df, x="Event Time", y="num_drinks", line_shape="linear", labels={"num_drinks": "Number of Returns"})
        fig.update_traces(fill='tozeroy', line=dict(color='#76d783'), fillcolor='rgba(118, 215, 131, 0.3)')
        fig.update_layout(yaxis=dict(range=[0, max(df['num_drinks']) + 1]))
        fig.update_yaxes(fixedrange=True)
        fig.update_xaxes(fixedrange=True)
        fig.update_layout(clickmode='none', autosize=True, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)