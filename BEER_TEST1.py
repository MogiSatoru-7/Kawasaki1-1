import streamlit as st
import pandas as pd

st.title('ビール管理アプリ')

days = 1  # 日数を1日に設定

beers_per_day = {}  # 日ごとのビールの本数を保持する辞書

for day in range(1, days + 1):
    beers_per_day[day] = st.slider(f'{day}日目の本数', 0, 10, 0)

# ビールの種類と価格の辞書
beer_prices = {
    "サッポロビール350㎜": 250,
    "サッポロビール500㎜": 300,
    "アサヒビール350㎜": 250,
    "アサヒビール500㎜": 300,
    "サントリービール350㎜": 250,
    "サントリービール500㎜": 300,
    "キリンービール350㎜": 250,
    "キリンービール500㎜": 300,
}

# 予算の入力
budget = st.number_input("予算を入力してください（円）", min_value=0.0)

# 選択されたビールのリストを保持する辞書
selected_beers_per_day = {}

for day, beers in beers_per_day.items():
    selected_beers = []
    for i in range(beers):
        beer = st.selectbox(f"{day}日目の{len(selected_beers)+1}本目のビールを選択してください", list(beer_prices.keys()))
        selected_beers.append(beer)
    selected_beers_per_day[day] = selected_beers

# 各日のビールの選択をセレクトボックスのようなフレームで表示
st.write("各日のビールの選択:")
for day, beers in selected_beers_per_day.items():
    beers_str = '\n'.join(beers)
    st.text_area(f"{day}日目のビールの選択:", value=beers_str, height=100)

# 各日のビールの合計金額を計算する
total_cost_per_day = {}
for day, beers in selected_beers_per_day.items():
    total_cost = sum(beer_prices[beer] for beer in beers)
    total_cost_per_day[day] = total_cost

# 各日のビールの合計金額を表示
st.write("各日のビールの合計金額:")
for day, total_cost in total_cost_per_day.items():
    st.write(f"{day}日目: {total_cost}円")

# 合計金額が予算を超えているかどうかを判断して表示
total_cost = sum(total_cost_per_day.values())
if total_cost <= budget:
    st.write(f"合計金額: {total_cost}円 (予算内)")
else:
    st.write(f"合計金額: {total_cost}円 (予算オーバー)")