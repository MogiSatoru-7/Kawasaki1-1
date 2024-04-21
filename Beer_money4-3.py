import streamlit as st
import requests
import os
import re
import pandas as pd
from datetime import datetime, timedelta
import requests_cache
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Dictionary mapping weather codes to descriptions
weather_descriptions = {
    0: "晴れ", 1: "晴れ", 2: "曇り", 3: "小雨",
    4: "霧", 5: "小雨", 6: "雨", 7: "雪",
    8: "雨", 9: "雷雨"
}

# Initialize the DataFrame in session state if not already present
if 'df_records' not in st.session_state:
    st.session_state.df_records = pd.DataFrame(
        columns=['date', 'day_of_week', 'weather_description', 'temperature_max', 'item_name', 'price_per_item', 'volume', 'drinking_day', 'number'])

def create_session():
    cache = requests_cache.CachedSession('.cache', expire_after=300)
    retries = Retry(total=5, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    cache.mount('http://', adapter)
    cache.mount('https://', adapter)
    return cache

def fetch_weather_week(selected_date):
    session = create_session()
    end_date = selected_date + timedelta(days=6)
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 35.5206, "longitude": 139.7172, "daily": ["weather_code", "temperature_2m_max"],
        "timezone": "auto", "start": selected_date.strftime('%Y-%m-%d'), "end": end_date.strftime('%Y-%m-%d')
    }
    response = session.get(url, params=params)
    data = response.json()

    # 天気情報をデータフレームに表示
    weather_data = []
    if 'daily' in data:
        daily_data = data['daily']

        for i in range(len(daily_data['weather_code'])):
            date = (selected_date + timedelta(days=i)).strftime('%Y-%m-%d')
            weather_code = daily_data['weather_code'][i]
            temperature_max = daily_data['temperature_2m_max'][i]
            weather_category = weather_code // 10
            weather_description = weather_descriptions.get(weather_category, "Unknown")
            weather_data.append({
                "date": date, "day_of_week": pd.Timestamp(date).strftime('%A'), "weather_description": weather_description,
                "temperature_max": temperature_max
    })
        return pd.DataFrame(weather_data)
    else:
        st.error("No weather data available for the selected week.")
        return pd.DataFrame()

REQUEST_URL = 'https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706'
APP_ID = "1099668680676374397"  # Rakuten APP ID

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
        existing_record = st.session_state.df_records[
            (st.session_state.df_records['date'] == selected_date.strftime('%Y-%m-%d')) &
            (st.session_state.df_records['item_name'] == st.session_state.item_info['itemName'])
        ]
        weather_info = st.session_state.weather_data.iloc[0]
        item_info = st.session_state.item_info

        quantity_match = re.search(r'(\d+)\s*本', item_info['itemName'])
        volume_match = re.search(r'(\d+)\s*ml', item_info['itemName'])
        quantity = int(quantity_match.group(1)) if quantity_match else 1
        volume = int(volume_match.group(1)) if volume_match else 0

        new_record = {
            'date': selected_date.strftime('%Y-%m-%d'),  # ここを修正する
            'day_of_week': selected_date.strftime('%A'),
            'weather_description': weather_info['weather_description'],
            'temperature_max': weather_info['temperature_max'],
            'item_name': item_info['itemName'],
            'price_per_item': item_info['itemPrice'] / quantity,
            'volume': volume,
            'drinking_day': '',  # 新しい "drinking day" カラムを追加
            'number': ''  # 新しい "number" カラムを追加
        }

        if 'df_records' not in st.session_state or st.session_state.df_records.empty:
            st.session_state.df_records = pd.DataFrame([new_record])
        else:
            st.session_state.df_records = pd.concat([st.session_state.df_records, pd.DataFrame([new_record])], ignore_index=True)

        st.dataframe(st.session_state.df_records)
    else:
        st.error("No weather or item data available to add.")

def delete_record(index):
    if 'df_records' in st.session_state and not st.session_state.df_records.empty:
        st.session_state.df_records = st.session_state.df_records.drop(index).reset_index(drop=True)
        display_data_with_delete_option()

def display_data_with_delete_option():
    if 'df_records' in st.session_state and not st.session_state.df_records.empty:
        for i, record in st.session_state.df_records.iterrows():
            cols = st.columns([3, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1])  # 列の数を増やす
            cols[0].write(record['date'])
            cols[1].write(record['day_of_week'])
            cols[2].write(record['weather_description'])
            cols[3].write(record['temperature_max'])
            cols[4].write(record['item_name'])
            cols[5].write(record['price_per_item'])
            cols[6].write(record['volume'])
            cols[7].write(record['drinking_day'])  # "drinking day" カラムを表示
            cols[8].write(record['number'])  # "number" カラムを表示
            if cols[9].button(f"Delete Record {i}"):
                delete_record(i)
            cols[10].write("")#追加

