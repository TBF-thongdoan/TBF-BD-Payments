import streamlit as st
from streamlit_echarts import st_echarts

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, datetime, timedelta
import pandas as pd

st.set_page_config(page_icon = 'https://static.wixstatic.com/media/91d4d0_50c2e78106264db2a9ddda29a7ad0503~mv2.png/v1/fit/w_2500,h_1330,al_c/91d4d0_50c2e78106264db2a9ddda29a7ad0503~mv2.png',page_title='TBF Payments', layout='wide')

@st.cache_data
def load_data():
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
    
    df = df.rename(columns={'Date Paid (R)':                'Date Paid'})
    df = df.rename(columns={'Date Invoice (R)':             'Date Invoice'})
    df = df.rename(columns={'Days Late (R)':                'Days Late'})
    df = df.rename(columns={'Active Remaining Amount (R)':  'Active Remaining Amount'})
    df = df.rename(columns={'Remaining Amount (R)':         'Remaining Amount'})
    
    df['Date Invoice']              = df['Date Invoice'].replace("", 0)
    df['Date Paid']                 = df['Date Paid'].replace("", 0)
    df['Days Late']                 = df['Days Late'].replace("", 0)
    df['Remaining Amount']          = df['Remaining Amount'].replace("", 0)
    df['Active Remaining Amount']   = df['Active Remaining Amount'].replace("", 0)

    df['Date Invoice']              = df['Date Invoice'].astype(int)
    df['Date Paid']                 = df['Date Paid'].astype(int)
    df['Days Late']                 = df['Days Late'].astype(int)

    df['Remaining Amount']          = df['Remaining Amount'].astype(float)
    df['Active Remaining Amount']   = df['Active Remaining Amount'].astype(float)

    df['Date Invoice']              = df['Date Invoice'].apply(convert_date)
    df['Date Paid']                 = df['Date Paid'].apply(convert_date)

    df['Date Invoice']              = pd.to_datetime(df['Date Invoice'])
    df['Date Paid']                 = pd.to_datetime(df['Date Paid'])

    # Loại bỏ 6 ký tự đầu tiên trong chuỗi
    df['Client']            = df['Client'].str.slice(start = 8)
    df['Active Clientss']   = df['Active Clientss'].str.slice(start = 8)

    df['Date Paid'] = df['Date Paid'].dt.strftime('%m/%Y')
    df['Date Paid'] = pd.to_datetime(df['Date Paid'])
    df['Date Paid'] = df['Date Paid'].dt.strftime('%Y-%m-%d')
    df['Date Paid'] = pd.to_datetime(df['Date Paid'])
    
    df = df[df['Date Paid'] >= '2023-01-01 00:00:00']
    
    year_list   = (df["Date Paid"].dt.strftime('%Y').unique()).tolist()
    year_of_df  = year_list[0]

    return df, year_of_df


def format_value(value):
    values = int(value / 1000000)
    return values


def initialize_state():
    if "selected_bar" not in st.session_state:
        st.session_state["selected_bar"] = None

# Hàm chuyển ngày dạng timestamp thành dạng ngày
def convert_date(number):
    delta           = timedelta(days=number - 2)
    start_date      = date(1900, 1, 1)
    result_date     = start_date + delta
    return result_date.strftime('%m/%d/%Y')

# Tạo hàm để tô màu các hàng nếu có một ô trong cột B chứa ký tự "ABS"
def highlight_rows(row):
    if '0-' in str(row['Status']):
        return [''] * len(row)
    
    elif  '-1-Disputed' in str(row['Status']):
        return ['background-color: #e9ecef'] * len(row)
    elif  '1-' in str(row['Status']):
        return ['background-color: #fae0e4'] * len(row)
        
    elif '2-' in str(row['Status']):
        return ['background-color: #e2eafc'] * len(row)
        
    elif  '3-' in str(row['Status']):
        return ['background-color: #d8f3dc'] * len(row)
        
    elif  '4-' in str(row['Status']):
        return ['background-color: #fff6cc'] * len(row)
        
    
        
    return [''] * len(row)


