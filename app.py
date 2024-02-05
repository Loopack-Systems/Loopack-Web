from datetime import datetime
import streamlit as st
from src.queries import Queries
from src.utils import vertical_space
import emoji
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import time

queries = Queries()

#@st.cache_data
def get_ranking_data():
    return queries.get_users_ranking()

#@st.cache_data
def get_card_data(card_number):
    df_daily, df_weekly, df_monthly = queries.get_temporal_usage(card_number)
    usage_dataframe = {"Daily": df_daily, "Weekly": df_weekly, "Monthly": df_monthly}
    df_daily, df_weekly, df_monthly = queries.get_temporal_returns(card_number)
    returns_dataframe = {"Daily": df_daily, "Weekly": df_weekly, "Monthly": df_monthly}
    phone, email, payment = queries.get_card_details(card_number)
    return usage_dataframe, returns_dataframe, phone, email, payment

#@st.cache_data
def get_all_data():
    df_daily, df_weekly, df_monthly = queries.get_all_temporal_usage()
    total_usage_dataframe = {"Daily": df_daily, "Weekly": df_weekly, "Monthly": df_monthly}
    df_daily, df_weekly, df_monthly = queries.get_all_temporal_returns()
    total_returns_dataframe = {"Daily": df_daily, "Weekly": df_weekly, "Monthly": df_monthly}
    return total_usage_dataframe, total_returns_dataframe

def prepare_ranking_to_show(all_ranking, drop_email=False):

    cols = ['Tag', 'ID', 'User Name', 'Drinks', 'Returns', "Impact", "Drinking", "Last Event"]

    if drop_email:
        aux = all_ranking.drop(columns=["user_email"]).copy()
        cols = ['Tag', 'ID', 'User Name', 'Drinks', 'Returns', "Impact", "Drinking", "Last Event"]
    else:
        aux = all_ranking.copy()
        cols = ['Tag', 'ID', 'User Name', 'User Email', 'Drinks', 'Returns', "Impact", "Drinking", "Last Event"]
   
    aux.columns = cols
    aux = aux.sort_values(by=['Impact', 'User Name'], ascending = False).reset_index(drop=True).reset_index().rename(columns={"index": "Ranking"})

    aux["Ranking"] = aux["Ranking"].apply(lambda x: x+1)
    aux["User Name"] = aux["User Name"].replace("-999", None)
    aux["Drinks"] = aux["Drinks"].astype(int)
    aux["Returns"] = aux["Returns"].astype(int)
    aux["Impact"] = aux["Impact"].astype(float).apply(lambda x: str(round(x,1)))

    #TO-DO remove this force
    aux["Drinking"] = aux.apply(lambda x: True if x.Drinks > x.Returns else False, axis = 1 )
    aux["Drinking"] = aux["Drinking"].replace(False, emoji.emojize(":red_circle:"))
    aux["Drinking"] = aux["Drinking"].replace(True, emoji.emojize(":green_circle:"))

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

st.write("Something Wrong? [Tell Us!](https://forms.gle/dmiCrKYZvB9CWwNf8)")

vertical_space(1)

filter_dashboard_btn = None
tab1, tab2, tab3, tab4 = st.tabs([":first_place_medal: Leaderboard", "My Dashboard", "FEUP", ":bust_in_silhouette: Register My Card"])

