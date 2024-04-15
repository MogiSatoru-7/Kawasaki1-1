import streamlit as st
import requests
import os
import re
import pandas as pd
from datetime import datetime
import requests_cache
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# 天気コードに対応する天気の説明を返す辞書
weather_descriptions = {
    0: "快晴",
    1: "晴れ",
    2: "曇り",
    3: "小雨",
    4: "雨",
    5: "大雨",
    6: "雪",
    7: "大雪",
    8: "みぞれ",
    9: "雷雨"
}

def create_session():
    cache = requests_cache.CachedSession('.cache', expire_after=300)  # キャッシュの有効期限を５分に設定
    retries = Retry(total=5, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    cache.mount('http://', adapter)
    cache.mount('https://', adapter)
    return cache

def fetch_weather(date):
    session = create_session()
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 35.5206,  # 神奈川県川崎市の緯度
        "longitude": 139.7172,  # 神奈川県川崎市の経度
        "daily": ["weather_code", "temperature_2m_max"],
        "timezone": "auto",
        "start": date.strftime('%Y-%m-%d'),  # APIに渡す日付フォーマット
        "end": date.strftime('%Y-%m-%d'),
        "past_days": 7,
        "forecast_days": 7
    }
    response = session.get(url, params=params)
    data = response.json()

    daily_data = data['daily']
    dates = pd.date_range(start=daily_data['time'][0], periods=len(daily_data['weather_code']), freq='D')
    weather_codes = daily_data['weather_code']
    weather_category = [code // 10 for code in weather_codes]  
    weather_descriptions_list = [weather_descriptions.get(code, "Unknown") for code in weather_category]

    daily_dataframe = pd.DataFrame({
        "date": dates,
        "day_of_week": dates.day_name(),
        "weather_code": weather_codes,
        "weather_description": weather_descriptions_list,
        "temperature_2m_max": daily_data['temperature_2m_max']
    })

    return daily_dataframe

# 楽天APIのエンドポイントとアプリケーションID
REQUEST_URL = 'https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706'
APP_ID = os.getenv('RAKUTEN_APP_ID')  # 環境変数からアプリケーションIDを取得

def fetch_top_item(keyword, ngkeyword='ふるさと エントリー クーポン 倍'):
    # APIリクエストのパラメータ
    params = {
        'applicationId': APP_ID,
        'keyword': keyword,
        'format': 'json',
        'NGKeyword': ngkeyword
    }
    
    # APIリクエストを送信
    response = requests.get(REQUEST_URL, params=params)
    
    if response.status_code == 200:
        items = response.json().get('Items', [])
        if items:
            return items[0]['Item']
    return None

def display_item_info(item):
    if item:
        item_name = item['itemName']
        item_price = item['itemPrice']

        # 商品名から「本」の前にある数字を抽出
        quantity_pattern = re.compile(r'(\d+)\s*本')
        quantity_match = quantity_pattern.search(item_name)

        # 商品名から「ml」の前にある数字を抽出
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
        if info_text:
            st.write(f'商品名: {item_name}, 価格: {item_price}円, {info_text}')
        else:
            st.write(f'商品名: {item_name}, 価格: {item_price}円')
    else:
        st.error('商品が見つかりませんでした。')

def main():
    st.title('楽天商品検索')

    base_keyword = 'ビール'
    additional_keyword = st.text_input("銘柄情報を入力してください")
    
    if st.button('商品を検索'):
        # 組み合わせたキーワード
        keyword = f'{base_keyword} {additional_keyword}'
        top_item = fetch_top_item(keyword)
        display_item_info(top_item)

    # 天気予報表示
    st.title('川崎市の天気予報')
    selected_date = st.date_input("日付を選択してください", datetime.today())
    
    if st.button('天気を取得'):
        df_weather = fetch_weather(selected_date)
        selected_weather = df_weather[df_weather['date'] == pd.Timestamp(selected_date)]
        if not selected_weather.empty:
            st.table(selected_weather)
        else:
            st.error('選択された日付の天気データはありません。')

if __name__ == "__main__":
    main()