def build_data_for_chart_payments(df: pd.DataFrame) -> pd.DataFrame:
    df_Payment      = df
    df_Payment      = df_Payment[df_Payment['Date Paid'] >= datetime(2023,1,1)]
    
    # Chuyển tất cả giá trị trong cột ngày "Date Paid" về cùng một tháng - sau đó đưa lại về kiểu dữ liệu DateTime để biểu đồ có thể hiểu
    df_Payment['Date Paid'] = df_Payment['Date Paid'].dt.strftime('%m/%Y')
    df_Payment["Date Paid"] = pd.to_datetime(df_Payment['Date Paid'])


    # Loại bỏ những Status không muốn lấy
    df_Payment      = df_Payment.loc[(df_Payment['Status'] != '3-Forecasted') & (df_Payment['Status'] != '-1-Disputed') & (df_Payment['Status'] != '4-Temp') ]
    
    # Group lại những giá trị có cùng Status và sau đó là cùng ngày
    df_Payment_bar                    = df_Payment.groupby(['Status', pd.Grouper(key='Date Paid')])['Remaining Amount'].sum().reset_index()
    df_Payment_bar                    = df_Payment_bar.pivot(index="Date Paid", columns="Status", values="Remaining Amount").fillna(0).reset_index()
    df_Payment_bar['Date Paid']   = df_Payment_bar['Date Paid'].dt.strftime('%b')
    df_Payment_bar                    = pd.DataFrame(df_Payment_bar)
    
    
    df_Payment_line                    = df_Payment.groupby([pd.Grouper(key='Date Paid')])['Remaining Amount'].sum().reset_index()
    df_Payment_line['Date Paid']   = df_Payment_line['Date Paid'].dt.strftime('%b')
    df_Payment_line                    = pd.DataFrame(df_Payment_line)
    
    
    df_Payment_line['Cumulative Amount']    = df_Payment_line['Remaining Amount'].cumsum()
    df_Payment_line                         = df_Payment_line.drop(['Remaining Amount'], axis=1)
 
    return df_Payment_bar, df_Payment_line


def build_chart_payments(df: pd.DataFrame) -> dict:
    df_Payment_bar, df_Payment_line = build_data_for_chart_payments(df)

    # Trích xuất thông tin từ DataFrame mới
    x_axis_data = df_Payment_bar["Date Paid"].tolist()
    legend_data = df_Payment_bar.columns[1:].tolist()
    bar_series_data = {status: df_Payment_bar[status].tolist() for status in legend_data}
    line_series_data = df_Payment_line["Cumulative Amount"].tolist()
    
    df_Payment_bar['Total'] = df_Payment_bar[['0-Fully Paid', '1-Outstanding', '2-Contracted']].sum(axis=1)
    
    max_yaxis_left  = round(format_value(df_Payment_bar['Total'].max()), -3)
    max_yaxis_right = format_value(df_Payment_line["Cumulative Amount"].max())
        
    for n in [5, 10]:
            check = max_yaxis_left * n
            if check >= max_yaxis_right:
                    max_yaxis_right = check
                    break
    
    
    for key, value in bar_series_data.items():
        for i in range(len(value)):
            value[i] = format_value(value[i]) # Rút gọn 6 chữ số đầu tiên

    for i in range(len(line_series_data)):
        line_series_data[i] = format_value(line_series_data[i]) # Rút gọn 6 chữ số đầu tiên # Rét gọn 6 chỉ sử dụng Ļ� hiển thịline_series_data:
        
    line_series_data = [line_series_data]
    
    colors = ['gray', '#ef233c', '#0353a4']  # Mảng màu sắc

    # Tạo đối tượng options cho biểu đồ
    options = {
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {
            "data": legend_data + ["Accumulated amount"],
            # "right": '5%'
            },
        "grid": {
            "left": '1%',
            "right": '0%',
            "containLabel": "true"
        },
        "xAxis": {"type": "category", "data": x_axis_data},
        "yAxis": [
            {
                "type": "value",
                "name": "Amount",
                "position": "left",
                "min": 0,
                "max": max_yaxis_left,
                "axisLabel": {
                    "formatter": '{value} M'
                }
             },
            {
                "type": "value", 
                "name": "Accumulated amount", 
                "position": "right",
                "min": 0,
                "max": max_yaxis_right,
                "axisLabel": {
                    "formatter": '{value}M'
                }
                },
        ],
        "series": [
            {
                "name": status, 
                "type": "bar", 
                "data": bar_series_data[status],
                "label": {
                    "show": True,
                    "formatter": "{c} M"
                },
                "stack": "1", 
                "yAxisIndex": 0,
                "itemStyle": {
                    "color": colors[i % len(colors)],
                    "opacity": 1  # Các cột không được hover sẽ có độ mờ là 1
                },
                "emphasis": {
                    "itemStyle": {
                        "opacity": 1  # Các cột được hover sẽ có độ mờ là 1
                    }
                }
        }
            # for status in legend_data
            for i, status in enumerate(legend_data)
           
        ] 
        + [
            {"name": "Accumulated amount", "type": "line", "data": data, "yAxisIndex": 1, "itemStyle": {
                                                                                                            "color": "black",
                                                                                                        }}
            for data in line_series_data
        ],
    }

    return options


