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
    0: "晴れ",
    1: "晴れ",
    2: "曇り",
    3: "小雨",
    4: "霧",
    5: "小雨",
    6: "雨",
    7: "雪",
    8: "雨",
    9: "雷雨"
}

# セッションステートでデータフレームの初期化
if 'df_records' not in st.session_state:
    st.session_state.df_records = pd.DataFrame(columns=['date', 'day_of_week', 'weather_description', 'temperature_max', 'item_name', 'price_per_item', 'volume'])

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
        "weather_category": weather_category,
        "weather_description": weather_descriptions_list,
        "temperature_2m_max": daily_data['temperature_2m_max']
    })

    st.session_state.weather_data = daily_dataframe
    return daily_dataframe

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
            st.session_state.item_info = items[0]['Item']
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

def add_to_dataframe(selected_date):
    if 'weather_data' in st.session_state and 'item_info' in st.session_state:
        # 正しい日付のデータを選択
        weather_info = st.session_state.weather_data[st.session_state.weather_data['date'] == pd.Timestamp(selected_date)].iloc[0]
        item_info = st.session_state.item_info

        # 商品情報の解析
        item_name = item_info['itemName']
        item_price = item_info['itemPrice']
        quantity_pattern = re.compile(r'(\d+)\s*本')
        quantity_match = quantity_pattern.search(item_name)
        volume_pattern = re.compile(r'(\d+)\s*ml')
        volume_match = volume_pattern.search(item_name)
        price_per_item = (item_price / int(quantity_match.group(1))) if quantity_match else None
        volume = int(volume_match.group(1)) if volume_match else None

        new_record = pd.DataFrame([{
            'date': weather_info['date'],
            'day_of_week': weather_info['day_of_week'],
             "weather_category": weather_info['weather_category'],
            'weather_description': weather_info['weather_description'],
            'temperature_max': weather_info['temperature_2m_max'],
            'item_name': item_name,
            'price_per_item': price_per_item,
            'volume': volume
        }])

        st.session_state.df_records = pd.concat([st.session_state.df_records, new_record], ignore_index=True)

## 今月飲んだビールの回数を計算して表示する関数
def display_beers_consumed(df):
    current_month = datetime.now().strftime('%Y-%m')
    df['date'] = pd.to_datetime(df['date'])
    monthly_beers = df[df['date'].dt.strftime('%Y-%m') == current_month]
    beer_sessions = len(monthly_beers)
    st.write(f"今月飲んだビールの本数: {beer_sessions}", f"🍺" * beer_sessions)


# 予算計算と何本飲めるかを表示する関数
def display_budget_and_beers(df):
    budget = 5000
    current_month = datetime.now().strftime('%Y-%m')
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')
    # 月ごとにフィルタリング
    monthly_expenses = df[df['date'] == current_month]['price_per_item'].sum() if 'price_per_item' in df.columns else 0
    remaining_budget = budget - monthly_expenses

    beers_third = remaining_budget // 170
    beers_premium = remaining_budget // 240
    beers_craft = remaining_budget // 500

    st.write(f"今月のビール金額: ¥{int(monthly_expenses)}、", f"今月の残り予算: ¥{int(remaining_budget)}")
    st.write(f"第三のビール: 今月あと{int(beers_third)}本", f"🍺" * int(beers_third))
    st.write(f"プレミアムビール: 今月あと{int(beers_premium)}本", f"🍺" * int(beers_premium))
    st.write(f"クラフトビール: 今月あと{int(beers_craft)}本", f"🍺" * int(beers_craft))


def display_beers_consumed(df):
    try:
        current_month = datetime.now().strftime('%Y-%m')
        df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')
        monthly_beers = df[df['date'].dt.strftime('%Y-%m') == current_month]
        beer_sessions = len(monthly_beers)
        return beer_sessions  # 常に整数を返す
    except Exception as e:
        st.error(f"ビールの消費数の計算中にエラーが発生しました: {e}")
        return 0  # エラーが発生した場合も0を返す


