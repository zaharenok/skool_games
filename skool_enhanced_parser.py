"""
Skool Games Enhanced Parser - Парсер данных о группах-победителях Skool Games
"""
import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright
from dataclasses import dataclass, asdict
from typing import List, Optional
from urllib.parse import urljoin

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
class GroupInfo:
    """Информация о группе"""
    name: str
    slug: str
    url: str
    title: str
    description: str
    members: str
    members_count: int
    status: str  # Private/Public
    price: str
    price_value: float
    creator: str
    creator_url: str
    admin_count: int
    online_count: str
    online_count_value: int
    category_from_games: str  # Категория из Games
    position_in_category: int  # Позиция в рейтинге
    mrr_growth: str
    mrr_growth_value: float


def parse_number_with_k(value: str) -> int:
    """Парсит числа с суффиксом k (тысячи)"""
    if not value:
        return 0
    value = value.strip().upper().replace(',', '').replace('K', '000')
    if value.endswith('000'):
        try:
            return int(value)
        except ValueError:
            return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


async def extract_group_links(page) -> List[dict]:
    """Извлекает ссылки на группы со страницы Games"""
    print("🔗 Извлечение ссылок на группы...")

    links = await page.evaluate('''() => {
        const allLinks = Array.from(document.querySelectorAll('a'));
        const seen = new Set();
        const groupLinks = [];

        allLinks.forEach(a => {
            const href = a.getAttribute('href');
            const text = a.textContent.trim();

            // Пропускаем служебные ссылки
            if (!href || href.includes('/-/') || href.startsWith('http')) {
                return;
            }

            // Ссылки на группы (не профили пользователей с /@)
            if (href.startsWith('/') && href.length > 2 && !href.startsWith('/@')) {
                const fullUrl = 'https://www.skool.com' + href;

                if (!seen.has(fullUrl) && text.length > 2) {
                    seen.add(fullUrl);
                    groupLinks.push({
                        name: text,
                        slug: href.substring(1),
                        url: fullUrl
                    });
                }
            }
        });

        return groupLinks;
    }''')

    print(f"   Найдено {len(links)} групп")
    return links


