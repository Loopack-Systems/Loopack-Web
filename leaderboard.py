import streamlit as st
from app.queries import Queries
from app.utils import vertical_space

queries = Queries()

@st.cache_data
def get_ranking_data():
    return queries.get_users_ranking()

@st.cache_data
def get_card_data(card_number):
    df_daily, df_weekly, df_monthly = queries.get_temporal_usage(card_number)
    timeframe_dataframe = {"Daily": df_daily, "Weekly": df_weekly, "Monthly": df_monthly}
    return timeframe_dataframe

@st.cache_data
def get_all_data():
    df_daily, df_weekly, df_monthly = queries.get_all_temporal_usage()
    timeframe_dataframe = {"Daily": df_daily, "Weekly": df_weekly, "Monthly": df_monthly}
    return timeframe_dataframe

st.set_page_config(
    page_title="loopack",
    page_icon=":green_circle:", 
    initial_sidebar_state="collapsed"
)

all_ranking = get_ranking_data()

col1, _, col3 = st.columns(3)
col1.title("Loopack")

issue = col3.button("Something Wrong? Tell Us!")
if issue:
    st.write("SEND TO A GOOGLE FORM")

vertical_space(1)

filter_dashboard_btn = None

tab1, tab2, tab3 = st.tabs(["Leaderboard", "My Dashboard", "FEUP Dashboard"])

with tab1:

    if "go_submitted" not in st.session_state:
        st.session_state["go_submitted"] = False

    vertical_space(1)
    st.text("Card Number")

    col21, col22, col23 = st.columns(3)
    card_number_filter = col21.text_input("Card Number", label_visibility="collapsed", key="leaderboard")
    filter_btn = col22.button("Filter")
    update_btn = col23.button("Update")
    if update_btn:
        st.cache_resource.clear()
        st.cache_data.clear()
        st.rerun()


    vertical_space(1)

    ranking = all_ranking.loc[all_ranking['card_number'].str.contains(card_number_filter, case=False)]

    vertical_space(1)

    ranking.columns = ['ID', 'Drinks', 'Returns', "Impact"]
    st.table(ranking)

    go_btn = None
    if len(ranking) == 1 and st.session_state["go_submitted"] == False:
        go_btn = st.button("Go to dashboard")

    if go_btn or st.session_state["go_submitted"]:
        
        st.session_state["go_submitted"] = True
        card_num = ranking["card_number"].iloc[0]
        timeframe_dataframe = get_card_data(card_num)

        vertical_space(2)
        st.markdown(f"### Card {card_num}")
        vertical_space(2)

        col221, col222 = st.columns(2, gap="large")
        col221.markdown("##### Drinks consumption")
        timeframe = col222.radio(label=" ", options=["Daily", "Weekly", "Monthly"], label_visibility="collapsed", horizontal=True, index=1, key="1")
        st.bar_chart(timeframe_dataframe[timeframe], x="event_time", y="num_drinks")


with tab2:

    if "card_submitted" not in st.session_state:
        st.session_state["card_submitted"] = False

    vertical_space(1)
    st.text("Card Number")

    col31, col32 = st.columns(2)
    card_number = col31.text_input("Card Number", label_visibility="collapsed", key="my_card")
    my_card_go_btn = col32.button("Go")

    if my_card_go_btn or st.session_state["card_submitted"]:

        st.session_state["card_submitted"] = True

        card_info = all_ranking.loc[all_ranking['card_number'].str.contains(card_number, case=False)]
        timeframe_dataframe = get_card_data(card_number)

        # the other information and gauge plots

        if len(timeframe_dataframe["Daily"]) == 0 or len(timeframe_dataframe["Weekly"]) == 0 or len(timeframe_dataframe["Monthly"]) == 0:
            st.error("Card not found")
        else:        
            vertical_space(2)
            st.markdown(f"### Card {card_number}")
            vertical_space(2)

            st.table(card_info)

            vertical_space(2)

            col41, col42 = st.columns(2, gap="large")
            timeframe = col42.radio(label=" ", options=["Daily", "Weekly", "Monthly"], label_visibility="collapsed", horizontal=True, index=1, key="2")
            col41.markdown("##### Drinks consumption")
            st.bar_chart(timeframe_dataframe[timeframe], x="event_time", y="num_drinks")

with tab3:
    timeframe_dataframe = get_all_data()

    # the other information and gauge plots

    if len(timeframe_dataframe["Daily"]) == 0 or len(timeframe_dataframe["Weekly"]) == 0 or len(timeframe_dataframe["Monthly"]) == 0:
        st.error("No data")
    else:        
        vertical_space(2)
        st.markdown(f"### All cards")
        vertical_space(2)

        # gauge plots

        vertical_space(2)

        col41, col42 = st.columns(2, gap="large")
        timeframe = col42.radio(label=" ", options=["Daily", "Weekly", "Monthly"], label_visibility="collapsed", horizontal=True, index=1, key="3")
        col41.markdown("##### Drinks consumption")
        st.bar_chart(timeframe_dataframe[timeframe], x="event_time", y="num_drinks")
