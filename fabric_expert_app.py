import streamlit as st
import pandas as pd

@st.cache_data
def load_data(path):
    df = pd.read_excel(path)
    df["Мин плотность (г/м2)"] = pd.to_numeric(df["Мин плотность (г/м2)"], errors="coerce")
    df["Макс плотность (г/м2)"] = pd.to_numeric(df["Макс плотность (г/м2)"], errors="coerce")
    df["Цена за метр"] = pd.to_numeric(df["Цена за метр"], errors="coerce")
    df["Цена за кг"] = pd.to_numeric(df["Цена за кг"], errors="coerce")
    df["Город"] = df["Город"].astype(str).str.strip().str.lower()
    df["Состав"] = df["Состав"].astype(str).str.strip().str.lower()
    df["Название ткани"] = df["Название ткани"].astype(str).str.strip().str.lower()
    df["Цвета"] = df["Цвет"].astype(str).str.replace('\n', ' ').str.lower().str.split(",")
    return df

df = load_data("reliase.xlsx")
уникальные_ткани = sorted(df["Название ткани"].dropna().unique())
уникальные_составы = sorted(df["Состав"].dropna().unique())
уникальные_цвета = sorted(set(c.strip() for sublist in df["Цвета"] for c in sublist if isinstance(sublist, list)))
usd_rate = 93.0

st.title("Экспертная система подбора тканей")

st.sidebar.header("1. Название ткани или Состав")
use_filter_fabric = st.sidebar.checkbox("Включить фильтрацию по ткани/составу", value=True)
filter_mode = st.sidebar.radio("Фильтровать по:", ["Название ткани", "Состав"])
похожие_ткани = df.copy()
if use_filter_fabric:
    if filter_mode == "Название ткани":
        selected_name = st.sidebar.selectbox("Название ткани:", уникальные_ткани)
        selected_sostav = df[df["Название ткани"] == selected_name]["Состав"].unique()
        похожие_ткани = df[df["Состав"].isin(selected_sostav)]
    else:
        selected_sostav = st.sidebar.selectbox("Состав:", уникальные_составы)
        похожие_ткани = df[df["Состав"] == selected_sostav]

st.sidebar.header("2. Плотность")
use_filter_density = st.sidebar.checkbox("Включить фильтрацию по плотности", value=True)
min_density, max_density = st.sidebar.slider("Диапазон плотности (г/м²):", 0, 1000, (200, 400))

st.sidebar.header("3. Цена")
use_filter_price = st.sidebar.checkbox("Включить фильтрацию по цене", value=True)
purchase_type = st.sidebar.radio("Тип закупки:", ["Розничная", "Оптовая"])
currency = st.sidebar.radio("Валюта:", ["RUB", "USD"])
price_col = "Цена за метр" if purchase_type == "Розничная" else st.sidebar.radio("Единица:", ["Цена за метр", "Цена за кг"])
min_price = st.sidebar.number_input("Мин. цена", value=0.0)
max_price = st.sidebar.number_input("Макс. цена", value=2000.0)

st.sidebar.header("4. Срочность доставки")
use_filter_delivery = st.sidebar.checkbox("Включить фильтрацию по сроку доставки", value=True)
delivery_times = {
    "До 5 дней": ["нижний новгород"],
    "До 10 дней": ["нижний новгород", "москва"],
    "Более 15 дней": ["нижний новгород", "москва", "казань"]
}
selected_delivery = st.sidebar.selectbox("Срочность:", list(delivery_times.keys()))
allowed_cities = delivery_times[selected_delivery]

st.sidebar.header("5. Цвет")
use_filter_color = st.sidebar.checkbox("Включить фильтрацию по цвету", value=True)
selected_colors = st.sidebar.multiselect("Выберите цвета:", уникальные_цвета)

filtered_df = df.copy()
if use_filter_fabric:
    filtered_df = filtered_df[filtered_df.index.isin(похожие_ткани.index)]
if use_filter_density:
    filtered_df = filtered_df[
        (filtered_df["Макс плотность (г/м2)"] >= min_density) &
        (filtered_df["Мин плотность (г/м2)"] <= max_density)
    ]
if use_filter_price:
    prices = filtered_df[price_col] * (usd_rate if currency == "USD" else 1)
    filtered_df = filtered_df[(prices >= min_price) & (prices <= max_price)]

