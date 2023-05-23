import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from  plotly.subplots  import  make_subplots
from streamlit_plotly_events import plotly_events

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, datetime, timedelta

#------------------------------------------------------------------------------------PHẦN TIÊU ĐỀ WEB-------------------------------------------------------------------------------------
st.set_page_config(page_icon= 'https://static.wixstatic.com/media/91d4d0_50c2e78106264db2a9ddda29a7ad0503~mv2.png/v1/fit/w_2500,h_1330,al_c/91d4d0_50c2e78106264db2a9ddda29a7ad0503~mv2.png',page_title='TBF Payment Monthly', layout='wide')
st.title('TBF - BD - Monthly Payments Report')

st.sidebar.header("Options filter")

# %% CÁC HÀM 
# Hàm chuyển ngày dạng timestamp thành dạng ngày
def convert_date(number):
    delta           = timedelta(days=number - 2)
    start_date      = date(1900, 1, 1)
    result_date     = start_date + delta
    return result_date.strftime('%m/%d/%Y')

# Hàm giảm đi 30 ngày
def subtract_day(date_str):
    date_str        = str (date_str)
    date_obj        = datetime.fromisoformat(date_str)
    unix_time       = int(date_obj.timestamp())
    new_unix_time   = unix_time - 86400 * 30
    new_date_obj    = datetime.fromtimestamp(new_unix_time)
    new_date_str    = new_date_obj.strftime('%Y-%m-%d')
    return new_date_str

# %% LẤY DỮ LIỆU TỪ GG SHEET
ss_cred_path    = 'credentials2.json' # Your path to the json credential file
scope           = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive'] # define the scope
creds           = ServiceAccountCredentials.from_json_keyfile_name(ss_cred_path, scope) # add credentials to the account
client          = gspread.authorize(creds) # authorize the clientsheet

sheet       = client.open_by_url('https://docs.google.com/spreadsheets/d/1yKc8ZxllaubaL_iMWXGWKHOLZ29_EgXbCg-QGHIO9-Q/edit?usp=sharing')
ws          = sheet.worksheet('All data copy (Thông)')
df          = pd.DataFrame(ws.get_values('A1:Q', value_render_option = 'UNFORMATTED_VALUE'))
df.columns  = df.iloc[0]
df          = df.drop(df.index[0])
df          = df[~df['Client'].str.contains('TBF')]
df          = df.drop([' EQ VND (auto) ',' Paid VND ', 'Date Due', 'Date Invoice', 'Date Paid','Invoice No.', 'Original Amount','Project Name'], axis=1)
df          = df.loc[(df['Status'] != '')]

# Loại bỏ 6 ký tự đầu tiên trong chuỗi
df['Client']            = df['Client'].str.slice(start = 8)
df['Active Clientss']   = df['Active Clientss'].str.slice(start = 8)


# %% LÀM SẠCH DỮ LIỆU SAU KHI LẤY TỪ GG SHEET
df['Date Invoice (R)']              = df['Date Invoice (R)'].replace("", 0)
df['Date Paid (R)']                 = df['Date Paid (R)'].replace("", 0)
df['Days Late (R)']                 = df['Days Late (R)'].replace("", 0)
df['Remaining Amount (R)']          = df['Remaining Amount (R)'].replace("", 0)
df['Active Remaining Amount (R)']   = df['Active Remaining Amount (R)'].replace("", 0)

df['Date Invoice (R)']              = df['Date Invoice (R)'].astype(int)
df['Date Paid (R)']                 = df['Date Paid (R)'].astype(int)
df['Days Late (R)']                 = df['Days Late (R)'].astype(int)

df['Remaining Amount (R)']          = df['Remaining Amount (R)'].astype(float)
df['Active Remaining Amount (R)']   = df['Active Remaining Amount (R)'].astype(float)


df['Date Invoice (R)']              = df['Date Invoice (R)'].apply(convert_date)
df['Date Paid (R)']                 = df['Date Paid (R)'].apply(convert_date)

df['Date Invoice (R)']              = pd.to_datetime(df['Date Invoice (R)'])
df['Date Paid (R)']                 = pd.to_datetime(df['Date Paid (R)'])



# %% BIỀU ĐỒ 1: Payment (based on payment receipt dates) --------------------------------------------
df_Payment      = df
df_Payment      = df_Payment[df_Payment['Date Paid (R)'] >= datetime(2023,1,1)]
df_Payment      = df_Payment.loc[(df_Payment['Status'] != '3-Forecasted') & (df_Payment['Status'] != '-1-Disputed') & (df_Payment['Status'] != '4-Temp') ]

