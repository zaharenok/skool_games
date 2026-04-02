#!/usr/bin/env python3
"""
Статистика Skool Games данных
"""
import json
from pathlib import Path
from datetime import datetime

# Загружаем JSON
data_file = Path("/home/oleg/repos/skool_games/skool_games_20260402_153048.json")

with open(data_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=" * 60)
print("📊 SKOOL GAMES - СТАТИСТИКА")
print("=" * 60)
print(f"Дата сбора: {data['scraped_at']}")
print()

categories = data['categories']

# Общая статистика
total_winners = sum(len(cat['winners']) for cat in categories)
total_growth = sum(
    winner['mrr_growth_value']
    for cat in categories
    for winner in cat['winners']
)

print(f"📈 Категорий: {len(categories)}")
print(f"👥 Победителей: {total_winners}")
print(f"💰 Общий рост MRR: ${total_growth:,.0f}")
print(f"📊 Средний рост на победителя: ${total_growth/total_winners:,.0f}")
print()

# По категориям
print("🏆 ТОП-3 по росту MRR:")
print("-" * 60)

cat_growth = []
for cat in categories:
    cat_total = sum(w['mrr_growth_value'] for w in cat['winners'])
    cat_growth.append({
        'name': cat['name'],
        'emoji': cat['emoji'],
        'total': cat_total,
        'winners': len(cat['winners'])
    })

# Сортируем по общему росту
cat_growth.sort(key=lambda x: x['total'], reverse=True)

for i, cat in enumerate(cat_growth[:3], 1):
    print(f"{i}. {cat['emoji']} {cat['name']:20s} "
          f"→ ${cat['total']:>10,.0f} "
          f"({cat['winners']} участников)")

print()

# Топ победители
print("🥇 ТОП-10 победителей по росту MRR:")
print("-" * 60)
all_winners = []
for cat in categories:
    for w in cat['winners']:
        all_winners.append({
            'name': w['name'],
            'community': w['community'],
            'category': cat['name'],
            'emoji': cat['emoji'],
            'growth': w['mrr_growth_value']
        })

all_winners.sort(key=lambda x: x['growth'], reverse=True)

for i, w in enumerate(all_winners[:10], 1):
    print(f"{i:2}. {w['emoji']} {w['category'][:12]:12s} "
          f"{w['name'][:20]:20s} ${w['growth']:>8,.0f}")

print()

# Детально по категориям
print("📋 ДЕТАЛИ ПО КАТЕГОРИЯМ:")
print("-" * 60)

for cat in categories:
    winners = cat['winners']
    total_cat = sum(w['mrr_growth_value'] for w in winners)
    avg = total_cat / len(winners)
    top_winner = max(winners, key=lambda x: x['mrr_growth_value'])

    print(f"\n{cat['emoji']} {cat['name']}")
    print(f"   Участников: {len(winners)}")
    print(f"   Общий рост: ${total_cat:,.0f}")
    print(f"   Средний: ${avg:,.0f}")
    print(f"   Лучший: {top_winner['name']} (${top_winner['mrr_growth_value']:,.0f})")

print()
print("=" * 60)
print("📊 Данные готовы к визуализации в Streamlit Dashboard!")
print("   Запусти: streamlit run dashboard.py")
print("=" * 60)
