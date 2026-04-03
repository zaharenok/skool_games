"""
Skool Games Deep Dashboard - Дашборд для изучения групп
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import json
import re
from datetime import datetime

st.set_page_config(
    page_title="Skool Games Deep Analysis",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .markdown-body {
        font-size: 14px;
        line-height: 1.6;
    }
    .group-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        background: white;
    }
    .stat-box {
        background: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔍 Skool Games Deep Analysis")

# Load data
@st.cache_data
def load_deep_data():
    """Загружает глубокие данные о группах"""
    data_dir = Path('.')
    json_files = list(data_dir.glob('skool_data_*/skool_deep_*.json'))

    if not json_files:
        return None, None

    latest_json = max(json_files, key=lambda p: p.stat().st_mtime)

    with open(latest_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Find markdown directory
    md_dir = latest_json.parent.parent / 'markdown'

    return data['groups'], md_dir

groups, md_dir = load_deep_data()

if not groups:
    st.warning("Нет данных. Запустите `python3 skool_deep_parser.py` сначала.")
    st.stop()

# Convert to DataFrame
df = pd.DataFrame([{
    'name': g['name'],
    'category': g['category'],
    'emoji': g['category_emoji'],
    'position': g['position'],
    'url': g['url'],
    'members': g['members_count'],
    'online': g['online_count'],
    'price': g['price_value'],
    'is_free': g['is_free'],
    'is_public': g['is_public'],
    'mrr_growth': g['mrr_growth_value'],
    'creator': g['creator_name'],
    'description': g['about_description'][:200],
    'features': len(g.get('features', [])),
    'has_markdown': True
} for g in groups])

# Sidebar
st.sidebar.header("Фильтры")

# Category filter
all_cats = ['All'] + sorted(df['category'].unique())
selected_cat = st.sidebar.selectbox('Категория', all_cats)

# Price filter
price_filter = st.sidebar.radio('Тип', ['All', 'Free', 'Paid'])

# Members filter
min_members = st.sidebar.slider('Мин. участников', 0, int(df['members'].max()), 0)

# Apply filters
filtered_df = df.copy()

if selected_cat != 'All':
    filtered_df = filtered_df[filtered_df['category'] == selected_cat]

if price_filter == 'Free':
    filtered_df = filtered_df[filtered_df['is_free'] == True]
elif price_filter == 'Paid':
    filtered_df = filtered_df[filtered_df['is_free'] == False]

if min_members > 0:
    filtered_df = filtered_df[filtered_df['members'] >= min_members]

# Stats
st.header("📊 Статистика")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Групп", len(filtered_df))
with col2:
    st.metric("Участников", f"{filtered_df['members'].sum():,.0f}")
with col3:
    avg_price = filtered_df[filtered_df['price'] > 0]['price'].mean() if len(filtered_df[filtered_df['price'] > 0]) > 0 else 0
    st.metric("Ср. цена", f"${avg_price:.0f}")
with col4:
    st.metric("MRR рост", f"${filtered_df['mrr_growth'].sum():,.0f}")

# Charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("Распределение по категориям")
    cat_counts = filtered_df['category'].value_counts().reset_index()
    cat_counts.columns = ['Category', 'Count']
    fig = px.pie(cat_counts, values='Count', names='Category', hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Цены")
    price_data = filtered_df[filtered_df['price'] > 0][['name', 'price']].sort_values('price', ascending=True).head(15)
    if not price_data.empty:
        fig = px.bar(price_data, x='price', y='name', orientation='h',
                     title='Топ-15 по цене', labels={'price': 'Цена ($)', 'name': 'Группа'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Нет данных о ценах")

# Group list
st.header("📋 Список групп")

# Search
search = st.text_input("🔍 Поиск по названию или описанию")

if search:
    search_df = filtered_df[
        filtered_df['name'].str.contains(search, case=False, na=False) |
        filtered_df['description'].str.contains(search, case=False, na=False)
    ]
else:
    search_df = filtered_df

# Display groups
for _, row in search_df.iterrows():
    with st.expander(f"{row['emoji']} {row['position']}. {row['name']} ({row['category']})"):
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"**URL:** [{row['name']}]({row['url']})")
            st.markdown(f"**Создатель:** {row['creator']}")
            st.markdown(f"**Описание:** {row['description']}...")

            # Load and display markdown if exists
            if md_dir:
                safe_name = re.sub(r'[<>:"|?*\\/]', '_', row['name'])
                safe_name = safe_name.replace(' ', '_')[:100]
                md_file = md_dir / f"{safe_name}.md"

                if md_file.exists():
                    with open(md_file, 'r', encoding='utf-8') as f:
                        md_content = f.read()
                    st.markdown("---")
                    st.markdown(md_content)

        with col2:
            st.markdown("### 📊 Статистика")
            st.metric("Участников", row['members'])
            st.metric("Онлайн", row['online'])
            st.metric("Цена", "Free" if row['is_free'] else f"${row['price']:.0f}")
            st.metric("MRR рост", f"${row['mrr_growth']:.0f}")
            st.metric("Фичи", row['features'])

# Export
st.header("💾 Экспорт")

col1, col2, col3 = st.columns(3)

with col1:
    csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button("📥 CSV", csv, "skool_groups.csv", "text/csv")

with col2:
    json_data = json.dumps([g for g in groups if g['name'] in filtered_df['name'].values],
                           ensure_ascii=False, indent=2)
    st.download_button("📥 JSON", json_data, "skool_groups.json", "application/json")

with col3:
    # Create combined markdown
    combined_md = "# Skool Groups Export\n\n"
    for _, row in search_df.iterrows():
        combined_md += f"## {row['name']}\n\n"
        combined_md += f"- **Category:** {row['category']}\n"
        combined_md += f"- **Position:** #{row['position']}\n"
        combined_md += f"- **Members:** {row['members']}\n"
        combined_md += f"- **Price:** {'Free' if row['is_free'] else f'${row[\"price\"]:.0f}'}\n"
        combined_md += f"- **URL:** {row['url']}\n\n"
        if md_dir:
            safe_name = re.sub(r'[<>:"|?*\\/]', '_', row['name'])
            safe_name = safe_name.replace(' ', '_')[:100]
            md_file = md_dir / f"{safe_name}.md"
            if md_file.exists():
                with open(md_file, 'r', encoding='utf-8') as f:
                    combined_md += f.read() + "\n\n---\n\n"

    st.download_button("📥 Markdown", combined_md, "skool_groups.md", "text/markdown")
