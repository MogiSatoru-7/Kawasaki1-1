import streamlit as st
import requests
import os
import re
import pandas as pd
from datetime import datetime
import requests_cache
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Dictionary mapping weather codes to descriptions
weather_descriptions = {
    0: "晴れ", 1: "晴れ", 2: "曇り", 3: "小雨",
    4: "霧", 5: "小雨", 6: "雨", 7: "雪",
    8: "雨", 9: "雷雨"
}

# Initialize the DataFrame in session state if not already present
if 'df_records' not in st.session_state:
    st.session_state.df_records = pd.DataFrame(
        columns=['date', 'day_of_week', 'weather_description', 'temperature_max', 'item_name', 'price_per_item', 'volume'])

def create_session():
    cache = requests_cache.CachedSession('.cache', expire_after=300)
    retries = Retry(total=5, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    cache.mount('http://', adapter)
    cache.mount('https://', adapter)
    return cache

def fetch_weather(date):
    session = create_session()
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 35.5206, "longitude": 139.7172, "daily": ["weather_code", "temperature_2m_max"],
        "timezone": "auto", "start": date.strftime('%Y-%m-%d'), "end": date.strftime('%Y-%m-%d')
    }
    response = session.get(url, params=params)
    data = response.json()

    if 'daily' in data:
        daily_data = data['daily']
        date = pd.Timestamp(date.strftime('%Y-%m-%d'))
        weather_code = daily_data['weather_code'][0]
        temperature_max = daily_data['temperature_2m_max'][0]
        weather_category = weather_code // 10
        weather_description = weather_descriptions.get(weather_category, "Unknown")
        daily_dataframe = pd.DataFrame([{
            "date": date, "day_of_week": date.day_name(), "weather_code": weather_code,
            "weather_category": weather_category, "weather_description": weather_description,
            "temperature_max": temperature_max
        }])
        st.session_state.weather_data = daily_dataframe
        return daily_dataframe
    else:
        st.error("No weather data available for the selected date.")
        return pd.DataFrame()

REQUEST_URL = 'https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706'
APP_ID = os.getenv('RAKUTEN_APP_ID')  # Application ID from environment variable

def fetch_top_item(keyword, ngkeyword='ふるさと エントリー クーポン 倍'):
    params = {
        'applicationId': APP_ID, 'keyword': keyword, 'format': 'json', 'NGKeyword': ngkeyword
    }
    response = requests.get(REQUEST_URL, params=params)
    if response.status_code == 200:
        items = response.json().get('Items', [])
        if items:
            item_info = items[0]['Item']
            st.session_state.item_info = item_info  # Save the item info in the session state
            return item_info
    return None

def display_item_info(item):
    if item:
        item_name = item['itemName']
        item_price = item['itemPrice']
        quantity_pattern = re.compile(r'(\d+)\s*本')
        quantity_match = quantity_pattern.search(item_name)
        volume_pattern = re.compile(r'(\d+)\s*ml')
        volume_match = volume_pattern.search(item_name)
        info_texts = []
        if quantity_match:
            quantity = int(quantity_match.group(1))
            price_per_item = item_price / quantity
            info_texts.append(f'数量: {quantity}本, 1本あたりの価格: {price_per_item:.2f}円')
        if volume_match:
            volume = int(volume_match.group(1))
            info_texts.append(f'内容量: {volume}ml')
        info_text = ', '.join(info_texts)
        st.write(f'商品名: {item_name}, 価格: {item_price}円, {info_text}')

def add_to_dataframe(selected_date):
    if 'weather_data' in st.session_state and 'item_info' in st.session_state:
        weather_info = st.session_state.weather_data.iloc[0]
        item_info = st.session_state.item_info

        # 数量と容量を商品名から抽出
        quantity_match = re.search(r'(\d+)\s*本', item_info['itemName'])
        volume_match = re.search(r'(\d+)\s*ml', item_info['itemName'])
        quantity = int(quantity_match.group(1)) if quantity_match else 1
        volume = int(volume_match.group(1)) if volume_match else 0

        # 新しいレコードを作成
        new_record = {
            'date': selected_date.strftime('%Y-%m-%d'),
            'day_of_week': selected_date.strftime('%A'),
            'weather_description': weather_info['weather_description'],
            'temperature_max': weather_info['temperature_max'],
            'item_name': item_info['itemName'],
            'price_per_item': item_info['itemPrice'] / quantity,
            'volume': volume
        }

        # データフレームに新しいレコードを追加
        if 'df_records' not in st.session_state or st.session_state.df_records.empty:
            st.session_state.df_records = pd.DataFrame([new_record])
        else:
            st.session_state.df_records = pd.concat([st.session_state.df_records, pd.DataFrame([new_record])], ignore_index=True)
        
        # データフレームを表示
        st.dataframe(st.session_state.df_records)
    else:
        st.error("No weather or item data available to add.")

