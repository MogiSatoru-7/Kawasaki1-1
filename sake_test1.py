import streamlit as st
import requests
from datetime import datetime

# 地域コードの設定
city_code_list = {
    "東京都": "130010",
    "大阪府": "270000",
}

def get_monthly_temperature_forecast(city_code):
    """指定された地域コードで今後1ヶ月の気温予測を取得"""
    url = f"https://weather.tsukumijima.net/api/forecast/city/{city_code}"
    response = requests.get(url)
    data = response.json()
    temperatures = []
    if 'forecasts' in data:
        for forecast in data['forecasts']:
            if 'temperature' in forecast and forecast['temperature']['max'] is not None:
                temp = forecast['temperature']['max']['celsius']
                temperatures.append(float(temp))
    return temperatures

def calculate_monthly_beer_budget(temperatures, price, budget):
    """気温に基づいて予算内で飲めるビールの本数を計算"""
    beer_counts = []
    total_cost = 0
    for temp in temperatures:
        if temp > 25:  # 暑い日はビールを多めに
            beers = budget / price / len(temperatures) * 1.5
        elif temp < 15:  # 寒い日はビールを少なめに
            beers = budget / price / len(temperatures) * 0.5
        else:
            beers = budget / price / len(temperatures)
        beer_counts.append(min(beers, (budget - total_cost) / price))
        total_cost += beers * price
    return beer_counts

def main():
    st.title('ビール消費量予測アプリ')
    city_code_index = st.selectbox("地域を選んでください。", list(city_code_list.keys()))
    city_code = city_code_list[city_code_index]
    price = st.number_input("ビール1本あたりの価格を入力してください（円）")
    budget = st.number_input("月間ビール予算を入力してください（円）")

    if st.button("予測を実行"):
        temperatures = get_monthly_temperature_forecast(city_code)
        if temperatures:
            beer_counts = calculate_monthly_beer_budget(temperatures, price, budget)
            st.write("今後の気温予測に基づくビールの消費量（本数）:")
            for day, beers in enumerate(beer_counts):
                st.write(f"Day {day+1}: 約{beers:.2f}本")
        else:
            st.write("気温情報を取得できませんでした。")

if __name__ == "__main__":
    main()