def build_data_for_chart_Client_Active (df: pd.DataFrame) -> pd.DataFrame:
    df_Top_Client     = df
    df_Top_Client     = df_Top_Client.loc[(df_Top_Client['Status'] != '3-Forecasted') & (df_Top_Client['Status'] != '-1-Disputed') & (df_Top_Client['Status'] != '4-Temp') ]

    # Lấy ra danh sách TOP 10 Client cao nhất từ trước tới giờ
    df_Top_Client_1                 = df_Top_Client.groupby(['Status', 'Client'])['Remaining Amount'].sum().reset_index()

    df_Top_Client_1_CheckClient     = df_Top_Client_1.groupby(['Client'])['Remaining Amount'].sum().reset_index()
    top_10_clients                  = df_Top_Client_1_CheckClient.nlargest(10, 'Remaining Amount')
    client_list                     = top_10_clients['Client'].to_list()

    # Lọc ra được danh sách 10 khách hàng "NO ACTIVE"
    df_Top_Client_1 = df_Top_Client_1[df_Top_Client_1['Client'].isin(client_list)] 
    df_Top_Client_1 = df_Top_Client_1.sort_values('Status')

    # Lấy ra danh sách TOP 10 Client Active
    df_Top_Client_2                 = df_Top_Client
    df_Top_Client_2                 = df_Top_Client_2.groupby(['Status', 'Active Clientss'])['Active Remaining Amount'].sum().reset_index()

    df_Top_Client_2_CheckClient     = df_Top_Client_2.groupby(['Active Clientss'])['Active Remaining Amount'].sum().reset_index()
    top_10_clients2                 = df_Top_Client_2_CheckClient.nlargest(10, 'Active Remaining Amount')
    client_list_2                   = top_10_clients2['Active Clientss'].to_list()

    # Lọc ra được danh sách 10 khách hàng "NO ACTIVE"
    df_Top_Client_2     = df_Top_Client_2[df_Top_Client_2['Active Clientss'].isin(client_list_2)]
    df_Top_Client_2     = df_Top_Client_2[df_Top_Client_2['Active Clientss'] != ""]
    df_Top_Client_2     = df_Top_Client_2.sort_values('Status')
    
    df_Top_Client_1     = df_Top_Client_1.pivot(index="Client", columns="Status", values="Remaining Amount").fillna(0).reset_index()
    df_Top_Client_2     = df_Top_Client_2.pivot(index="Active Clientss", columns="Status", values="Active Remaining Amount").fillna(0).reset_index()
    
    check_status_list = ['0-Fully Paid', '1-Outstanding', '2-Contracted']
    existing_columns1    = df_Top_Client_1.columns.tolist()
    existing_columns2    = df_Top_Client_2.columns.tolist()
    
    for i in check_status_list:
        if i not in existing_columns1:
            df_Top_Client_1 [f"{i}"] = 0
        if i not in existing_columns2:
            df_Top_Client_2 [f"{i}"] = 0
            
    sort_column         = ['Client','0-Fully Paid', '1-Outstanding', '2-Contracted']
    sort_column2        = ['Active Clientss','0-Fully Paid', '1-Outstanding', '2-Contracted']
    df_Top_Client_1     = df_Top_Client_1.reindex(columns=sort_column)
    df_Top_Client_2     = df_Top_Client_2.reindex(columns=sort_column2)
    

    return df_Top_Client_1, df_Top_Client_2