def delete_record(index):
    if 'df_records' in st.session_state and not st.session_state.df_records.empty:
        st.session_state.df_records = st.session_state.df_records.drop(index).reset_index(drop=True)
        display_data_with_delete_option()  # 更新されたデータフレームを再表示

def display_data_with_delete_option():
    if 'df_records' in st.session_state and not st.session_state.df_records.empty:
        for i, record in st.session_state.df_records.iterrows():
            cols = st.columns([3, 1, 1, 2, 1, 1, 1, 1, 1])
            cols[0].write(record['date'])
            cols[1].write(record['day_of_week'])
            cols[2].write(record['weather_description'])
            cols[3].write(record['temperature_max'])
            cols[4].write(record['item_name'])
            cols[5].write(record['price_per_item'])
            cols[6].write(record['volume'])
            if cols[7].button(f"Delete Record {i}"):
                delete_record(i)
            cols[8].write("")



def display_beers_consumed(df):
    # 現在の月を取得
    current_month = datetime.now().strftime('%Y-%m')
    df['date'] = pd.to_datetime(df['date'])
    # 現在の月に該当するビールの消費回数を計算
    monthly_beers = df[df['date'].dt.strftime('%Y-%m') == current_month]
    beer_sessions = len(monthly_beers)
    # 今月飲んだビールの本数とビールのアイコンを表示
    st.write(f"今月飲んだビールの本数: {beer_sessions}", f"🍺" * beer_sessions)

def display_budget_and_beers(df):
    budget = 5000  # 月の予算設定
    current_month = datetime.now().strftime('%Y-%m')
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')
    # 現在の月のビールにかかった費用を計算
    monthly_expenses = df[df['date'] == current_month]['price_per_item'].sum() if 'price_per_item' in df.columns else 0
    remaining_budget = budget - monthly_expenses  # 残りの予算を計算

    # 残りの予算で買えるビールの本数を計算
    beers_third = remaining_budget // 170
    beers_premium = remaining_budget // 240
    beers_craft = remaining_budget // 500

    # 今月のビールに関する金額と残りの予算、そして買えるビールの本数を表示
    st.write(f"今月のビール金額: ¥{int(monthly_expenses)}、", f"今月の残り予算: ¥{int(remaining_budget)}")
    st.write(f"第三のビール: 今月あと{int(beers_third)}本", f"🍺" * int(beers_third))
    st.write(f"プレミアムビール: 今月あと{int(beers_premium)}本", f"🍺" * int(beers_premium))
    st.write(f"クラフトビール: 今月あと{int(beers_craft)}本", f"🍺" * int(beers_craft))

def main():
    st.title('毎日ビールを飲みたい🍻')
    uploaded_file = st.file_uploader("アップロード")
    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
        st.session_state.df_records = data
        st.write('Data successfully loaded!')
        st.dataframe(st.session_state.df_records)

    base_keyword = 'ビール'
    additional_keyword = st.text_input("ビールの銘柄情報を入力してください")
    selected_date = st.date_input("日付を選択してください", datetime.today())

    if st.button('ビールを検索'):
        keyword = f'{base_keyword} {additional_keyword}'
        top_item = fetch_top_item(keyword)
        if top_item:
            display_item_info(top_item)

    if st.button('天気を取得'):
        df_weather = fetch_weather(selected_date)
        if not df_weather.empty:
            st.table(df_weather)
            st.session_state.weather_data = df_weather

    if st.button('飲んだ！'):
        if 'weather_data' in st.session_state and 'item_info' in st.session_state:
            add_to_dataframe(selected_date)
        else:
            st.error('商品情報と天気情報の両方が利用可能であることを確認してください。')

    if st.session_state.df_records is not None and not st.session_state.df_records.empty:
        csv = st.session_state.df_records.to_csv(index=False).encode('utf-8')
        st.download_button("データをCSVでダウンロード", csv, 'data.csv', 'text/csv')

    display_data_with_delete_option()

    # Display beer consumption and budget details
    if 'df_records' in st.session_state:
        display_beers_consumed(st.session_state.df_records)
        display_budget_and_beers(st.session_state.df_records)

if __name__ == "__main__":
    main()