async def scrape_group_page(page, group_url: str, group_name: str, category: str, position: int, mrr_growth: str, mrr_value: float) -> Optional[GroupInfo]:
    """Парсит страницу группы"""

    try:
        await page.goto(group_url, wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(1500)

        data = await page.evaluate('''() => {
            const result = {
                title: document.title || '',
                description: '',
                members: '0',
                status: '',
                price: '',
                creator: '',
                adminCount: 0,
                onlineCount: '0',
                fullText: ''
            };

            // Описание社区
            const descSelectors = [
                '[class*="description"]',
                '.bio',
                '[class*="about"]',
                'meta[name="description"]'
            ];

            for (const selector of descSelectors) {
                const el = document.querySelector(selector);
                if (el) {
                    result.description = el.textContent?.trim() || el.getAttribute('content') || '';
                    if (result.description) break;
                }
            }

            // Получаем текст для парсинга
            const bodyText = document.body.innerText;

            // Участники - ищем patrones como "105 Members", "191.8k members"
            const membersPatterns = [
                /([\\d\\.]+)(k)?\\s*(members|Members)/i,
                /(\\d+(?:\\.\\d+)?[kK]?)\\s*members/i
            ];

            for (const pattern of membersPatterns) {
                const match = bodyText.match(pattern);
                if (match) {
                    result.members = match[1] + (match[2] || '');
                    break;
                }
            }

            // Статус (Private/Public)
            if (bodyText.includes('Private')) {
                result.status = 'Private';
            } else if (bodyText.includes('Public')) {
                result.status = 'Public';
            }

            // Цена - ищем patrones como "$5", "$99/month"
            const pricePatterns = [
                /\\$(\\d+(?:\\.\\d+)?)/,
                /(\\d+(?:\\.\\d+)?)\\s*\\$/
            ];

            for (const pattern of pricePatterns) {
                const match = bodyText.match(pattern);
                if (match) {
                    // Проверяем что это цена, а не другое число
                    const beforeText = bodyText.substring(Math.max(0, bodyText.indexOf(match[0]) - 20), bodyText.indexOf(match[0]));
                    if (beforeText.includes('$') || beforeText.includes('price') || beforeText.includes('month') || beforeText.includes('/')) {
                        result.price = '$' + match[1];
                        break;
                    }
                }
            }

            // Создатель
            const creatorPatterns = [
                /by\\s+([A-Z][^\\n]{1,40})/i,
                /created\\s+by\\s+([A-Z][^\\n]{1,40})/i
            ];

            for (const pattern of creatorPatterns) {
                const match = bodyText.match(pattern);
                if (match) {
                    result.creator = match[1].trim();
                    break;
                }
            }

            // Админы
            const adminMatch = bodyText.match(/(\\d+)\\s*admin/i);
            if (adminMatch) {
                result.adminCount = parseInt(adminMatch[1]);
            }

            // Онлайн
            const onlinePatterns = [
                /(\\d+(?:\\.\\d+)?[kK]?)\\s*online/i,
                /online\\s*(\\d+(?:\\.\\d+)?[kK]?)/i
            ];

            for (const pattern of onlinePatterns) {
                const match = bodyText.match(pattern);
                if (match) {
                    result.onlineCount = match[1];
                    break;
                }
            }

            // Первые строки для дополнительной информации
            result.fullText = bodyText.split('\\n').slice(0, 30).join('\\n');

            return result;
        }''')

        # Дополнительный поиск описания через meta теги
        if not data['description']:
            desc_meta = await page.query_selector('meta[name="description"]')
            if desc_meta:
                data['description'] = await desc_meta.get_attribute('content') or ''

        # URL создателя
        creator_url = ""
        if data['creator']:
            # Ищем ссылку на создателе
            creator_link = await page.query_selector(f'text="{data["creator"]}"')
            if creator_link:
                href = await creator_link.get_attribute('href')
                if href:
                    creator_url = urljoin('https://www.skool.com', href)

        # Очистка описания от повторяющихся фраз
        description = data['description'][:500] if data['description'] else ''

        group_info = GroupInfo(
            name=group_name,
            slug=group_url.split('/')[-1],
            url=group_url,
            title=data['title'],
            description=description,
            members=data['members'],
            members_count=parse_number_with_k(data['members']),
            status=data['status'],
            price=data['price'],
            price_value=float(data['price'].replace('$', '').replace(',', '')) if data['price'] else 0,
            creator=data['creator'],
            creator_url=creator_url,
            admin_count=data['adminCount'],
            online_count=data['onlineCount'],
            online_count_value=parse_number_with_k(data['onlineCount']),
            category_from_games=category,
            position_in_category=position,
            mrr_growth=mrr_growth,
            mrr_growth_value=mrr_value
        )

        print(f"   ✓ {group_name}: {data['members']} members | {data['price']}")
        return group_info

    except Exception as e:
        print(f"   ✗ Ошибка при парсинге {group_url}: {e}")
        return None


async def parse_enhanced_games():
    """Парсит Games страницы и собирает данные о всех группах"""

    url = "https://www.skool.com/skoolers/-/games"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await context.add_cookies(COOKIES)

        page = await context.new_page()
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Категории
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

        all_groups = []

        for emoji, category in categories_data:
            print(f"\n{'='*60}")
            print(f"📂 Категория: {emoji} {category}")
            print(f"{'='*60}")

            try:
                # Кликаем на категорию
                await page.click(f'text="{emoji} {category}"', timeout=5000)
                await page.wait_for_timeout(2000)

                # Парсим данные с leaderboard
                leaderboard_data = await page.evaluate('''() => {
                    const text = document.body.innerText;
                    const lines = text.split('\\n');
                    const winners = [];

                    let i = 0;
                    while (i < lines.length) {
                        const line = lines[i].trim();

                        if (line.match(/^\\d+$/) && parseInt(line) >= 1 && parseInt(line) <= 100) {
                            const position = parseInt(line);

                            if (i + 3 < lines.length) {
                                const name = lines[i + 1].trim();
                                const community = lines[i + 2].trim();

                                let j = 3;
                                let mrr = '';
                                while (!mrr.startsWith('+$') && j < 8 && i + j < lines.length) {
                                    mrr = lines[i + j].trim();
                                    j++;
                                }

                                if (mrr.startsWith('+$') && name && community) {
                                    winners.push({
                                        position: position,
                                        name: name,
                                        community: community,
                                        mrr_growth: mrr
                                    });
                                }
                            }
                        }
                        i++;
                    }

                    return winners;
                }''')

                print(f"   Найдено {len(leaderboard_data)} участников")

                # Кликаем "See more" если есть для получения больше ссылок
                see_more = await page.query_selector('text="See more"')
                if see_more:
                    print("   Загрузка дополнительных участников...")
                    await see_more.click()
                    await page.wait_for_timeout(2000)

                    # Получаем обновленный leaderboard
                    leaderboard_data = await page.evaluate('''() => {
                        const text = document.body.innerText;
                        const lines = text.split('\\n');
                        const winners = [];

                        let i = 0;
                        while (i < lines.length) {
                            const line = lines[i].trim();

                            if (line.match(/^\\d+$/) && parseInt(line) >= 1 && parseInt(line) <= 100) {
                                const position = parseInt(line);

                                if (i + 3 < lines.length) {
                                    const name = lines[i + 1].trim();
                                    const community = lines[i + 2].trim();

                                    let j = 3;
                                    let mrr = '';
                                    while (!mrr.startsWith('+$') && j < 8 && i + j < lines.length) {
                                        mrr = lines[i + j].trim();
                                        j++;
                                    }

                                    if (mrr.startsWith('+$') && name && community) {
                                        winners.push({
                                            position: position,
                                            name: name,
                                            community: community,
                                            mrr_growth: mrr
                                        });
                                    }
                                }
                            }
                            i++;
                        }

                        return winners;
                    }''')

                # Извлекаем ссылки на группы
                group_links = await extract_group_links(page)

                # Создаем映射 сообщество -> URL
                community_to_url = {}
                for link in group_links:
                    community_to_url[link['name'].lower()] = link['url']

                # Теперь для каждого участника ищем URL группы и парсим страницу
                seen_groups = set()

                for winner in leaderboard_data[:20]:  # Ограничиваем для теста
                    community_name = winner['community']
                    position = winner['position']
                    mrr_growth = winner['mrr_growth']
                    mrr_value = float(mrr_growth.replace('$', '').replace(',', '').replace('+', ''))

                    # Ищем URL группы
                    group_url = None
                    for key, url in community_to_url.items():
                        if community_name.lower() in key or key in community_name.lower():
                            group_url = url
                            break

                    # Если не нашли, пробуем напрямую
                    if not group_url:
                        # Создаем slug из названия
                        slug = community_name.lower().replace(' ', '-').replace('/', '-')
                        group_url = f"https://www.skool.com/{slug}"

                    # Пропускаем если уже парсили эту группу
                    if group_url in seen_groups:
                        continue

                    seen_groups.add(group_url)

                    # Парсим страницу группы
                    group_info = await scrape_group_page(
                        page,
                        group_url,
                        community_name,
                        category,
                        position,
                        mrr_growth,
                        mrr_value
                    )

                    if group_info:
                        all_groups.append(group_info)

                    await page.wait_for_timeout(1000)

            except Exception as e:
                print(f"Ошибка в категории {category}: {e}")
                continue

        await browser.close()

        return all_groups


async def main():
    """Главная функция"""
    print("🚀 Запуск Skool Games Enhanced Parser")
    print("=" * 60)

    groups = await parse_enhanced_games()

    if not groups:
        print("❌ Не удалось собрать данные")
        return

    # Сохраняем результаты
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON
    output_data = {
        "scraped_at": datetime.now().isoformat(),
        "total_groups": len(groups),
        "groups": [asdict(g) for g in groups]
    }

    json_file = f'skool_groups_enhanced_{timestamp}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # CSV
    import csv
    csv_file = f'skool_groups_enhanced_{timestamp}.csv'
    with open(csv_file, 'w', encoding='utf-8', newline='') as f:
        if groups:
            writer = csv.DictWriter(f, fieldnames=groups[0].__dict__.keys())
            writer.writeheader()
            for g in groups:
                writer.writerow(asdict(g))

    # Статистика
    print(f"\n{'='*60}")
    print("✅ Парсинг завершен!")
    print(f"{'='*60}")
    print(f"📊 Всего групп: {len(groups)}")

    # По категориям
    from collections import Counter
    by_cat = Counter(g.category_from_games for g in groups)
    for cat, count in sorted(by_cat.items()):
        emoji = next((e for e, c in [("🎨", "Hobbies"), ("🎸", "Music"), ("💰", "Money"), ("🙏", "Spirituality"), ("💻", "Tech"), ("🥕", "Health"), ("⚽", "Sports"), ("📚", "Self-improvement"), ("❤️", "Relationships")] if c == cat), "")
        print(f"   {emoji} {cat}: {count}")

    total_members = sum(g.members_count for g in groups)
    total_mrr = sum(g.mrr_growth_value for g in groups)

    print(f"\n👥 Всего участников: {total_members:,}")
    print(f"💰 Общий MRR рост: ${total_mrr:,.0f}")

    # Средняя цена
    priced_groups = [g for g in groups if g.price_value > 0]
    if priced_groups:
        avg_price = sum(g.price_value for g in priced_groups) / len(priced_groups)
        print(f"💵 Средняя цена: ${avg_price:.2f}")

    print(f"\n💾 Сохранено:")
    print(f"   📄 {json_file}")
    print(f"   📊 {csv_file}")


if __name__ == "__main__":
    asyncio.run(main())
