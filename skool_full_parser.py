#!/usr/bin/env python3
"""
Skool Games Full Parser - Парсер с ссылками и About страницами
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
]


@dataclass
class GroupFullInfo:
    """Полная информация о группе"""
    # Из leaderboard
    position: int
    category: str
    category_emoji: str
    mrr_growth: str
    mrr_growth_value: float

    # Основная информация
    name: str
    slug: str
    url: str

    # About страница
    about_title: str
    about_description: str
    about_full_text: str

    # Статистика группы
    members: str
    members_count: int
    online: str
    online_count: int

    # Информация о цене
    price_display: str
    price_value: float
    is_free: bool

    # Создатель
    creator_name: str
    creator_url: str

    # Метаданные
    scraped_at: str


def parse_number(value: str) -> int:
    """Парсит число с суффиксом k"""
    if not value:
        return 0
    value = value.strip().upper().replace(',', '')
    if 'K' in value:
        return int(float(value.replace('K', '')) * 1000)
    try:
        return int(float(value))
    except ValueError:
        return 0


async def scrape_about_page(page, group_slug: str, group_url: str) -> dict:
    """Парсит About страницу группы"""
    about_url = f"{group_url}/about"

    try:
        await page.goto(about_url, timeout=15000)
        await page.wait_for_timeout(1500)

        data = await page.evaluate('''() => {
            const result = {
                title: document.title || '',
                description: '',
                fullText: document.body.innerText
            };

            // Ищем описание в разных местах
            const selectors = [
                '[class*="description"]',
                '[class*="about"]',
                '[class*="bio"]',
                'meta[name="description"]',
                'section',
                'article'
            ];

            for (const selector of selectors) {
                const els = document.querySelectorAll(selector);
                for (const el of els) {
                    const text = el.textContent?.trim() || el.getAttribute('content') || '';
                    if (text && text.length > 50 && text.length < 2000) {
                        result.description = text;
                        break;
                    }
                }
                if (result.description) break;
            }

            return result;
        }''')

        return {
            'about_title': data['title'],
            'about_description': data['description'] or '',
            'about_full_text': data['fullText'][:5000] if data['fullText'] else ''
        }

    except Exception as e:
        print(f"      ⚠ About page error: {e}")
        return {
            'about_title': '',
            'about_description': '',
            'about_full_text': ''
        }


async def scrape_group_main(page, group_url: str, position: int, category: str, emoji: str, mrr_growth: str, mrr_value: float) -> Optional[GroupFullInfo]:
    """Парсит основную страницу группы"""

    try:
        await page.goto(group_url, timeout=15000)
        await page.wait_for_timeout(1500)

        data = await page.evaluate('''() => {
            const result = {
                title: document.title || '',
                members: '0',
                online: '0',
                price: '',
                isFree: false,
                creator: '',
                description: '',
                slug: ''
            };

            // Получаем slug из URL
            result.slug = window.location.pathname.split('/').pop();

            // Парсим текст страницы
            const bodyText = document.body.innerText;

            // Участники
            const membersMatch = bodyText.match(/([\\d\\.]+)(k)?\\s*(members|Members)/i);
            if (membersMatch) {
                result.members = membersMatch[1] + (membersMatch[2] || '');
            }

            // Онлайн
            const onlineMatch = bodyText.match(/(\\d+(?:\\.\\d+)?[kK]?)\\s*online/i);
            if (onlineMatch) {
                result.online = onlineMatch[1];
            }

            // Цена - ищем patrones
            if (bodyText.includes('Free') || bodyText.includes('Бесплатно')) {
                result.isFree = true;
                result.price = 'Free';
            } else {
                const priceMatch = bodyText.match(/\\$([\\d\\.]+)/);
                if (priceMatch) {
                    result.price = '$' + priceMatch[1];
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

            // Описание (meta)
            const metaDesc = document.querySelector('meta[name="description"]');
            if (metaDesc) {
                result.description = metaDesc.getAttribute('content') || '';
            }

            return result;
        }''')

        # Дополнительный поиск создателя через ссылки
        creator_url = ""
        if data['creator']:
            try:
                creator_link = await page.query_selector(f'text="{data["creator"]}"')
                if creator_link:
                    href = await creator_link.get_attribute('href')
                    if href and '/@' in href:
                        creator_url = urljoin('https://www.skool.com', href)
            except:
                pass

        # About страница
        print(f"      📄 Scraping About page...")
        about_data = await scrape_about_page(page, data['slug'], group_url)

        group_info = GroupFullInfo(
            position=position,
            category=category,
            category_emoji=emoji,
            mrr_growth=mrr_growth,
            mrr_growth_value=mrr_value,
            name=data['title'],
            slug=data['slug'],
            url=group_url,
            about_title=about_data['about_title'],
            about_description=about_data['about_description'],
            about_full_text=about_data['about_full_text'],
            members=data['members'],
            members_count=parse_number(data['members']),
            online=data['online'],
            online_count=parse_number(data['online']),
            price_display=data['price'] or 'N/A',
            price_value=float(data['price'].replace('$', '')) if data['price'] and data['price'] != 'Free' else 0,
            is_free=data['isFree'] or data['price'] == 'Free',
            creator_name=data['creator'],
            creator_url=creator_url,
            scraped_at=datetime.now().isoformat()
        )

        print(f"      ✓ {data['title']}: {data['members']} members | {data['price']}")
        return group_info

    except Exception as e:
        print(f"      ✗ Error: {e}")
        return None


async def parse_games_full():
    """Парсит Games и собирает полные данные о группах"""

    url = "https://www.skool.com/skoolers/-/games"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await context.add_cookies(COOKIES)

        page = await context.new_page()
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(3000)

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
        seen_urls = set()

        for emoji, category in categories_data:
            print(f"\n{'='*70}")
            print(f"📂 Категория: {emoji} {category}")
            print(f"{'='*70}")

            try:
                # Возвращаемся на games страницу
                await page.goto(url, wait_until="networkidle")
                await page.wait_for_timeout(2000)

                await page.click(f'text="{emoji} {category}"', timeout=5000)
                await page.wait_for_timeout(2000)

                # Click "See more" для получения полного списка
                see_more = await page.query_selector('text="See more"')
                if see_more:
                    await see_more.click()
                    await page.wait_for_timeout(2000)

                # Extract links to groups
                group_links = await page.evaluate('''() => {
                    const links = Array.from(document.querySelectorAll('a'));
                    const seen = new Set();
                    const result = [];

                    links.forEach(a => {
                        const href = a.getAttribute('href');
                        const text = a.textContent.trim();

                        if (!href || href.includes('/-/') || href.startsWith('http') || href.startsWith('/@')) {
                            return;
                        }

                        if (href.startsWith('/') && href.length > 2 && text.length > 2) {
                            const fullUrl = 'https://www.skool.com' + href;
                            if (!seen.has(fullUrl)) {
                                seen.add(fullUrl);
                                result.push({
                                    name: text,
                                    url: fullUrl
                                });
                            }
                        }
                    });

                    return result;
                }''')

                print(f"   Found {len(group_links)} group links")

                # Parse leaderboard
                leaderboard = await page.evaluate('''() => {
                    const text = document.body.innerText;
                    const lines = text.split('\\n');
                    const winners = [];

                    for (let i = 0; i < lines.length; i++) {
                        const line = lines[i].trim();

                        if (line.match(/^\\d+$/) && parseInt(line) >= 1 && parseInt(line) <= 100) {
                            const position = parseInt(line);

                            if (i + 3 < lines.length) {
                                const name = lines[i + 1].trim();
                                const community = lines[i + 2].trim();

                                let j = 3;
                                let mrr = '';
                                while (j < 8 && i + j < lines.length && !mrr.startsWith('+$')) {
                                    mrr = lines[i + j].trim();
                                    j++;
                                }

                                if (mrr.startsWith('+$') && name && community) {
                                    winners.push({
                                        position: position,
                                        name: name,
                                        community: community,
                                        mrr: mrr
                                    });
                                }
                            }
                        }
                    }

                    return winners;
                }''')

                print(f"   Found {len(leaderboard)} winners")

                # Create mapping community name -> URL
                name_to_url = {}
                for link in group_links:
                    name_to_url[link['name'].lower()] = link['url']

                # Scrape each group
                for winner in leaderboard[:15]:  # Limit for demo
                    community = winner['community']
                    position = winner['position']
                    mrr = winner['mrr']
                    mrr_value = float(mrr.replace('$', '').replace(',', '').replace('+', ''))

                    # Find URL
                    group_url = None
                    for key, url in name_to_url.items():
                        if community.lower() in key or key in community.lower():
                            group_url = url
                            break

                    # Fallback: construct URL
                    if not group_url:
                        slug = community.lower().replace(' ', '-').replace('/', '-').replace('?', '')
                        group_url = f"https://www.skool.com/{slug}"

                    if group_url in seen_urls:
                        continue
                    seen_urls.add(group_url)

                    print(f"   [{position}] {community}")
                    group_info = await scrape_group_main(page, group_url, position, category, emoji, mrr, mrr_value)

                    if group_info:
                        all_groups.append(group_info)

                    await page.wait_for_timeout(1000)

            except Exception as e:
                print(f"   Error in {category}: {e}")
                continue

        await browser.close()
        return all_groups


async def main():
    print("🚀 Skool Games Full Parser")
    print("=" * 70)
    print("Collecting: links + about pages + full info")
    print("=" * 70)

    groups = await parse_games_full()

    if not groups:
        print("❌ No data collected")
        return

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output = {
        "scraped_at": datetime.now().isoformat(),
        "total_groups": len(groups),
        "groups": [asdict(g) for g in groups]
    }

    json_file = f'skool_full_{timestamp}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # CSV with key fields
    import csv
    csv_file = f'skool_full_{timestamp}.csv'
    fieldnames = ['position', 'category', 'name', 'url', 'members', 'price_display', 'creator_name', 'mrr_growth', 'about_description']

    with open(csv_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for g in groups:
            writer.writerow(asdict(g))

    # Stats
    print(f"\n{'='*70}")
    print("✅ DONE!")
    print(f"{'='*70}")
    print(f"📊 Groups: {len(groups)}")
    print(f"📄 {json_file}")
    print(f"📊 {csv_file}")

    # Show sample
    if groups:
        g = groups[0]
        print(f"\n📋 Sample:")
        print(f"   Name: {g.name}")
        print(f"   URL: {g.url}")
        print(f"   About: {g.about_description[:100]}...")


if __name__ == "__main__":
    asyncio.run(main())
