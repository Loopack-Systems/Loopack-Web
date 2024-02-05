import pymysql
import pandas as pd
import streamlit as st

DATABASE_CREDENTIALS = {
    "HOST": st.secrets["DB_HOST"],
    "DATABASE": st.secrets["DB_DATABASE"],
    "USER": st.secrets["DB_USER"],
    "PASSWORD": st.secrets["DB_PASSWORD"]
}

class Queries():

    def __init__(self):
        
        self.conn = pymysql.connect(
             host=DATABASE_CREDENTIALS["HOST"],
             user=DATABASE_CREDENTIALS["USER"],    
             password=DATABASE_CREDENTIALS["PASSWORD"], 
             database=DATABASE_CREDENTIALS["DATABASE"],  
         )

    def get_cup_current_info(self, cup_id):

        self.cursor = self.conn.cursor()

        query = f"select cup_status_id, last_cup_event_type_id, current_device_id from cup where id = '{cup_id}'"
        self.cursor.execute(query)
        res = [tuple(row) for row in self.cursor.fetchall()]
        column_names = [column[0] for column in self.cursor.description]
        
        info_df = pd.DataFrame(res, columns=column_names)

        self.cursor.close()

        return info_df["cup_status_id"], info_df["last_cup_event_type_id"], info_df["current_device_id"]
    
    def __get_users_status(self):

        self.cursor = self.conn.cursor()

        query = """SELECT
                    c.number as card_number,
                    cet.name as last_event
                    FROM
                    cup_event ce
                    JOIN (
                        SELECT
                        refund_card_id,
                        MAX(event_time) AS last_event_time
                        FROM
                        cup_event
                        GROUP BY
                        refund_card_id
                    ) last_events ON ce.refund_card_id = last_events.refund_card_id
                    AND ce.event_time = last_events.last_event_time
                    JOIN card c ON c.id = ce.refund_card_id
                    JOIN cup_event_type cet ON cet.id = ce.cup_event_type_id
                """
        
        self.cursor.execute(query)
        res = [tuple(row) for row in self.cursor.fetchall()]
        column_names = [column[0] for column in self.cursor.description]
        
        df = pd.DataFrame(res, columns=column_names)
        df["currently_drinking"] = df["last_event"].apply(lambda x: True if x == "Left dispenser" else False)
        df = df.drop(columns=["last_event"])

        self.cursor.close()

        return df
    
    def get_users_ranking(self):

        self.cursor = self.conn.cursor()

        query = """with
                    drinks as (
                        select
                        refund_card_id,
                        count(cup_id) as num_drinks
                        from
                        cup_event
                        where
                        cup_event_type_id = 3 and fake = 0 and created_at > "2024-02-05"
                        group by
                        refund_card_id
                    ),
                    returned as (
                        select
                        refund_card_id,
                        count(cup_id) as num_returned_cups
                        from
                        cup_event
                        where
                        cup_event_type_id = 2 and fake = 0 and created_at > "2024-02-05"
                        group by
                        refund_card_id
                    ),
                    last_event as (
                        select
                        refund_card_id,
                        max(event_time) as last_event
                        from
                        cup_event
                      	where fake = 0 and created_at > "2024-02-05"
                        group by
                        refund_card_id
                    )
                    select
                    d.refund_card_id as card_id,
                    c.number as card_number,
                    c.name as user_name,
                    c.email as user_email,
                    d.num_drinks,
                    r.num_returned_cups,
                    r.num_returned_cups * 20.69 as impact,
                    le.last_event
                    from
                    drinks d
                    left join returned r on d.refund_card_id = r.refund_card_id
                    left join last_event le on d.refund_card_id = le.refund_card_id
                    left join card c on c.id = d.refund_card_id
                    where
                    (
                        c.is_test = 0
                        or c.is_test is null
                    )
                    and d.refund_card_id not in(-998, -999)
                    union
                    select
                    id as card_id,
                    number as card_number,
                    name as user_name,
                    email as user_email,
                    0 as num_drinks,
                    0 as num_returned_cups,
                    0 as impact,
                    NULL as last_event
                    from
                    card
                    where
                    id not in(
                      select distinct refund_card_id 
                      from cup_event
                      where fake = 0 and created_at > "2024-02-05"
                    )
                    and is_test = 0
                """
        
        self.cursor.execute(query)
        res = [tuple(row) for row in self.cursor.fetchall()]
        column_names = [column[0] for column in self.cursor.description]
        
        df = pd.DataFrame(res, columns=column_names)
        df["num_drinks"] = df["num_drinks"].fillna(0)
        df["num_returned_cups"] = df["num_returned_cups"].fillna(0)
        df["impact"] = df["impact"].fillna(0)

        df["user_name"] = df["user_name"].fillna("-999")
        df["user_email"] = df["user_email"].fillna("-999")

        status = self.__get_users_status()

        df = df.merge(status, on="card_number", how="left")
        df["currently_drinking"] = df["currently_drinking"].fillna(False)
        df = df.sort_values(by="num_returned_cups")

        df = df[["card_id", "card_number", "user_name", "user_email", "num_drinks", "num_returned_cups", "impact", "currently_drinking", "last_event"]]

        self.cursor.close()

        return df
    
    def get_all_temporal_usage(self):

        self.cursor = self.conn.cursor()

        query_daily = f"""
                    select
                    DATE_FORMAT(event_time, "%Y-%m-%d") as day,
                    count(cup_id) as num_drinks
                    from
                    cup_event ce
                    left join card c on c.id = ce.refund_card_id
                    where
                    cup_event_type_id = 3 and event_time >= '2024-02-05 00:00:00'
                    group by
                    DATE_FORMAT(event_time, "%Y-%m-%d")
                    order by
                    DATE_FORMAT(event_time, "%Y-%m-%d") asc
                    """
        
        self.cursor.execute(query_daily)
        res = [tuple(row) for row in self.cursor.fetchall()]
        column_names = [column[0] for column in self.cursor.description]
        df_daily = pd.DataFrame(res, columns=column_names)
        df_daily = df_daily.rename(columns={'day': 'event_time'})
        df_daily["event_time"] = pd.to_datetime(df_daily["event_time"])

        query_weekly = f"""
                    SELECT
                    DATE_FORMAT(
                        ADDDATE(event_time, INTERVAL - DAYOFWEEK(event_time) DAY),
                        "%Y-%m-%d"
                    ) as week,
                    COUNT(cup_id) AS num_drinks
                    FROM
                    cup_event ce 
                    left join card c on c.id = ce.refund_card_id
                    where
                    cup_event_type_id = 3 and event_time >= '2024-01-30 00:00:00'
                    GROUP BY
                    week
                    ORDER BY week ASC
                    """
        
        self.cursor.execute(query_weekly)
        res = [tuple(row) for row in self.cursor.fetchall()]
        column_names = [column[0] for column in self.cursor.description]
        df_weekly = pd.DataFrame(res, columns=column_names)
        df_weekly = df_weekly.rename(columns={'week': 'event_time'})
        df_weekly["event_time"] = pd.to_datetime(df_weekly["event_time"])

        query_monthly = f"""
                        select
                        DATE_FORMAT(event_time, "%Y-%m-01") as month,
                        count(cup_id) as num_drinks
                        from
                        cup_event ce
                        left join card c on c.id = ce.refund_card_id
                        where
                        cup_event_type_id = 3 and event_time >= '2024-01-30 00:00:00'
                        group by
                        month
                        order by
                        month asc
                    """
        
        self.cursor.execute(query_monthly)
        res = [tuple(row) for row in self.cursor.fetchall()]
        column_names = [column[0] for column in self.cursor.description]
        df_monthly = pd.DataFrame(res, columns=column_names)
        df_monthly = df_monthly.rename(columns={'month': 'event_time'})
        df_monthly["event_time"] = pd.to_datetime(df_monthly["event_time"])

        self.cursor.close()

        return df_daily, df_weekly, df_monthly
    

    def get_all_temporal_returns(self):

        self.cursor = self.conn.cursor()

        query_daily = f"""
                    select
                    DATE_FORMAT(event_time, "%Y-%m-%d") as day,
                    count(cup_id) as num_drinks
                    from
                    cup_event ce
                    left join card c on c.id = ce.refund_card_id
                    where
                    cup_event_type_id = 2 and event_time >= '2024-02-05 00:00:00'
                    group by
                    DATE_FORMAT(event_time, "%Y-%m-%d")
                    order by
                    DATE_FORMAT(event_time, "%Y-%m-%d") asc
                    """
        
        self.cursor.execute(query_daily)
        res = [tuple(row) for row in self.cursor.fetchall()]
        column_names = [column[0] for column in self.cursor.description]
        df_daily = pd.DataFrame(res, columns=column_names)
        df_daily = df_daily.rename(columns={'day': 'event_time'})
        df_daily["event_time"] = pd.to_datetime(df_daily["event_time"])

        query_weekly = f"""
                    SELECT
                    DATE_FORMAT(
                        ADDDATE(event_time, INTERVAL - DAYOFWEEK(event_time) DAY),
                        "%Y-%m-%d"
                    ) as week,
                    COUNT(cup_id) AS num_drinks
                    FROM
                    cup_event ce 
                    left join card c on c.id = ce.refund_card_id
                    where
                    cup_event_type_id = 2 and event_time >= '2024-01-30 00:00:00'
                    GROUP BY
                    week
                    ORDER BY week ASC
                    """
        
        self.cursor.execute(query_weekly)
        res = [tuple(row) for row in self.cursor.fetchall()]
        column_names = [column[0] for column in self.cursor.description]
        df_weekly = pd.DataFrame(res, columns=column_names)
        df_weekly = df_weekly.rename(columns={'week': 'event_time'})
        df_weekly["event_time"] = pd.to_datetime(df_weekly["event_time"])

        query_monthly = f"""
                        select
                        DATE_FORMAT(event_time, "%Y-%m-01") as month,
                        count(cup_id) as num_drinks
                        from
                        cup_event ce
                        left join card c on c.id = ce.refund_card_id
                        where
                        cup_event_type_id = 2 and event_time >= '2024-01-30 00:00:00'
                        group by
                        month
                        order by
                        month asc
                    """
        
        self.cursor.execute(query_monthly)
        res = [tuple(row) for row in self.cursor.fetchall()]
        column_names = [column[0] for column in self.cursor.description]
        df_monthly = pd.DataFrame(res, columns=column_names)
        df_monthly = df_monthly.rename(columns={'month': 'event_time'})
        df_monthly["event_time"] = pd.to_datetime(df_monthly["event_time"])

        self.cursor.close()

        return df_daily, df_weekly, df_monthly    
    
    def get_temporal_usage(self, card_number):

        self.cursor = self.conn.cursor()

        query_daily = f"""
                    select
                    DATE_FORMAT(event_time, "%Y-%m-%d") as day,
                    count(cup_id) as num_drinks
                    from
                    cup_event ce
                    join card c on c.id = ce.refund_card_id
                    where
                    c.number = '{card_number}'
                    and cup_event_type_id = 3
                    group by
                    DATE_FORMAT(event_time, "%Y-%m-%d")
                    order by
                    DATE_FORMAT(event_time, "%Y-%m-%d") asc
                    """
        
        self.cursor.execute(query_daily)
        res = [tuple(row) for row in self.cursor.fetchall()]
        column_names = [column[0] for column in self.cursor.description]
        df_daily = pd.DataFrame(res, columns=column_names)
        df_daily = df_daily.rename(columns={'day': 'event_time'})
        df_daily["event_time"] = pd.to_datetime(df_daily["event_time"])

        query_weekly = f"""
                    SELECT
                    DATE_FORMAT(
                        ADDDATE(event_time, INTERVAL - DAYOFWEEK(event_time) DAY),
                        "%Y-%m-%d"
                    ) as week,
                    COUNT(cup_id) AS num_drinks
                    FROM
                    cup_event ce 
                    join card c on c.id = ce.refund_card_id
                    where
                    c.number = '{card_number}'
                    and cup_event_type_id = 3
                    GROUP BY
                    week
                    ORDER BY week ASC
                    """
        
        self.cursor.execute(query_weekly)
        res = [tuple(row) for row in self.cursor.fetchall()]
        column_names = [column[0] for column in self.cursor.description]
        df_weekly = pd.DataFrame(res, columns=column_names)
        df_weekly = df_weekly.rename(columns={'week': 'event_time'})
        df_weekly["event_time"] = pd.to_datetime(df_weekly["event_time"])

        query_monthly = f"""
                        select
                        DATE_FORMAT(event_time, "%Y-%m-01") as month,
                        count(cup_id) as num_drinks
                        from
                        cup_event ce
                        join card c on c.id = ce.refund_card_id
                        where
                        c.number = '{card_number}'
                        and cup_event_type_id = 3
                        group by
                        month
                        order by
                        month asc
                    """
        
        self.cursor.execute(query_monthly)
        res = [tuple(row) for row in self.cursor.fetchall()]
        column_names = [column[0] for column in self.cursor.description]
        df_monthly = pd.DataFrame(res, columns=column_names)
        df_monthly = df_monthly.rename(columns={'month': 'event_time'})
        df_monthly["event_time"] = pd.to_datetime(df_monthly["event_time"])

        self.cursor.close()

        return df_daily, df_weekly, df_monthly
    
    def get_temporal_returns(self, card_number):

            self.cursor = self.conn.cursor()

            query_daily = f"""
                        select
                        DATE_FORMAT(event_time, "%Y-%m-%d") as day,
                        count(cup_id) as num_drinks
                        from
                        cup_event ce
                        join card c on c.id = ce.refund_card_id
                        where
                        c.number = '{card_number}'
                        and cup_event_type_id = 2
                        group by
                        DATE_FORMAT(event_time, "%Y-%m-%d")
                        order by
                        DATE_FORMAT(event_time, "%Y-%m-%d") asc
                        """
            
            self.cursor.execute(query_daily)
            res = [tuple(row) for row in self.cursor.fetchall()]
            column_names = [column[0] for column in self.cursor.description]
            df_daily = pd.DataFrame(res, columns=column_names)
            df_daily = df_daily.rename(columns={'day': 'event_time'})
            df_daily["event_time"] = pd.to_datetime(df_daily["event_time"])

            query_weekly = f"""
                        SELECT
                        DATE_FORMAT(
                            ADDDATE(event_time, INTERVAL - DAYOFWEEK(event_time) DAY),
                            "%Y-%m-%d"
                        ) as week,
                        COUNT(cup_id) AS num_drinks
                        FROM
                        cup_event ce 
                        join card c on c.id = ce.refund_card_id
                        where
                        c.number = '{card_number}'
                        and cup_event_type_id = 2
                        GROUP BY
                        week
                        ORDER BY week ASC
                        """
            
            self.cursor.execute(query_weekly)
            res = [tuple(row) for row in self.cursor.fetchall()]
            column_names = [column[0] for column in self.cursor.description]
            df_weekly = pd.DataFrame(res, columns=column_names)
            df_weekly = df_weekly.rename(columns={'week': 'event_time'})
            df_weekly["event_time"] = pd.to_datetime(df_weekly["event_time"])

            query_monthly = f"""
                            select
                            DATE_FORMAT(event_time, "%Y-%m-01") as month,
                            count(cup_id) as num_drinks
                            from
                            cup_event ce
                            join card c on c.id = ce.refund_card_id
                            where
                            c.number = '{card_number}'
                            and cup_event_type_id = 2
                            group by
                            month
                            order by
                            month asc
                        """
            
            self.cursor.execute(query_monthly)
            res = [tuple(row) for row in self.cursor.fetchall()]
            column_names = [column[0] for column in self.cursor.description]
            df_monthly = pd.DataFrame(res, columns=column_names)
            df_monthly = df_monthly.rename(columns={'month': 'event_time'})
            df_monthly["event_time"] = pd.to_datetime(df_monthly["event_time"])

            self.cursor.close()

            return df_daily, df_weekly, df_monthly

    def get_card_details(self, card_number):
        self.cursor = self.conn.cursor()

        query = f"""
                    SELECT number, email, payment
                    FROM card 
                    WHERE number = {card_number}
                    """
        self.cursor.execute(query)
        res = [tuple(row) for row in self.cursor.fetchall()]
        self.cursor.close()

        phone = res[0][0]
        email = res[0][1]
        payment = res[0][2]
        return phone, email, payment
    
    def update_card_details(self, card_number, new_phone, new_email, new_payment):
        self.cursor = self.conn.cursor()

        query = f"""
                    UPDATE card
                    SET number = {new_phone}, email = '{new_email}', payment = '{new_payment}'
                    WHERE number = {card_number}
                    """
        self.cursor.execute(query)
        self.cursor.close()



    def register_card(self, card_id_decimal, username, email, phone, payment):

        self.cursor = self.conn.cursor()

        query = f"insert into card (id, number, name, email, is_test, payment) values ('{card_id_decimal}', '{phone}', '{username}', '{email}', 0, '{payment}')"
        if payment is None:
            query = f"insert into card (id, number, name, email, is_test) values ('{card_id_decimal}', 0, '{username}', '{email}', 0)"

        res = self.cursor.execute(query)
        self.conn.commit()
        self.cursor.close()

        return res
    
    def validate_new_card_inputs(self, card_id_decimal, email, phone):

        self.cursor = self.conn.cursor()

        query = f"select id from card where id = '{card_id_decimal}' or number = '{phone}' or email = '{email}'"

        self.cursor.execute(query)
        res = [tuple(row) for row in self.cursor.fetchall()]
        column_names = [column[0] for column in self.cursor.description]

        df = pd.DataFrame(res, columns=column_names)

        self.cursor.close()

        if len(df) == 0:
            return True
        else:
            return False
        
    def get_last_events(self, card_input):

        self.cursor = self.conn.cursor()

        query = f"""
                SELECT event_time, device_id, cup_event_type
                FROM (
                    SELECT event_time, device_id, cet.name as cup_event_type
                    FROM cup_event ce
                    JOIN cup_event_type cet on ce.cup_event_type_id = cet.id
                    WHERE refund_card_id = '{card_input}'
                    UNION ALL
                    SELECT event_time, device_id, "Payment" as cup_event_type
                    FROM payment_event
                    WHERE refund_card_id = '{card_input}'
                ) AS combined_result
                WHERE event_time > CURRENT_DATE - INTERVAL 1 DAY
                ORDER BY event_time DESC;
                """

        self.cursor.execute(query)

        res = [tuple(row) for row in self.cursor.fetchall()]
        column_names = [column[0] for column in self.cursor.description]

        df = pd.DataFrame(res, columns=column_names)

        self.cursor.close()

        return df