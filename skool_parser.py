"""
Skool Games Parser - Парсер данных с Skool Games leaderboard
"""
import asyncio
import json
import csv
from datetime import datetime
from playwright.async_api import async_playwright
from dataclasses import dataclass, asdict
from typing import List, Optional

COOKIES = [
    {
        "name": "client_id",
        "value": "3bb9498182124479a98f44f1b0df11f2",
        "domain": ".skool.com",
        "path": "/",
        "secure": True,
    },
    {
        "name": "auth_token",
        "value": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE4MDUyMTg0MzksImlhdCI6MTc3MzY4MjQzOSwidXNlcl9pZCI6IjA0YjAyZjUwMjg1MzQ3MzVhZTYwYmY0MTQ0NjViNzY2In0.VLa9BpYNWOLo6AAtVhQxMPN1jT6PNpxzPUpnHXOKvZQ",
        "domain": ".skool.com",
        "path": "/",
        "secure": True,
    },
    {
        "name": "aws-waf-token",
        "value": "01fe6574-edc7-407b-b5bb-cebe7f8337fd:HAoArnxeUcMKAAAA:pcucFFaxMiDZlMnHfnlZsEiec56MYsqYRlwY1Iir0rjv6rQDqxTMIKbecNefe6t+mazWa0VqWgDwmBjNIu1zWtZbVOKx20PrvpbLmOJ0QPZLfONwbhVshy8Jea5cijUxaO1lU/m/QRt1VWZcojnTombWHa1PU3znOi+0gJSO29dZ6PXeBmrOpHBE4EjeWaUZwl3bUjm0adaHNobOhpOymGiXcxT3/Uo/K83H8SOjDVHHYMd06TvM31FSdDK+L85cKgFekg==",
        "domain": ".skool.com",
        "path": "/",
        "secure": True,
    }
]


@dataclass
class Winner:
    """Данные о победителе"""
    position: int
    name: str
    community: str
    mrr_growth: str  # e.g. "+$536"
    mrr_growth_value: float  # e.g. 536.0
    current_mrr: str  # e.g. "$1,528"
    current_mrr_value: float  # e.g. 1528.0
    category: str


@dataclass
class Category:
    """Данные о категории"""
    name: str
    emoji: str
    winners: List[Winner]


def parse_mrr(value: str) -> float:
    """Парсит MRR значение в float"""
    if not value:
        return 0.0
    # Убираем $, запятые и плюсы
    cleaned = value.replace('$', '').replace(',', '').replace('+', '').strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