with tab1:

    if "go_submitted" not in st.session_state:
        st.session_state["go_submitted"] = False



    st.markdown("## Ranking")
    st.write("Our leaderboard will run during our whole Pilot from **Feb 05 to Feb 29**. Register to get a free coffee for every 10 uses!")
    st.markdown("We appreciate everyone who used Loopack during our testing week 🙏  but all status have been reset from Feb 05 for the official launch (except for our friend Cristiano, of course)! [Talk to us](https://forms.gle/dmiCrKYZvB9CWwNf8) if you have any questions.")
    
    st.text("Your Name, Email or Card RFID")

    col21, col22, col23 = st.columns(3)
    card_number_filter = col21.text_input("User Name", label_visibility="collapsed", key="leaderboard")

    filter_btn = col22.button("Filter")

    update_btn = col23.button("Refresh Leaderboard", type="secondary")
    if update_btn:
        st.cache_resource.clear()
        st.cache_data.clear()
        st.rerun()

    aux = prepare_ranking_to_show(all_ranking)

    try:
        if len(card_number_filter) > 0:
            aux = aux.loc[
                (aux['Tag'].str.contains(card_number_filter, case=False)) \
                | (aux['Tag'].apply(lambda x: ":".join([hex(int(num))[2:].upper() for num in x.split("-")])).str.contains(card_number_filter, case=False))\
                | (aux['User Name'].str.contains(card_number_filter, case=False)) \
                | (aux['User Email'].str.contains(card_number_filter, case=False))][:15]
    except Exception as e:
        st.error(e)
        aux = pd.DataFrame()

    # s1 = dict(selector='th', props=[('text-align', 'center')])
    # s2 = dict(selector='td', props=[('text-align', 'center')])
    # table = aux.style.set_table_styles([s1,s2]).hide(axis=0).to_html()   
        
    vertical_space(2)

    if len(aux) > 0:
        aux = aux[["Ranking", "ID", "User Name", "Drinking", "Impact", "Drinks", "Returns", 
                   #"User Email", 
                   "Last Event", 
                   "Tag"]].rename(columns={"Tag": "Card RFID", "User Email": "Email"})
        aux["User Name"] = aux["User Name"].fillna("NOT REGISTERED")
        aux['Decimal ID'] = aux["Card RFID"]
        aux["Card RFID"] = aux["Card RFID"].apply(lambda x: ":".join([hex(int(num))[2:].upper() for num in x.split("-")]))
        # TO-DO ver o que se passa
        aux = aux.drop_duplicates(['Decimal ID'])
        st.dataframe(aux.rename(columns={"Ranking": "Rank", "Impact": "Impact (g of CO2)"}).drop(columns="ID"), hide_index=True)
        #st.write(f'{table}', unsafe_allow_html=True, )
    else:
        st.error("No data to show!")