def main():
    # カラムを作成
    col1, col2 = st.columns([3, 1])  # 3:1の比率でカラムを分けます。

    # タイトルを左側のカラムに表示
    with col1:
        st.title('毎日ビールを飲みたい🍻')

    # ビールの消費数に基づいて画像を選択
    beer_count = display_beers_consumed(st.session_state.df_records)
    
    if beer_count <= 20:
        image_path = '健康な肝臓.png'
        image_caption = "肝臓が健康"
    else:
        image_path = '不健康な肝臓.png'
        image_caption = "肝臓が弱っている"

    # 画像を右側のカラムに表示
    with col2:
        st.image(image_path, width=150, caption=image_caption)

    # CSVファイルをアップロードして読み込む
    uploaded_file = st.file_uploader("アップロード")
    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
        st.session_state.df_records = data
        st.write('Data successfully loaded!')
        st.dataframe(st.session_state.df_records)

    base_keyword = 'ビール'
    additional_keyword = st.text_input("ビールの銘柄情報を入力してください")
    
    # 日付選択は常に表示
    selected_date = st.date_input("日付を選択してください", datetime.today())
    
    if st.button('ビールを検索'):
        # 組み合わせたキーワード
        keyword = f'{base_keyword} {additional_keyword}'
        top_item = fetch_top_item(keyword)
        display_item_info(top_item)
        st.session_state.selected_item = top_item  # 商品情報をセッションステートに保存
    if st.button('天気を取得'):
        df_weather = fetch_weather(selected_date)
        selected_weather = df_weather[df_weather['date'] == pd.Timestamp(selected_date)]
        if not selected_weather.empty:
            st.table(selected_weather)
            st.session_state.selected_weather = selected_weather  # 天気情報をセッションステートに保存
        else:
            st.error('選択された日付の天気データはありません。')

    if st.button('飲んだ！'):
        if hasattr(st.session_state, 'selected_weather') and hasattr(st.session_state, 'selected_item'):
            # 選択された天気と商品情報を取得
            selected_weather = st.session_state.selected_weather.iloc[0]
            selected_item = st.session_state.selected_item

            # 商品名と価格を解析
            item_name = selected_item['itemName']
            item_price = selected_item['itemPrice']
            quantity_pattern = re.compile(r'(\d+)\s*本')
            quantity_match = quantity_pattern.search(item_name)
            volume_pattern = re.compile(r'(\d+)\s*ml')
            volume_match = volume_pattern.search(item_name)

            quantity = int(quantity_match.group(1)) if quantity_match else None
            price_per_item = item_price / quantity if quantity else None
            volume = int(volume_match.group(1)) if volume_match else None

            # 新しいレコードを作成
            new_record = {
                'date': selected_weather['date'],
                'day_of_week': selected_weather['day_of_week'],
                'weather_category': selected_weather['weather_category'],
                'weather_description': selected_weather['weather_description'],
                'temperature_max': selected_weather['temperature_2m_max'],
                'item_name': item_name,
                'price_per_item': price_per_item,
                'volume': volume
            }

            # データフレームに新しいレコードを追加
            new_record_df = pd.DataFrame([new_record])
            st.session_state.df_records = pd.concat([st.session_state.df_records, new_record_df], ignore_index=True)

            st.write('データを記録しました！')
            st.dataframe(st.session_state.df_records)
        else:
            st.error('商品情報または天気情報がまだ取得されていません。')

    # ダウンロードボタン
    if st.session_state.df_records is not None and not st.session_state.df_records.empty:
        csv = st.session_state.df_records.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name='data.csv',
            mime='text/csv',
        )
    else:
        st.write("No data to download")

       # データフレームの読み込み
    if 'df_records' in st.session_state:
        display_beers_consumed(st.session_state.df_records)
        display_budget_and_beers(st.session_state.df_records)
    else:
        st.write("データがありません。")


if __name__ == "__main__":
    main()