def display_beers_consumed(df, monthly=True):
    current_date = datetime.now()
    if monthly:
        current_period = current_date.strftime('%Y-%m')
        period_label = "今月"
    else:
        current_period = f"{current_date.strftime('%Y-%m-%d')} ～ {(current_date + timedelta(days=(6 - current_date.weekday()))).strftime('%Y-%m-%d')}"
        period_label = "今週"

    df['date'] = pd.to_datetime(df['date'])
    beers_period = df[df['date'].dt.strftime('%Y-%m') == current_period] if monthly else df[(df['date'] >= current_date.strftime('%Y-%m-%d')) & (df['date'] <= (current_date + timedelta(days=(6 - current_date.weekday()))).strftime('%Y-%m-%d'))]
    beer_sessions = len(beers_period)
    st.write(f"{period_label}飲んだビールの本数: {beer_sessions}", f"🍺" * beer_sessions)

def display_budget_and_beers(df, monthly=True, period_label=None):
    current_date = datetime.now()
    if monthly:
        remaining_budget = 5000
        if period_label is None:
            period_label = "今月"
    else:
        remaining_budget = 1250
        if period_label is None:
            period_label = "今週"

    current_period = current_date.strftime('%Y-%m') if monthly else f"{current_date.strftime('%Y-%m-%d')} ～ {(current_date + timedelta(days=(6 - current_date.weekday()))).strftime('%Y-%m-%d')}"
    period_beers = df[df['date'].dt.strftime('%Y-%m') == current_period] if monthly else df[(df['date'] >= current_date.strftime('%Y-%m-%d')) & (df['date'] <= (current_date + timedelta(days=(6 - current_date.weekday()))).strftime('%Y-%m-%d'))]
    period_expenses = period_beers['price_per_item'].sum() if 'price_per_item' in period_beers.columns else 0

    remaining_budget -= period_expenses

    if remaining_budget >= 0:
        beers_third = remaining_budget // 170
        beers_premium = remaining_budget // 240
        beers_craft = remaining_budget // 500

        st.write(f"{period_label}のビール金額: ¥{int(period_expenses)}、", f"{period_label}の残り予算: ¥{int(remaining_budget)}")
        st.write(f"第三のビール: {period_label}あと{int(beers_third)}本", "🍺" * int(beers_third))
        st.write(f"プレミアムビール: {period_label}あと{int(beers_premium)}本", "🍺" * int(beers_premium))
        st.write(f"クラフトビール: {period_label}あと{int(beers_craft)}本", "🍺" * int(beers_craft))
    else:
        st.write(f"{period_label}の残りの予算がありません。")

def determine_drinking_days(df_weather):
    # 気温が最も高い日と最も低い日を見つける
    max_temp_day = df_weather[df_weather['temperature_max'] == df_weather['temperature_max'].max()]
    min_temp_day = df_weather[df_weather['temperature_max'] == df_weather['temperature_max'].min()]

    # 気温が最も高い日と最も低い日に「◎」「△」を追加し、その他の日に「〇」を追加
    for index, row in df_weather.iterrows():
        if row['date'] in max_temp_day['date'].values:
            df_weather.at[index, 'drinking_day'] = '◎'
            df_weather.at[index, 'number'] = 2  # 2本
        elif row['date'] in min_temp_day['date'].values:
            df_weather.at[index, 'drinking_day'] = '△'
            df_weather.at[index, 'number'] = 0  # 1本 or 0
        else:
            df_weather.at[index, 'drinking_day'] = '〇'
            df_weather.at[index, 'number'] = 1  # 1本

    return df_weather

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

    if st.button('週の天気を取得'):
        df_weather = fetch_weather_week(selected_date)
        if not df_weather.empty:
            df_weather = determine_drinking_days(df_weather)
            st.table(df_weather)
            st.session_state.weather_data = df_weather
            st.write("ビール日和◎🍺🍺")
        # 合計数を計算して表示
        st.write(f"今週のビール本数予測: {df_weather['number'].sum()}")

    if st.button('飲んだ！'):
        if 'weather_data' in st.session_state and 'item_info' in st.session_state:
            add_to_dataframe(selected_date)
        else:
            st.error('商品情報と天気情報の両方が利用可能であることを確認してください。')

    if st.session_state.df_records is not None and not st.session_state.df_records.empty:
        csv = st.session_state.df_records.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("データをCSVでダウンロード", csv, 'data.csv', 'text/csv')


    display_data_with_delete_option()

    # Display beer consumption and budget details for both monthly and weekly periods
    if 'df_records' in st.session_state:
        display_beers_consumed(st.session_state.df_records, monthly=True)
        display_budget_and_beers(st.session_state.df_records, monthly=True, period_label="今月")
        display_beers_consumed(st.session_state.df_records, monthly=False)
        display_budget_and_beers(st.session_state.df_records, monthly=False, period_label="今週")
        
if __name__ == "__main__":
    main()