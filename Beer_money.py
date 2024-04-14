import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ビール銘柄と価格の辞書
beer_brands = {
    "スーパードライ": 200, "一番搾り": 200, "黒ラベル": 200, "プレミアムモルツ": 210,
    "金麦": 170, "よなよなエール": 210, "豊潤": 280, "オリオン": 200, "サントリー生ビール": 180,
    "マルエフ": 190, "クラシックラガー": 180, "本麒麟": 170, "淡麗": 170
}


# Streamlitアプリの基本設定
st.title("毎日ビールが飲みたい")

# ファイルアップローダーの追加
uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type=['csv'])


# 日付の手動選択
selected_date = st.date_input("日付を選んでください", datetime.now())

# ボタンを押した時に天気を取得
if st.button('天気と気温を取得'):
    # 「つくみじま」の天気予報APIのURL（神奈川県川崎市）
    url = "https://weather.tsukumijima.net/api/forecast/city/140010"

    # APIリクエストを送信
    response = requests.get(url)
    data = response.json()

    # 天気情報の取得
    today_weather = data['forecasts'][0]['detail']['weather']['T18_24']

    # 気温情報の取得（最高・最低気温）
    if data['forecasts'][0]['temperature']['max'] is not None:
        today_temp_max = data['forecasts'][0]['temperature']['max']['celsius']['T18_24']
    else:
        today_temp_max = "不明"

    if data['forecasts'][0]['temperature']['min'] is not None:
        today_temp_min = data['forecasts'][0]['temperature']['min']['celsius']['T18_24']
    else:
        today_temp_min = "不明"

    # 平均気温の計算（最高気温と最低気温が両方取得できた場合のみ）
    if today_temp_max != "不明" and today_temp_min != "不明":
        avg_temp = (float(today_temp_max) + float(today_temp_min)) / 2
    else:
        avg_temp = "不明"

    # 最高気温と最低気温の平均値を計算
    if today_temp_max is not None and today_temp_min is not None:
        avg_temp = (float(today_temp_max) + float(today_temp_min)) / 2
        st.write(f"今日の平均気温: {avg_temp:.1f}℃")
    else:
        st.write("平均気温: 不明")
        avg_temp = 0

# ビール銘柄の選択
selected_beer = st.selectbox("ビールの銘柄を選んでください", list(beer_brands.keys()))

# 選択されたビール銘柄に応じた価格の自動反映
price = beer_brands[selected_beer]
st.write(f"価格: {price}円")
# 記録ボタン
submitted = st.button("記録を追加")

# CSVに保存するボタン
save_button = st.button("CSVに保存")

if save_button:
    # DataFrameをCSVに保存
    df.to_csv(csv_file, index=False)
    st.success('CSVファイルに保存されました！')

if uploaded_file is not None:
    # アップロードされたファイルをデータフレームとして読み込む
    df = pd.read_csv(uploaded_file)

    # 'Date'列を明示的に日付時刻型に変換
    df['Date'] = pd.to_datetime(df['Date'])
    # グラフ表示モードの選択
    mode = st.radio(
        "グラフ表示モードを選択してください",
        ('日付換算', '月換算')
    )

    # グラフを描画
    plt.figure(figsize=(10, 6))

    if mode == '日付換算':
        # 日付ごとの集計とグラフ描画
        daily_consumption = df.groupby(df['Date'].dt.date)['Price'].sum()
        plt.plot(daily_consumption.index, daily_consumption.values, marker='o', linestyle='-')
    elif mode == '月換算':
    # 月ごとの集計
        df['Month'] = df['Date'].dt.to_period('M')
        monthly_consumption = df.groupby('Month')['Price'].sum()
        # グラフ描画
        plt.plot(monthly_consumption.index.astype('datetime64[ns]'), monthly_consumption.values, marker='o', linestyle='-')
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
    # グラフの設定
    plt.title('Beer Consumption Cost')
    plt.xlabel('Date' if mode == '日付換算' else 'Month')
    plt.ylabel('Total Cost (JPY)')
    plt.ylim(bottom=0)  # Y軸の下限を0に設定
    plt.grid(axis='y')  # Y軸に沿ったグリッド線のみ表示
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Streamlitでグラフを表示
    st.pyplot(plt)
    
