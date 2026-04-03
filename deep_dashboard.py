"""
Skool Games Deep Dashboard - Дашборд для изучения групп
"""
import streamlit as st
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

# Custom CSS - улучшенный дизайн
st.markdown("""
<style>
    /* Главная страница */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        color: white;
    }

    /* Заголовок категории */
    .category-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px 25px;
        border-radius: 12px;
        margin: 30px 0 20px 0;
        font-size: 1.4em;
        font-weight: 600;
        box-shadow: 0 4px 10px rgba(102, 126, 234, 0.3);
    }

    /* Описание */
    .description-box {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 15px;
        border-radius: 8px;
        margin: 15px 0;
        line-height: 1.6;
    }

    /* Полный текст */
    .full-text-box {
        background: #fff;
        border: 1px solid #dee2e6;
        border-radius: 10px;
        padding: 20px;
        margin: 15px 0;
        max-height: 400px;
        overflow-y: auto;
        white-space: pre-wrap;
        line-height: 1.7;
    }

    /* Фичи */
    .feature-item {
        background: white;
        border: 1px solid #e9ecef;
        border-left: 3px solid #667eea;
        border-radius: 6px;
        padding: 10px 15px;
        margin: 6px 0;
        font-size: 0.95em;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>🔍 Skool Games Deep Analysis</h1></div>', unsafe_allow_html=True)

# Load data
@st.cache_data
def load_deep_data():
    """Загружает глубокие данные о группах"""
    data_dir = Path('.')

    # Try enhanced data first (all categories with About pages)
    enhanced_files = list(data_dir.glob('skool_data_*/skool_enhanced_*.json'))

    # Fallback to deep data (some categories with About pages)
    if not enhanced_files:
        enhanced_files = list(data_dir.glob('skool_data_*/skool_deep_*.json'))

    if not enhanced_files:
        return None, None, None

    latest_json = max(enhanced_files, key=lambda p: p.stat().st_mtime)

    with open(latest_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Find directories
    md_dir = latest_json.parent.parent / 'markdown'
    images_dir = latest_json.parent.parent / 'images'

    # Extract groups from categories_data format
    groups = []
    if 'categories_data' in data:
        for cat in data['categories_data']:
            cat_emoji = cat.get('emoji', '')
            for winner in cat.get('winners', []):
                # Add emoji if missing
                if 'category_emoji' not in winner and cat_emoji:
                    winner['category_emoji'] = cat_emoji
                groups.append(winner)

    return groups, md_dir, images_dir

groups, md_dir, images_dir = load_deep_data()

if not groups:
    st.warning("Нет данных. Запустите `python3 skool_deep_parser.py` сначала.")
    st.info("💡 Для парсинга всех категорий может потребоваться несколько минут.")
    st.stop()

# Convert to list
groups_list = []
for g in groups:
    groups_list.append({
        'name': g.get('name', g.get('community', '')),
        'category': g.get('category', ''),
        'emoji': g.get('category_emoji', g.get('emoji', '')),
        'position': g.get('position', 0),
        'url': g.get('url', ''),
        'about_url': g.get('about_url', ''),
        'members': g.get('members_count', 0),
        'online': g.get('online_count', 0),
        'price': g.get('price_value', 0),
        'is_free': g.get('is_free', False),
        'is_public': g.get('is_public', False),
        'mrr_growth': g.get('mrr_growth_value', 0),
        'creator': g.get('creator_name', ''),
        'description': g.get('about_description', ''),
        'full_text': g.get('about_full_text', ''),
        'features': g.get('features', []),
        'cover_image': g.get('cover_image_url', ''),
        'cover_base64': g.get('cover_image_base64', '')
    })

# Sidebar
st.sidebar.header("🎯 Фильтры")

categories = sorted(list(set([g['category'] for g in groups_list])))
selected_cat = st.sidebar.selectbox('Категория', ['All'] + categories)
price_filter = st.sidebar.radio('Тип', ['All', 'Free', 'Paid'], horizontal=True)
max_members = max([g['members'] for g in groups_list])
min_members = st.sidebar.slider('Мин. участников', 0, max_members, 0)

# Apply filters
filtered_groups = []
for g in groups_list:
    if selected_cat != 'All' and g['category'] != selected_cat:
        continue
    if price_filter == 'Free' and not g['is_free']:
        continue
    if price_filter == 'Paid' and g['is_free']:
        continue
    if g['members'] < min_members:
        continue
    filtered_groups.append(g)

# Stats
st.header("📊 Общая статистика")

# Show actual categories count
actual_categories = sorted(list(set([g['category'] for g in groups_list])))
total_categories_all = 9  # All possible categories

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("📁 Категорий", f"{len(actual_categories)}/{total_categories_all}")
with col2:
    st.metric("📁 Групп", len(filtered_groups))
with col3:
    total_members = sum([g['members'] for g in filtered_groups])
    st.metric("👥 Участников", f"{total_members:,.0f}")
with col4:
    paid_groups = [g for g in filtered_groups if g['price'] > 0]
    avg_price = sum([g['price'] for g in paid_groups]) / len(paid_groups) if paid_groups else 0
    st.metric("💰 Ср. цена", f"${avg_price:.0f}")
with col5:
    total_mrr = sum([g['mrr_growth'] for g in filtered_groups])
    st.metric("📈 MRR рост", f"${total_mrr:,.0f}")

# Info if not all categories
if len(actual_categories) < total_categories_all:
    st.info(f"ℹ️ В данных только {len(actual_categories)} из {total_categories_all} категорий. Для сбора всех категорий запустите:")
    st.code("python3 skool_deep_parser.py")

# Charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("🎯 Распределение по категориям")
    cat_counts = {}
    for g in filtered_groups:
        cat_counts[g['category']] = cat_counts.get(g['category'], 0) + 1

    if cat_counts:
        categories_list = list(cat_counts.keys())
        fig = px.pie(
            values=list(cat_counts.values()),
            names=categories_list,
            hole=0.4,
            color=categories_list,
            color_discrete_map={
                cat: px.colors.qualitative.Set3[i % len(px.colors.qualitative.Set3)]
                for i, cat in enumerate(categories_list)
            }
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(showlegend=True, height=400, margin=dict(t=30, b=30, l=30, r=30))
        st.plotly_chart(fig, width="stretch")

with col2:
    st.subheader("💎 Топ-15 по цене")
    price_data = [g for g in filtered_groups if g['price'] > 0]
    price_data = sorted(price_data, key=lambda x: x['price'])[:15]

    if price_data:
        fig = px.bar(
            x=[g['price'] for g in price_data],
            y=[g['name'] for g in price_data],
            orientation='h',
            color=[g['price'] for g in price_data],
            color_continuous_scale='Viridis',
            labels={'x': 'Цена ($)', 'y': 'Группа'},
            height=400
        )
        fig.update_layout(yaxis={'categoryorder': 'total ascending'}, margin=dict(t=30, b=30, l=20, r=30))
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Нет данных о ценах")

# Group list
st.header("📋 Группы")

# Search
search = st.text_input("🔍 Поиск по названию, описанию или фичам")

if search:
    search_lower = search.lower()
    filtered_groups = [
        g for g in filtered_groups
        if search_lower in g['name'].lower() or
           search_lower in g['description'].lower() or
           any(search_lower in f.lower() for f in g['features'])
    ]

# Group by category
if selected_cat == 'All':
    categories_to_show = sorted(list(set([g['category'] for g in filtered_groups])))
else:
    categories_to_show = [selected_cat]

if not categories_to_show:
    st.info("ℹ️ В данных только категории Hobbies. Для сбора всех категорий запустите:")
    st.code("python3 skool_deep_parser.py")

for category in categories_to_show:
    cat_groups = [g for g in filtered_groups if g['category'] == category]

    if not cat_groups:
        continue

    # Category header
    cat_emoji = cat_groups[0]['emoji']
    st.markdown(f'<div class="category-header">{cat_emoji} {category} • {len(cat_groups)} групп</div>', unsafe_allow_html=True)

    # Display groups
    for g in sorted(cat_groups, key=lambda x: x['position']):
        with st.expander(f"#{g['position']} {g['name']}", expanded=False):
            # Cover image
            if g['cover_base64']:
                img_data = f"data:image/png;base64,{g['cover_base64']}"
                st.image(img_data, width="stretch")
            elif g['cover_image']:
                st.image(g['cover_image'], width="stretch")

            # Main info
            col1, col2 = st.columns([3, 1])

            with col1:
                # URL and name
                st.markdown(f"### 🔗 [{g['name']}]({g['url']})")
                if g['about_url']:
                    st.markdown(f"📄 [About страница]({g['about_url']})")

                # Creator
                if g['creator']:
                    st.markdown(f"👤 **Создатель:** {g['creator']}")

                # Short description
                if g['description']:
                    st.markdown('<div class="description-box">', unsafe_allow_html=True)
                    st.markdown(g['description'])
                    st.markdown('</div>', unsafe_allow_html=True)

                # Features
                if g['features']:
                    st.markdown("#### ✨ Возможности:")
                    for feature in g['features'][:5]:
                        st.markdown(f"<div class='feature-item'>✓ {feature}</div>", unsafe_allow_html=True)
                    if len(g['features']) > 5:
                        st.caption(f"...и еще {len(g['features']) - 5} функций")

                # Full text in tab
                if g['full_text']:
                    with st.expander("📖 Полное описание с About страницы"):
                        st.markdown('<div class="full-text-box">', unsafe_allow_html=True)
                        st.markdown(g['full_text'])
                        st.markdown('</div>', unsafe_allow_html=True)

            with col2:
                st.markdown("### 📊")
                st.markdown(f"## {g['members']:,}")
                st.caption("участников")

                st.markdown(f"## {g['online']}")
                st.caption("онлайн")

                price_display = "Free" if g['is_free'] else f"${g['price']:.0f}"
                st.markdown(f"## {price_display}")
                st.caption("цена")

                st.markdown(f"## ${g['mrr_growth']:.0f}")
                st.caption("MRR рост")

                # Status badge
                status_badge = "🌍 Public" if g['is_public'] else "🔒 Private"
                st.markdown(f"**{status_badge}**")

            st.markdown("---")