df_Payment_1    = df_Payment.groupby(['Status', pd.Grouper(key='Date Paid (R)', freq='M')])['Remaining Amount (R)'].sum().reset_index()
df_Payment_2    = df_Payment.groupby([pd.Grouper(key='Date Paid (R)', freq='M')])['Remaining Amount (R)'].sum().reset_index()

df_Payment_1['Date Paid (R)'] = df_Payment_1['Date Paid (R)'].apply(subtract_day)
df_Payment_2['Date Paid (R)'] = df_Payment_2['Date Paid (R)'].apply(subtract_day)

chart_Payments   =  make_subplots ( specs = [[{ "secondary_y" :  True}]]) 

# Biểu đồ BAR
chart_Payments.add_trace(
        go.Bar(x                    = df_Payment_1['Date Paid (R)'],
               y                    = df_Payment_1['Remaining Amount (R)'] ,
               name                 = 'Payments (based on payment receipt dates)',
               hovertemplate        = '<b>Date Paid:</b> %{x}<br><b>Remaining Amount:</b> %{y}<br><b>Status:</b> %{customdata}',
               customdata           = df_Payment_1['Status'],
               marker_color         = df_Payment_1['Status'].map({'0-Fully Paid': 'gray', '1-Outstanding': '#ef233c', '2-Contracted': '#0353a4'})
               ),
               secondary_y          = False
            )

# Biểu đồ LINE
chart_Payments.add_trace(
        go.Scatter(x                = df_Payment_2['Date Paid (R)'],
                   y                = df_Payment_2['Remaining Amount (R)'].cumsum(),
                   name             = 'Accumulated Man-hours',
                   mode             = 'lines + markers + text',
                   textposition     = 'top center',
                   textfont         = dict(color = 'black', size = 10),
                   text             = df_Payment_2['Remaining Amount (R)'].cumsum(),
                   line             = dict(color = 'black', width = 3) # đặt màu đường là red và độ dày là 2),
                   ),  
                   secondary_y      = True,
                   )

chart_Payments.update_layout(yaxis1  = dict(range = [0,10000000000]),
                             yaxis2  = dict (range = [0,40000000000]),
                             xaxis   = dict(type='date',
                                        # nticks=40,
                                        # tickformat="%d\n%b - %Y",
                                        # tickangle=0,
                                        )
                            )

chart_Payments.update_layout(
                            title='Payment (based on payment receipt dates)',
                            legend = dict(
                                orientation = 'h',
                                yanchor     = 'bottom',
                                y           = 1.02,
                                xanchor     = 'left',
                                x           = 0,
                                font        = dict(size=12),
                                itemsizing  = 'constant',
                                bgcolor     = 'rgba(0,0,0,0)'
                                ),
                            barmode = 'group'
)

# %% BIỀU ĐỒ 2: TOP 10 CLIENTS --------------------------------------------
df_Top_Client     = df
df_Top_Client     = df_Top_Client.loc[(df_Top_Client['Status'] != '3-Forecasted') & (df_Top_Client['Status'] != '-1-Disputed') & (df_Top_Client['Status'] != '4-Temp') ]


# Lấy ra danh sách TOP 10 Client cao nhất từ trước tới giờ
df_Top_Client_1                 = df_Top_Client.groupby(['Status', 'Client'])['Remaining Amount (R)'].sum().reset_index()

df_Top_Client_1_CheckClient     = df_Top_Client_1.groupby(['Client'])['Remaining Amount (R)'].sum().reset_index()
top_10_clients                  = df_Top_Client_1_CheckClient.nlargest(10, 'Remaining Amount (R)')
client_list                     = top_10_clients['Client'].to_list()

# Lọc ra được danh sách 10 khách hàng "NO ACTIVE"
df_Top_Client_1 = df_Top_Client_1[df_Top_Client_1['Client'].isin(client_list)] 
df_Top_Client_1 = df_Top_Client_1.sort_values('Status')

# Lấy ra danh sách TOP 10 Client Active
df_Top_Client_2                 = df_Top_Client
df_Top_Client_2                 = df_Top_Client_2.groupby(['Status', 'Active Clientss'])['Active Remaining Amount (R)'].sum().reset_index()