# Перерасчет в рубли для отображения
if currency == "USD":
    filtered_df["Цена за метр (в руб)"] = filtered_df["Цена за метр"] * usd_rate
    filtered_df["Цена за кг (в руб)"] = filtered_df["Цена за кг"] * usd_rate
else:
    filtered_df["Цена за метр (в руб)"] = filtered_df["Цена за метр"]
    filtered_df["Цена за кг (в руб)"] = filtered_df["Цена за кг"]

if use_filter_delivery:
    filtered_df = filtered_df[filtered_df["Город"].isin(allowed_cities)]
if use_filter_color and selected_colors:
    filtered_df = filtered_df[filtered_df["Цвета"].apply(lambda clrs: any(c.strip() in clrs for c in selected_colors))]

st.sidebar.header("6. AHP - Метод анализа иерархий")
use_ahp = st.sidebar.checkbox("Включить AHP", value=True)

if use_ahp and not filtered_df.empty:
    weights = {
        "Ткань/Состав": st.sidebar.slider("Вес: Название ткани / Состав", 0.0, 1.0, 0.2),
        "Плотность": st.sidebar.slider("Вес: Плотность", 0.0, 1.0, 0.25),
        "Цена": st.sidebar.slider("Вес: Цена", 0.0, 1.0, 0.25),
        "Срок доставки": st.sidebar.slider("Вес: Срок доставки", 0.0, 1.0, 0.15),
        "Цвет": st.sidebar.slider("Вес: Цвет", 0.0, 1.0, 0.15)
    }
    total = sum(weights.values())
    weights = {k: v / total for k, v in weights.items()}
    def norm_score(val, best, tol): return max(0, 1 - abs(val - best) / tol) if pd.notna(val) else 1
    target_density = (min_density + max_density) / 2
    filtered_df["Средняя плотность"] = (
        filtered_df["Мин плотность (г/м2)"] + filtered_df["Макс плотность (г/м2)"]) / 2
    filtered_df["Оценка_плотности"] = filtered_df["Средняя плотность"].apply(lambda x: norm_score(x, target_density, 50))
    if use_filter_price:
        price_val = filtered_df[price_col] * (usd_rate if currency == "USD" else 1)
        filtered_df["Оценка_цены"] = price_val.apply(lambda x: norm_score(x, price_val.min(), 300))
    else:
        filtered_df["Оценка_цены"] = 1
    filtered_df["Оценка_ткани"] = 1
    filtered_df["Оценка_срока"] = 1
    filtered_df["Оценка_цвета"] = 1 if not use_filter_color else filtered_df["Цвета"].apply(
        lambda clrs: 1 if any(c.strip() in clrs for c in selected_colors) else 0)
    filtered_df["AHP_оценка"] = (
        filtered_df["Оценка_ткани"] * weights["Ткань/Состав"] +
        filtered_df["Оценка_плотности"] * weights["Плотность"] +
        filtered_df["Оценка_цены"] * weights["Цена"] +
        filtered_df["Оценка_срока"] * weights["Срок доставки"] +
        filtered_df["Оценка_цвета"] * weights["Цвет"]
    )
    sorted_weights = sorted(weights.items(), key=lambda x: -x[1])
    priority_cols = []
    for key, _ in sorted_weights:
        if key == "Ткань/Состав": priority_cols += ["Название ткани", "Состав"]
        elif key == "Плотность": priority_cols += ["Мин плотность (г/м2)", "Макс плотность (г/м2)"]
        elif key == "Цена": priority_cols += ["Цена за метр (в руб)", "Цена за кг (в руб)"]
        elif key == "Срок доставки": priority_cols.append("Город")
        elif key == "Цвет": priority_cols.append("Цвет")
    rest = [c for c in filtered_df.columns if c not in priority_cols and not c.startswith("Оценка")]
    show_cols = priority_cols + ["AHP_оценка"] + rest
    show_cols = list(dict.fromkeys(show_cols))  # Удалить дубликаты
    st.subheader("Результаты по AHP")
    st.write(filtered_df.sort_values("AHP_оценка", ascending=False)[show_cols].reset_index(drop=True))
else:
    st.subheader("Результаты фильтрации")
    st.write(filtered_df.reset_index(drop=True))


# --- Отображение исходной таблицы ---
with st.expander("📄 Посмотреть исходные данные"):
    st.dataframe(df)