with tab2:

    if "card_submitted" not in st.session_state:
        st.session_state["card_submitted"] = False

    vertical_space(1)
    st.text("Your Email")

    col31, col32 = st.columns(2)
    card_input = col31.text_input("Account ID", label_visibility="collapsed", key="my_card")
    my_card_go_btn = col32.button("Go")

    if my_card_go_btn or st.session_state["card_submitted"]:

        all_ranking = get_ranking_data()

        st.session_state["card_submitted"] = True

        aux = prepare_ranking_to_show(all_ranking, drop_email=False)

        try:
            aux = aux.loc[
                (aux['ID']==card_input) \
                | (aux['Tag']==str(card_input)) \
                | (aux['Tag'].apply(lambda x: ":".join([hex(int(num))[2:].upper() for num in x.split("-")])) == str(card_input))\
                | (aux['User Email'] == card_input)
                          
                ]
        except:
            aux = pd.DataFrame()

        card_info = aux.copy()

        error = False

        try:
            if "@" in card_input:
                card_input = card_info["ID"].item()
            usage_dataframe, returns_dataframe, phone, email, payment = get_card_data(card_input)
        except Exception as e:
            st.error(e)
            error = True

        # the other information and gauge plots

        if error or len(card_info) == 0:
            st.error("Card not found!")
        else:
            if payment is not None:
                payment_type = payment.split(":")[0]
            else: 
                payment_type = "No details registered"

            new_phone = phone
            new_email = email

            colemail, colptype, colpdata = st.columns(3)
            with colemail:
                new_email = st.text_input('Email', value=email)
            with colptype:
                if payment_type == "No details registered":
                    new_payment = st.selectbox("Reward Payment", ["MBWay", "Revolut", "Paypal", "None"], index=0)
                elif payment_type == "MBWay":
                    new_payment = st.selectbox("Reward Payment", ["MBWay", "Revolut", "Paypal", "None"], index=0)
                elif payment_type == "revtag":
                    payment_type = "Revolut"
                    new_payment = st.selectbox("Reward Payment", ["Revolut", "MBWay", "Paypal", "None"], index=0)
                elif payment_type == "paypal":
                    payment_type = "Paypal"
                    new_payment = st.selectbox("Reward Payment", ["Paypal", "Revolut", "MBWay", "None"], index=0)
            with colpdata:
                if payment_type == new_payment:
                    if payment_type == "MBWay":
                        new_phone = st.text_input('Phone', value=phone)
                    elif payment_type == "Revolut":
                        new_revtag = st.text_input('Revtag', value=payment.split(":")[1])
                    elif payment_type == "Paypal":
                        new_paypal = st.text_input('Paypal', value=payment.split(":")[1])
                else:
                    if new_payment == "MBWay":
                        new_phone = st.text_input('Phone', placeholder="912345678")
                    elif new_payment == "Revolut":
                        new_revtag = st.text_input('Revtag', placeholder="@cr7")
                    elif new_payment == "Paypal":
                        new_paypal = st.text_input('Paypal', placeholder="cr7@gmail.com")
            
            update_btn = st.button('Update Info (not available, feature coming soon) ', disabled=True)

            if update_btn:
                if len(new_email) == 0:
                    valid = False
                    st.error("Missing Paypal email!")   
                elif not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
                    valid = False
                    st.error("Invalid Email!")
                if new_payment == "MBWay":
                    if len(new_phone) > 0:
                        if not new_phone.replace("+", "").replace(" ", "").isdigit():
                            valid = False
                            st.error("Invalid phone number!")
                    else:
                        st.error("Invalid phone number!")

                elif new_payment == "Revolut":
                    if len(new_revtag) == 0:
                        valid = False
                        st.error("Missing Revtag!")
                    else:
                        new_payment = f"revtag:{new_revtag}"
                elif new_payment == "Paypal":
                    if len(new_paypal) == 0:
                        valid = False
                        st.error("Missing Paypal email!")   
                    elif not re.match(r"[^@]+@[^@]+\.[^@]+", new_paypal):
                        valid = False
                        st.error("Invalid Paypal email!")
                    else:
                        new_payment = f"paypal:{new_paypal}"
                else:
                    new_payment = 'NULL'
                
                try:
                    queries.update_card_details(card_input, new_phone, new_email, new_payment)
                    st.success("Details Updated!")
                except Exception as e:
                    st.error(f"An error occured. Please try again! {e}") 

            if len(usage_dataframe["Daily"]) == 0 or len(usage_dataframe["Weekly"]) == 0 or len(usage_dataframe["Monthly"]) == 0:
                st.error("Card never used!")
            else:        
                user_name = card_info["User Name"].item()
                vertical_space(5)
                st.markdown(f"### {user_name}")

                col311, col312, col313 = st.columns(3)

                # Gauge plot for 'Drinks'
                with col311:
                    fig_drinks = go.Figure(go.Indicator(
                                    mode = "number+delta",
                                    value = int(round(float(card_info["Drinks"].item()))),
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
                    impact = int(round(float(card_info["Impact"].item())))
                    unit="g"
                    if impact > 1000:
                        impact = round(impact/1000, 1)
                        unit = "kg"
                    fig_impact = go.Figure(go.Indicator(
                                    mode = "number+delta",
                                    value = impact,
                                    title = {"text": f"Impact<br><span style='font-size:0.8em;color:gray'>{unit} of CO2</span><br>"},
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
            if len(df) > 0:
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
            else:
                st.warning("No cup returns yet")

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
            if len(df) > 0:
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
            else:
                st.warning("No cup returns yet")

            vertical_space(2)
            st.markdown("##### Last events")
            vertical_space(1)
            last_usage = queries.get_last_events(card_info["Tag"].item())
            if len(last_usage) > 0:
                last_usage = last_usage.loc[last_usage["cup_event_type"]!="Payment"]
                last_usage["event_time"] = last_usage["event_time"].dt.strftime('%Y-%m-%d %H:%M')
                last_usage["cup_event_type"] = last_usage["cup_event_type"].replace("Entered collector", "Left cup in smart bin").replace("Left dispenser", "Collected cup from dispenser")
                st.dataframe(last_usage[["event_time", "cup_event_type"]].rename(columns={"event_time": "Time", "cup_event_type": "Event"}), hide_index=True)
            else:
                st.warning("No usage yet!")

            if st.button("Refresh", key=1234):
                time.sleep(0.1)



with tab3:

    aux = prepare_ranking_to_show(all_ranking)
    total_usage_dataframe, total_returns_dataframe = get_all_data()

    aux = aux.loc[(~aux['ID'].isin(["-999", "1", "6", "2"]))&(aux["Last Event"]>='2024-01-30 00:00:00')]


    vertical_space(2)
    st.markdown(f"### Overall Metrics")
    vertical_space(2)

    col311, col312, col313 = st.columns(3)

    # Gauge plot for 'Drinks'
    with col311:
        fig_drinks = go.Figure(go.Indicator(
                        mode = "number+delta",
                        value = int(aux["Drinks"].sum()),
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
        impact = int(round(float(aux["Impact"].astype(float).sum())))
        unit="g"
        if impact > 1000:
            impact = round(impact/1000, 1)
            unit = "kg"
        fig_impact = go.Figure(go.Indicator(
                        mode = "number+delta",
                        value = impact,
                        title = {"text": f"Impact<br><span style='font-size:0.8em;color:gray'>{unit} of CO2</span><br>"},
                        domain = {'row': 0, 'column': 1}))

        st.plotly_chart(fig_impact, use_container_width=True)

    if len(total_usage_dataframe["Daily"]) == 0 or len(total_usage_dataframe["Weekly"]) == 0 or len(total_usage_dataframe["Monthly"]) == 0:
        st.error("No data")
    else:
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

with tab4:
    
    st.markdown("## Register")

    vertical_space(2)
 
    st.write("**Don't know the RFID tag of your U.Porto card?** It's so simple you won't believe it:")
    st.write("1. Install the mobile application NFC Tools ([Only For Android](https://play.google.com/store/apps/details?id=com.wakdev.wdnfc&hl=en&gl=US) ...Apple doesn't like student cards 🤷)")
    st.write("2. Select 'READ' and approach your U.Porto card towards your phone (you may need to turn on NFC in your phone before)")
    st.write("3. Your card RFID/ NFC ID is the 'Serial Number': an hexadecimal code similar to 9C:C0:57:52). Just copy and paste this number in the field below!")
    st.write("4. Voilà! Make sure your information is correct, so we can reward you for every 10 coffees you drink in a Loopack cup. If you have any questions [contact us](https://forms.gle/dmiCrKYZvB9CWwNf8), or check out [our FAQ](https://loopack.pt/faq.html)!")
    vertical_space(2)

    st.text("Your Name")
    username = st.text_input("User Name", label_visibility="collapsed", placeholder="Cristiano Ronaldo")

    st.text("U.Porto Card RFID/ NFC ID: Hexadecimal code retrieved from NFC Tools")
    card_id = st.text_input("Card RFID", label_visibility="collapsed", placeholder="9C:C0:57:52")

    st.text("Email (your university email or other)")
    email = st.text_input("Email", label_visibility="collapsed", placeholder='cr7@fe.up.pt')

    st.markdown(f"### {emoji.emojize(':coffee:')} Free Coffee Every 10 Uses!")
    st.text('(Optional) We need some payment details, and a valid email.')

    payment = st.selectbox('How Would You Like to be Rewarded?',("I don't want rewards", 'Paypal', 'Revolut', 'MBWay'))
    phone = None
    paypal = None
    revtag = None
    if payment == 'Paypal':
        paypal = st.text_input("Paypal Email", placeholder='cr7@gmail.com')
        phone = st.text_input("Phone Number", placeholder=912345678)
    
    elif payment == 'Revolut':
        revtag = st.text_input("Revtag", placeholder='@cr7')
        phone = st.text_input("Revolut Number", placeholder=912345678)

    elif payment == 'MBWay':
        phone = st.text_input("MBWay Number", placeholder=912345678)

    vertical_space(1)
    register_btn = st.button("Submit")

    if register_btn:

        valid = True

        # Check name
        if len(username) > 0:
            names_list = username.split(" ")
            username = names_list[0]
            if len(names_list) > 1:
                username += " " + names_list[-1]
        else:
            valid = False
            st.error("Missing user name!")

        # Check card ID
        if len(card_id) > 0:
            if ":" in card_id:
                card_id_decimal = []
                for hex_code in card_id.split(":"):
                    card_id_decimal.append(str(int(hex_code, 16)))
                card_id_decimal = "-".join(card_id_decimal)
            else:
                card_id_decimal = []
                for i in range(0, len(card_id)-1, 2):
                    hex_code = card_id[i:i+2]
                    card_id_decimal.append(str(int(hex_code, 16)))
                card_id_decimal = "-".join(card_id_decimal) 
        else:
            valid = False
            st.error("Missing card RFID!")

        # Check Email
        if len(email) == 0:
            valid = False
            st.error("Missing email!")
        else:
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                valid = False
                st.error("Invalid email!")

        # Check Payment Method
        if payment == "I don't want rewards":
            payment = None
        else:
            # Check Phone
            if len(phone) > 0:
                if not phone.replace("+", "").replace(" ", "").isdigit():
                    valid = False
                    st.error("Invalid phone number!")
            if payment == 'Revolut':
                if len(revtag) == 0:
                    valid = False
                    st.error("Missing Revtag!")
                else:
                    payment = f"revtag:{revtag}"
            elif payment == 'Paypal':
                if len(paypal) == 0:
                    valid = False
                    st.error("Missing Paypal email!")   
                elif not re.match(r"[^@]+@[^@]+\.[^@]+", paypal):
                    valid = False
                    st.error("Invalid Paypal email!")
                else:
                    payment = f"paypal:{paypal}"     

        
        if valid:
            try:
                validated = queries.validate_new_card_inputs(card_id_decimal, email, phone)
                if validated:
                    res = queries.register_card(card_id_decimal, username, email, phone, payment)
                    st.success('Card registered!', icon="✅")
                else:
                    st.error("The card ID, email or phone are already registered! If you think this is a mistake please [report here](https://forms.gle/dmiCrKYZvB9CWwNf8).")
            except Exception as e:
                st.error(f"Something went wrong! Please try again or report issue")
