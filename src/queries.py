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
                        cup_event_type_id = 3
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
                        cup_event_type_id = 2
                        group by
                        refund_card_id
                    )
                    select
                    c.number as card_number,
                    c.name as user_name,
                    c.email as user_email,
                    d.num_drinks,
                    r.num_returned_cups,
                    r.num_returned_cups * 0.1 as impact
                    from
                    drinks d
                    join returned r on d.refund_card_id = r.refund_card_id
                    right join card c on c.id = d.refund_card_id
                """
        
        self.cursor.execute(query)
        res = [tuple(row) for row in self.cursor.fetchall()]
        column_names = [column[0] for column in self.cursor.description]
        
        df = pd.DataFrame(res, columns=column_names)
        df["num_drinks"] = df["num_drinks"].fillna(0)
        df["num_returned_cups"] = df["num_drinks"].fillna(0)
        df["num_returned_cups"] = df["num_drinks"].fillna(0)
        df["impact"] = df["impact"].fillna(0)

        df["user_name"] = df["user_name"].fillna("-999")
        df["user_email"] = df["user_email"].fillna("-999")

        status = self.__get_users_status()

        df = df.merge(status, on="card_number", how="left")
        df["currently_drinking"] = df["currently_drinking"].fillna(False)
        df = df.sort_values(by="num_returned_cups")

        self.cursor.close()

        print(df)

        return df
    
    def get_all_temporal_usage(self):

        self.cursor = self.conn.cursor()

        query_daily = f"""
                    select
                    DATE_FORMAT(event_time, "%Y-%m-%d") as day,
                    count(cup_id) as num_drinks
                    from
                    cup_event ce
                    join card c on c.id = ce.refund_card_id
                    where
                    cup_event_type_id = 3
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
                    cup_event_type_id = 3
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
                        cup_event_type_id = 3
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
                    join card c on c.id = ce.refund_card_id
                    where
                    cup_event_type_id = 2
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
                    cup_event_type_id = 2
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
                        cup_event_type_id = 2
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

        