def build_chart_Client_Active (df: pd.DataFrame, selected_option): 
    df_Top_Client_1, df_Top_Client_2 = build_data_for_chart_Client_Active(df)

    # Tính tổng và sắp xếp lại theo thứ tự tổng giảm dần
    numeric_cols                = df_Top_Client_1.select_dtypes(include='number').columns
    df_Top_Client_1["total"]    = df_Top_Client_1[numeric_cols].sum(axis=1)  # Tính tổng các cột và gán vào cột "total"
    df_Top_Client_1             = df_Top_Client_1.sort_values(by="total", ascending=True)
    df_Top_Client_1             = df_Top_Client_1.drop(["total"], axis = 1)
    
    # Tính tổng và sắp xếp lại theo thứ tự tổng giảm dần
    numeric_cols2               = df_Top_Client_2.select_dtypes(include='number').columns
    df_Top_Client_2["total"]    = df_Top_Client_2[numeric_cols2].sum(axis=1)  # Tính tổng các cột và gán vào cột "total"
    df_Top_Client_2             = df_Top_Client_2.sort_values(by="total", ascending=True)
    df_Top_Client_2             = df_Top_Client_2.drop(["total"], axis = 1)

    if selected_option: # Active
        df_ACTIVE_or_NoACTIVE   = df_Top_Client_2
        x_axis_data             = df_ACTIVE_or_NoACTIVE["Active Clientss"].tolist()
        legend_data             = df_ACTIVE_or_NoACTIVE.columns[1:].tolist()
        bar_series_data         = {status: df_ACTIVE_or_NoACTIVE[status].tolist() for status in legend_data}
        for key, value in bar_series_data.items():
            for i in range(len(value)):
                value[i] = format_value(value[i]) # Rút gọn 6 chữ số đầu tiên
        TITLE                   = 'TOP 10 clients - ACTIVE ✅'
        
    else: # No Active
        df_ACTIVE_or_NoACTIVE   = df_Top_Client_1
        x_axis_data             = df_ACTIVE_or_NoACTIVE["Client"].tolist()
        legend_data             = df_ACTIVE_or_NoACTIVE.columns[1:].tolist()
        bar_series_data         = {status: df_ACTIVE_or_NoACTIVE[status].tolist() for status in legend_data}
        for key, value in bar_series_data.items():
            for i in range(len(value)):
                value[i] = format_value(value[i]) # Rút gọn 6 chữ số đầu tiên
        TITLE                   = 'TOP 10 clients'

    colors = ['gray', '#ef233c', '#0353a4']  # List màu sắc

    # Tạo đối tượng options cho biểu đồ
    options_active = {
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {"data": legend_data},
        "grid": {
            "top": '10%',
            "left": '3%',
            "right": '10%',
            "bottom": '3%',
            "containLabel": True
        },
        "yAxis": {"type": "category", "data": x_axis_data},
        "xAxis": [
            {
                "type": "value",
                "name": "Amount",
                "position": "bottom",
                
                "axisLabel": {
                    "formatter": '{value} M'
                }
            }
        ],
        "series": [
            {
                "name": status,
                "type": "bar",
                "data": bar_series_data[status],
                "stack": "1",
                "xAxisIndex": 0,
                "label": {
                    "show": True,
                    "formatter": "{c} M"
                },
                "itemStyle": {
                    "color": colors[i % len(colors)],
                    "opacity": 1,
                },
                "emphasis": {
                    "itemStyle": {
                        "opacity": 1,
                    }
                }
            }
            # for status in legend_data
            for i, status in enumerate(legend_data)
        ]
    }
    return options_active