df_Top_Client_2_CheckClient     = df_Top_Client_2.groupby(['Active Clientss'])['Active Remaining Amount (R)'].sum().reset_index()
top_10_clients2                 = df_Top_Client_2_CheckClient.nlargest(10, 'Active Remaining Amount (R)')
client_list_2                   = top_10_clients2['Active Clientss'].to_list()

# Lọc ra được danh sách 10 khách hàng "NO ACTIVE"
df_Top_Client_2     = df_Top_Client_2[df_Top_Client_2['Active Clientss'].isin(client_list_2)]
df_Top_Client_2     = df_Top_Client_2[df_Top_Client_2['Active Clientss'] != ""]
df_Top_Client_2     = df_Top_Client_2.sort_values('Status')


# Tạo một selectbox trong sidebar với danh sách tùy chọn
selected_option     = (st.sidebar.checkbox("Clients no ACTIVE") == False)

if selected_option: # Active
    df_ACTIVE_or_NoACTIVE   = df_Top_Client_2
    X                       = 'Active Remaining Amount (R)'
    Y                       = 'Active Clientss'
    TITLE                   = 'TOP 10 clients - ACTIVE ✅'
else: # No Active
    df_ACTIVE_or_NoACTIVE   = df_Top_Client_1
    X                       = 'Remaining Amount (R)'
    Y                       = 'Client'
    TITLE                   = 'TOP 10 clients'

chart_Active = px.bar(df_ACTIVE_or_NoACTIVE,
                x                       = X,
                y                       = Y,
                title                   = TITLE,
                orientation             = 'h',
                color                   = 'Status',
                # text_auto             = True,
                color_discrete_sequence = ['gray','#ef233c','#0353a4']
)

chart_Active.update_layout(legend=dict(
                                orientation     = "h",
                                yanchor         = "bottom",
                                y               = -0.4,
                                xanchor         = "left",
                                x               = 0.01
                            )
)


chart_Active.update_yaxes(categoryorder = 'total ascending')

# %% TABLE LIST CLIENT ----------------------------------------

df_List_Client          = df
df_List_Client          = df_List_Client[df_List_Client['Date Paid (R)'] >= datetime(2023,1,1)]
df_List_Client          = df_List_Client[['Status', 'Client', 'Date Paid (R)', 'Days Late (R)', 'Remaining Amount (R)']]
df_List_Client          = df_List_Client.loc[(df_List_Client['Status'] != '3-Forecasted') & (df_List_Client['Status'] != '-1-Disputed') & (df_List_Client['Status'] != '4-Temp') & (df_List_Client['Status'] != '0-Fully Paid')]
df_List_Client2         = df_List_Client.groupby(['Status', 'Client'])['Days Late (R)'].mean().reset_index()
df_List_Client1         = df_List_Client.groupby(['Status', 'Client'])['Remaining Amount (R)'].sum().reset_index()
group_df_List_Client    = df_List_Client1.join(df_List_Client2.set_index(['Status', 'Client']), on=(['Status', 'Client']))

group_df_List_Client['Remaining Amount (R)']    = group_df_List_Client['Remaining Amount (R)'].astype(int)
group_df_List_Client['Days Late (R)']           = group_df_List_Client['Days Late (R)'].astype(int)
group_df_List_Client['Remaining Amount (R)']    = group_df_List_Client['Remaining Amount (R)'] .apply(lambda x: '{:,.0f}  VND'.format(x))


# %% TƯƠNG TÁC VỚI STREAMLIT


data_selected = plotly_events(
    chart_Payments,
    select_event=True,
)

st.write(data_selected)

data_list = { el["y"] for el in data_selected}
st.write (data_list)

col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(chart_Active, use_container_width=True) # BIỂU ĐỒ 2 - Data dựa trên checkbox, unsafe_allow_html=True )
    
with col2:
    st.table(group_df_List_Client)
    

    


# %%
# RUN STREAMLIT FILE
# streamlit run "D:\Documents\Ty\THE BIM FACTORY 4.7.2022\Streamlit_app\TBF_Payments\STL_TBF_Payment.py"

# ---------CREATE REQUIREMENTS FILE
# pip install pipreqs
# pipreqs 'D:\Documents\Ty\THE BIM FACTORY 4.7.2022\Streamlit_app\TBF_Payments\TBF-BD-Payments' --encoding=utf-8 ( --force (Để ghi đè lên tệp đã tồn tại) )