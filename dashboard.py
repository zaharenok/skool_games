"""
Skool Games Dashboard - Интерактивный дашборд для данных Skool Games
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json

st.set_page_config(
    page_title="Skool Games Dashboard",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🏆 Skool Games Leaderboard Dashboard")

# Загрузка данных
@st.cache_data
def load_data():
    try:
        with open('skool_games_20260402_153048.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        winners = []
        for cat in data['categories']:
            for w in cat['winners']:
                winners.append({
                    'Category': cat['name'],
                    'Emoji': cat['emoji'],
                    'Position': w['position'],
                    'Name': w['name'],
                    'Community': w['community'],
                    'MRR Growth': w['mrr_growth'],
                    'Growth Value': w['mrr_growth_value'],
                    'Current MRR': w['current_mrr'],
                    'MRR Value': w['current_mrr_value']
                })
        return pd.DataFrame(winners)
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("Нет данных для отображения. Запустите парсер сначала.")
    st.stop()

# Боковая панель
st.sidebar.header("Фильтры")

# Выбор категории
all_categories = ['All'] + sorted(df['Category'].unique())
selected_category = st.sidebar.selectbox('Категория', all_categories)

if selected_category == 'All':
    filtered_df = df
else:
    filtered_df = df[df['Category'] == selected_category]

# Статистика
st.header("📊 Общая статистика")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Всего участников", len(filtered_df))

with col2:
    total_growth = filtered_df['Growth Value'].sum()
    st.metric("Общий рост MRR", f"${total_growth:,.0f}")

with col3:
    avg_growth = filtered_df['Growth Value'].mean()
    st.metric("Средний рост", f"${avg_growth:,.0f}")

with col4:
    st.metric("Категорий", filtered_df['Category'].nunique())

# Графики
st.header("📈 Визуализация")

# Рост по категориям
col1, col2 = st.columns(2)

with col1:
    st.subheader("Общий рост MRR по категориям")
    category_growth = df.groupby('Category')['Growth Value'].sum().reset_index()
    category_growth = category_growth.sort_values('Growth Value', ascending=True)

    fig_cat = px.bar(
        category_growth,
        x='Growth Value',
        y='Category',
        orientation='h',
        color='Growth Value',
        color_continuous_scale='Viridis',
        text_auto='$,.0f'
    )
    fig_cat.update_layout(
        xaxis_title="Рост MRR ($)",
        yaxis_title="",
        height=400,
        showlegend=False
    )
    st.plotly_chart(fig_cat, use_container_width=True)

with col2:
    st.subheader("Количество участников по категориям")
    category_count = df.groupby('Category').size().reset_index(name='Count')
    category_count = category_count.sort_values('Count', ascending=True)

    fig_count = px.bar(
        category_count,
        x='Count',
        y='Category',
        orientation='h',
        color='Count',
        color_continuous_scale='Plasma',
        text_auto=True
    )
    fig_count.update_layout(
        xaxis_title="Количество",
        yaxis_title="",
        height=400,
        showlegend=False
    )
    st.plotly_chart(fig_count, use_container_width=True)

# Топ участники
st.header("🏅 Топ участники")

# Топ по росту MRR
col1, col2 = st.columns(2)

with col1:
    st.subheader("Топ-10 по росту MRR")
    top_growth = filtered_df.nlargest(10, 'Growth Value')[['Name', 'Community', 'Category', 'MRR Growth', 'Growth Value']]

    fig_top_growth = px.bar(
        top_growth,
        x='Growth Value',
        y='Name',
        orientation='h',
        color='Category',
        text='MRR Growth',
        height=500
    )
    fig_top_growth.update_layout(
        xaxis_title="Рост MRR ($)",
        yaxis_title="",
        yaxis={'categoryorder': 'total ascending'},
        showlegend=True
    )
    st.plotly_chart(fig_top_growth, use_container_width=True)

with col2:
    st.subheader("Топ-10 по текущему MRR")
    top_mrr = filtered_df[filtered_df['MRR Value'] > 0].nlargest(10, 'MRR Value')[['Name', 'Community', 'Category', 'Current MRR', 'MRR Value']]

    if not top_mrr.empty:
        fig_top_mrr = px.bar(
            top_mrr,
            x='MRR Value',
            y='Name',
            orientation='h',
            color='Category',
            text='Current MRR',
            height=500
        )
        fig_top_mrr.update_layout(
            xaxis_title="Текущий MRR ($)",
            yaxis_title="",
            yaxis={'categoryorder': 'total ascending'},
            showlegend=True
        )
        st.plotly_chart(fig_top_mrr, use_container_width=True)
    else:
        st.info("Нет данных о текущем MRR")

# Детальная таблица
st.header("📋 Детальные данные")

# Возможность поиска и фильтрации
search = st.text_input("🔍 Поиск по имени или сообществу")

if search:
    search_df = filtered_df[
        filtered_df['Name'].str.contains(search, case=False, na=False) |
        filtered_df['Community'].str.contains(search, case=False, na=False)
    ]
else:
    search_df = filtered_df

# Отображение таблицы с возможностью сортировки
display_df = search_df[['Position', 'Category', 'Name', 'Community', 'MRR Growth', 'Current MRR']].copy()
display_df.columns = ['#', 'Категория', 'Имя', 'Сообщество', 'Рост MRR', 'Текущий MRR']

st.dataframe(
    display_df.sort_values('#'),
    use_container_width=True,
    hide_index=True
)

# Экспорт данных
st.header("💾 Экспорт данных")

col1, col2 = st.columns(2)

with col1:
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 Скачать CSV",
        data=csv,
        file_name=f"skool_games_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

with col2:
    json_data = json.dumps(df.to_dict('records'), ensure_ascii=False, indent=2)
    st.download_button(
        label="📥 Скачать JSON",
        data=json_data,
        file_name=f"skool_games_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json"
    )

# Footer
st.divider()
st.caption(f"Данные обновлены: {datetime.now().strftime('%d.%m.%Y %H:%M')} | Skool Games Parser")