def load_data_client_list(df: pd.DataFrame) -> pd.DataFrame:
    df_List_Client          = df
    df_List_Client          = df_List_Client[df_List_Client['Date Paid'] >= datetime(2023,1,1)]
    df_List_Client          = df_List_Client[['Status', 'Client', 'Date Paid', 'Days Late', 'Remaining Amount']]
    df_List_Client          = df_List_Client.loc[(df_List_Client['Status'] != '3-Forecasted') & (df_List_Client['Status'] != '-1-Disputed') & (df_List_Client['Status'] != '4-Temp') & (df_List_Client['Status'] != '0-Fully Paid')]
    df_List_Client2         = df_List_Client.groupby(['Status', 'Client'])['Days Late'].mean().reset_index()
    df_List_Client1         = df_List_Client.groupby(['Status', 'Client'])['Remaining Amount'].sum().reset_index()
    group_df_List_Client    = df_List_Client1.join(df_List_Client2.set_index(['Status', 'Client']), on=(['Status', 'Client']))

    group_df_List_Client['Days Late']           = group_df_List_Client['Days Late'].astype(int)
    group_df_List_Client['Remaining Amount']    = group_df_List_Client['Remaining Amount'] .apply(lambda x: '{:,.0f}  VND'.format(x))


    # Áp dụng hàm tô màu vào DataFrame
    group_df_List_Client = group_df_List_Client.style.apply(highlight_rows, axis=1)
    
    return group_df_List_Client


def render_preview_ui(df: pd.DataFrame):
    df                  = df[["Status", "Client", "Date Invoice", "Date Paid", "Remaining Amount"]]
    df['Date Paid']     = df['Date Paid'].dt.strftime('%Y %b %d')
    df['Date Invoice']  = df['Date Invoice'].dt.strftime('%Y %b %d')
    
    # Áp dụng hàm tô màu vào DataFrame
    df                  = df.style.apply(highlight_rows, axis=1)
    
    with st.expander('Preview all data payments'):
        st.dataframe(df, use_container_width=True)


def query_data(df: pd.DataFrame) -> pd.DataFrame:
    df ["selected"] = False

    if st.session_state["selected_bar"] == None:
        df = df
        return df
    else:
        df.loc[df['Date Paid'] == st.session_state["selected_bar"], "selected"] = True
        df = df.loc[df['selected'] == True]
        return df
    


def update_state(mouseover_label: str, year: str):
    rerun = False
    date_format = "%d/%b/%Y"
    dates = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep","Oct", "Nov", "Dec"]
    
    if mouseover_label in dates:
        date_string = f"01/{mouseover_label}/{year}"
        date_query = datetime.strptime(date_string, date_format)
        if date_query != st.session_state["selected_bar"]:
            st.session_state["selected_bar"] = date_query
            rerun = True

    else:
        if st.session_state["selected_bar"] != None:
            st.session_state["selected_bar"] = None
            st.experimental_rerun()
    
    if rerun:
        st.experimental_rerun()


def render_plotly_ui(df: pd.DataFrame,  selected_option):
    options_active          = build_chart_Client_Active(df, selected_option)
    df_list_clients         = load_data_client_list(df)    
    
    col1, col2 = st.columns(2)
    with col1:
        st_echarts(options_active, height="30rem")
        
    with col2:
        st.dataframe(df_list_clients, use_container_width=True)


def main():
    initialize_state()
    df, year_of_df      = load_data()
    option_payments     = build_chart_payments(df)
    transform_df        = query_data(df)

    btn_refresh         = st.button("Refresh")
    
    if btn_refresh:
    #     #Resfesh lại dữ liệu ban đầu
    #     # st.session_state.checkbox_value = False
    #     if st.session_state["selected_bar"] != None:
    #         st.session_state["selected_bar"] = None

        st.experimental_rerun()
        
    mouseover_label = st_echarts(option_payments,
                             events={
                                #  "MOUSEOUT": "function(params) {return params.value}",
                                 "CLICK": "function(params) {return params.name}"
                             },
                             height="30rem")
    
    selected_option         = (st.checkbox("Clients no ACTIVE") == False)
    
    update_state(mouseover_label, year_of_df)
    render_plotly_ui(transform_df, selected_option)
    render_preview_ui(df)

if __name__ == "__main__":
    
    st.title("TBF Payments")
    main()



# RUN STREAMLIT FILE
# streamlit run "D:\Documents\Ty\THE BIM FACTORY 4.7.2022\Streamlit_app\TBF_Payments\STL_TBF_Payment.py"

# ---------CREATE REQUIREMENTS FILE
# pip install pipreqs
# pipreqs 'path' --encoding=utf-8 --force ( --force (Để ghi đè lên tệp đã tồn tại) )