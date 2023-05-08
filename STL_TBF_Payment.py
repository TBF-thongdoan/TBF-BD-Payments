# %%
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from  plotly.subplots  import  make_subplots

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, datetime, timedelta

# %%
#------------------------------------------------------------------------------------PHẦN TIÊU ĐỀ WEB-------------------------------------------------------------------------------------
st.set_page_config(page_icon= 'https://static.wixstatic.com/media/91d4d0_50c2e78106264db2a9ddda29a7ad0503~mv2.png/v1/fit/w_2500,h_1330,al_c/91d4d0_50c2e78106264db2a9ddda29a7ad0503~mv2.png',page_title='THE BIM FACTORY', layout='wide')
st.title('BIM Fee for Raffles MUR TD & SD')

st.sidebar.header("Options filter")

# %%
ss_cred_path ='credentials2.json' # Your path to the json credential file
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive'] # define the scope
creds = ServiceAccountCredentials.from_json_keyfile_name(ss_cred_path, scope) # add credentials to the account
client = gspread.authorize(creds) # authorize the clientsheet

# %%
sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1yKc8ZxllaubaL_iMWXGWKHOLZ29_EgXbCg-QGHIO9-Q/edit?usp=sharing')
ws = sheet.worksheet('All data')
df = pd.DataFrame(ws.get_values('A3:L', value_render_option = 'UNFORMATTED_VALUE'))
df.columns = df.iloc[0]
df = df.drop(df.index[0])
df = df.drop(['Notes','Invoice No.', 'Original Amount', 'Currency'], axis=1)
df = df[~df['Client'].str.contains('TBF')]
print(df)

# %%
df['Date Invoice']      = df['Date Invoice'].replace("", 0)
df['Date Due']          = df['Date Due'].replace("", 0)
df['Date Paid']         = df['Date Paid'].replace("", 0)
df['Paid VND']          = df['Paid VND'].replace("", 0)


df['Date Invoice']      = df['Date Invoice'].astype(int)
df['Date Due']          = df['Date Due'].astype(int)
df['Date Paid']         = df['Date Paid'].astype(int)

df['EQ VND (auto)']     = df['EQ VND (auto)'].astype(float)
df['Paid VND']          = df['Paid VND'].astype(float)

df['EQ VND (auto)']     = df['EQ VND (auto)'].astype(int)
df['Paid VND']          = df['Paid VND'].astype(int)

print(df.info())

# %%
def convert_date(number):
    delta = timedelta(days=number)
    start_date = date(1900, 1, 1)
    result_date = start_date + delta
    return result_date.strftime('%m/%d/%Y')


df['Date Invoice']  = df['Date Invoice'].apply(convert_date)
df['Date Due']      = df['Date Due'].apply(convert_date)
df['Date Paid']     = df['Date Paid'].apply(convert_date)

df['Date Invoice']  = pd.to_datetime(df['Date Invoice'])
df['Date Due']      = pd.to_datetime(df['Date Due'])
df['Date Paid']     = pd.to_datetime(df['Date Paid'])
print(df)

# %%
df['Date Invoice']          = df['Date Invoice'].dt.date
df['Date Due']              = df['Date Due'].dt.date
df['Date Paid']             = df['Date Paid'].dt.date


df = df[df['Date Invoice'] >= date(2022,1,1)]
df

chart2   =  make_subplots ( specs = [[{ "secondary_y" :  True}]]) 
chart2 .add_trace(
        go.Bar(x=df['Date Invoice'], y=df['Client'],
               name= 'Participants by date',
               marker_color = '#333333', 
               text=df['Client']),
               secondary_y=False)

chart2 .update_layout(yaxis2 = dict(range = [0,10000]),
                      yaxis1 = dict (range = [0,10000]),
                      xaxis = dict(type='date',
                                nticks=40,
                                tickformat="%d\n%b - %Y",
                                tickangle=0,)
                        )
chart2.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="left",
            x=0.05
            ))

st.plotly_chart(chart2, use_container_width=True)
# %%


# %%
# RUN STREAMLIT FILE
# streamlit run "D:\Documents\Ty\THE BIM FACTORY 4.7.2022\Streamlit_app\TBF_Payments\STL_TBF_Payment.py"

# ---------CREATE REQUIREMENTS FILE
# pip install pipreqs
# pipreqs 'D:\Documents\Ty\THE BIM FACTORY 4.7.2022\Streamlit_app\TBF_Payments' --encoding=utf-8