async def parse_category_page(page, category_emoji: str, category_name: str) -> Category:
    """Парсит страницу категории"""
    print(f"Парсинг категории: {category_emoji} {category_name}")

    # Кликаем на категорию
    try:
        await page.click(f'text="{category_emoji} {category_name}"', timeout=5000)
    except:
        # Пробуем кликнуть только по названию
        await page.click(f'text="{category_name}"', timeout=5000)

    await page.wait_for_timeout(3000)

    winners = []

    # Получаем текст страницы
    all_text = await page.inner_text('body')
    lines = all_text.split('\n')

    # Ищем данные в формате:
    # Номер
    # Имя
    # Название сообщества
    # +$X (рост)
    # +$X
    # $X,X00 (текущий MRR)

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Проверяем, является ли строка номером позиции
        if line.isdigit() and 1 <= int(line) <= 100:
            position = int(line)

            # Следующие строки должны быть: имя, сообщество, рост, текущий MRR
            if i + 5 < len(lines):
                name = lines[i + 1].strip()
                community = lines[i + 2].strip()

                # Пропускаем звезды и эмодзи
                j = 3
                mrr_growth = lines[i + j].strip()
                while not mrr_growth.startswith('+$') and j < 8:
                    j += 1
                    if i + j >= len(lines):
                        break
                    mrr_growth = lines[i + j].strip()

                current_mrr = ""
                if i + j + 1 < len(lines):
                    potential_mrr = lines[i + j + 1].strip()
                    if potential_mrr.startswith('$'):
                        current_mrr = potential_mrr

                if mrr_growth.startswith('+$'):
                    winner = Winner(
                        position=position,
                        name=name,
                        community=community,
                        mrr_growth=mrr_growth,
                        mrr_growth_value=parse_mrr(mrr_growth),
                        current_mrr=current_mrr,
                        current_mrr_value=parse_mrr(current_mrr),
                        category=category_name
                    )
                    winners.append(winner)
                    print(f"  {position}. {name} - {community} | Growth: {mrr_growth} | MRR: {current_mrr}")

        i += 1

    # Кликаем "See more" если есть
    see_more = await page.query_selector('text="See more"')
    if see_more:
        print("  Загрузка дополнительных данных...")
        await see_more.click()
        await page.wait_for_timeout(2000)

        # Повторно парсим
        all_text = await page.inner_text('body')
        lines = all_text.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if line.isdigit() and 1 <= int(line) <= 100:
                position = int(line)

                if i + 5 < len(lines):
                    name = lines[i + 1].strip()
                    community = lines[i + 2].strip()

                    j = 3
                    mrr_growth = lines[i + j].strip()
                    while not mrr_growth.startswith('+$') and j < 8:
                        j += 1
                        if i + j >= len(lines):
                            break
                        mrr_growth = lines[i + j].strip()

                    current_mrr = ""
                    if i + j + 1 < len(lines):
                        potential_mrr = lines[i + j + 1].strip()
                        if potential_mrr.startswith('$'):
                            current_mrr = potential_mrr

                    if mrr_growth.startswith('+$'):
                        # Проверяем, нет ли уже такого победителя
                        existing = next((w for w in winners if w.position == position and w.name == name), None)
                        if not existing:
                            winner = Winner(
                                position=position,
                                name=name,
                                community=community,
                                mrr_growth=mrr_growth,
                                mrr_growth_value=parse_mrr(mrr_growth),
                                current_mrr=current_mrr,
                                current_mrr_value=parse_mrr(current_mrr),
                                category=category_name
                            )
                            winners.append(winner)
                            print(f"  {position}. {name} - {community} | Growth: {mrr_growth} | MRR: {current_mrr}")
            i += 1

    return Category(name=category_name, emoji=category_emoji, winners=winners)


async def parse_all_categories(page) -> List[Category]:
    """Парсит все категории"""

    categories_data = [
        ("🎨", "Hobbies"),
        ("🎸", "Music"),
        ("💰", "Money"),
        ("🙏", "Spirituality"),
        ("💻", "Tech"),
        ("🥕", "Health"),
        ("⚽", "Sports"),
        ("📚", "Self-improvement"),
        ("❤️", "Relationships"),
    ]

    categories = []

    for emoji, name in categories_data:
        try:
            category = await parse_category_page(page, emoji, name)
            categories.append(category)
            await page.wait_for_timeout(1000)
        except Exception as e:
            print(f"Ошибка при парсинге категории {name}: {e}")

    return categories


async def main():
    """Главная функция"""
    url = "https://www.skool.com/skoolers/-/games"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        # Добавляем куки
        await context.add_cookies(COOKIES)

        page = await context.new_page()
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Парсим все категории
        categories = await parse_all_categories(page)

        # Сохраняем результаты
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON
        output_data = {
            "scraped_at": datetime.now().isoformat(),
            "categories": [
                {
                    "name": cat.name,
                    "emoji": cat.emoji,
                    "winners": [asdict(w) for w in cat.winners]
                }
                for cat in categories
            ]
        }

        with open(f'skool_games_{timestamp}.json', 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        # CSV
        with open(f'skool_games_{timestamp}.csv', 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Category', 'Position', 'Name', 'Community', 'MRR Growth', 'MRR Growth Value', 'Current MRR', 'Current MRR Value'])

            for cat in categories:
                for winner in cat.winners:
                    writer.writerow([
                        cat.name,
                        winner.position,
                        winner.name,
                        winner.community,
                        winner.mrr_growth,
                        winner.mrr_growth_value,
                        winner.current_mrr,
                        winner.current_mrr_value
                    ])

        # Статистика
        total_winners = sum(len(cat.winners) for cat in categories)
        print(f"\n✅ Парсинг завершен!")
        print(f"📊 Категорий: {len(categories)}")
        print(f"👥 Всего победителей: {total_winners}")
        print(f"💾 Сохранено: skool_games_{timestamp}.json и skool_games_{timestamp}.csv")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
