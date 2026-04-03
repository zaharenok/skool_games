#!/usr/bin/env python3
"""
Skool Games All Categories Parser - Собирает все категории и About страницы
Сначала использует базовый парсер для всех категорий, затем собирает About для каждой группы
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from dataclasses import dataclass, asdict
from typing import List, Optional
import base64

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
class GroupInfo:
    """Информация о группе"""
    position: int
    category: str
    category_emoji: str
    mrr_growth: str
    mrr_growth_value: float
    name: str
    slug: str
    url: str
    about_url: str
    about_description: str
    about_full_text: str
    members: str
    members_count: int
    online: str
    online_count: int
    price_display: str
    price_value: float
    is_free: bool
    is_public: bool
    creator_name: str
    creator_url: str
    cover_image_url: str
    cover_image_base64: str
    features: List[str]
    scraped_at: str


def parse_number(value: str) -> int:
    if not value:
        return 0
    value = value.strip().upper().replace(',', '')
    if 'K' in value:
        return int(float(value.replace('K', '')) * 1000)
    try:
        return int(float(value))
    except ValueError:
        return 0


def extract_features(text: str) -> List[str]:
    features = []
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith(('•', '-', '*', '✅', '🚀', '📚', '🎓', '✓')):
            feature = line.lstrip('•-*✅🚀📚🎓✓').strip()
            if feature and len(feature) > 5 and len(feature) < 200:
                features.append(feature)
    return features[:20]


async def scrape_about_page(page, group_url: str) -> dict:
    """Парсит About страницу группы"""
    about_url = f"{group_url}/about"

    try:
        await page.goto(about_url, timeout=20000)
        await page.wait_for_timeout(2000)

        data = await page.evaluate('''() => {
            const result = {
                title: document.title || '',
                description: '',
                fullText: document.body.innerText,
                members: '0',
                online: '0',
                admins: 0,
                price: '',
                isFree: false,
                isPublic: false,
                creator: '',
                coverImage: ''
            };

            // Meta description
            const metaDesc = document.querySelector('meta[name="description"]');
            if (metaDesc) {
                result.description = metaDesc.getAttribute('content') || '';
            }

            // OG images
            const ogImage = document.querySelector('meta[property="og:image"]');
            if (ogImage) {
                result.coverImage = ogImage.getAttribute('content') || '';
            }

            // Parse body text
            const bodyText = document.body.innerText;

            // Members
            const membersMatch = bodyText.match(/([\\d\\.]+)(k)?\\s*(members|Members)/i);
            if (membersMatch) {
                result.members = membersMatch[1] + (membersMatch[2] || '');
            }

            // Online
            const onlineMatch = bodyText.match(/(\\d+(?:\\.\\d+)?[kK]?)\\s*online/i);
            if (onlineMatch) {
                result.online = onlineMatch[1];
            }

            // Admins
            const adminMatch = bodyText.match(/(\\d+)\\s*admin/i);
            if (adminMatch) {
                result.admins = parseInt(adminMatch[1]);
            }

            // Price and status
            if (bodyText.includes('Free') || bodyText.includes('Free trial')) {
                result.isFree = true;
            }

            if (bodyText.includes('Public')) {
                result.isPublic = true;
            }

            // Price extraction
            const pricePatterns = [
                /\\$([\\d\\.]+)\\s*\\/\\s*month/i,
                /JOIN\\s*\\$([\\d\\.]+)/i
            ];

            for (const pattern of pricePatterns) {
                const match = bodyText.match(pattern);
                if (match) {
                    result.price = '$' + match[1];
                    break;
                }
            }

            // Creator
            const creatorPatterns = [
                /by\\s+([A-Z][^\\n]{1,40})/i,
                /created\\s+by\\s+([A-Z][^\\n]{1,40})/i
            ];

            for (const pattern of creatorPatterns) {
                const match = bodyText.match(pattern);
                if (match && match[1].length < 40) {
                    result.creator = match[1].trim();
                    break;
                }
            }

            return result;
        }''')

        return data

    except Exception as e:
        print(f"         ⚠ About page error: {e}")
        return {}


async def scrape_group(page, group_url: str, position: int, category: str, emoji: str, mrr_growth: str, mrr_value: float, output_dir: Path) -> Optional[GroupInfo]:
    """Парсит группу"""

    try:
        # Get About page data
        about_data = await scrape_about_page(page, group_url)

        if not about_data:
            return None

        # Cover image base64
        cover_base64 = ""
        if about_data.get('coverImage'):
            try:
                response = await page.request.get(about_data['coverImage'])
                if response.status == 200:
                    content = await response.body()
                    cover_base64 = base64.b64encode(content).decode('utf-8')

                    # Save image
                    images_dir = output_dir / 'images'
                    images_dir.mkdir(exist_ok=True)
                    safe_name = re.sub(r'[<>:"|?*\\/]', '_', about_data['title'])
                    safe_name = safe_name.replace(' ', '_')[:100]
                    ext = about_data['coverImage'].split('.')[-1].split('?')[0]
                    if ext.lower() not in ['png', 'jpg', 'jpeg', 'webp']:
                        ext = 'png'
                    cover_filename = f"{safe_name}_cover.{ext}"
                    cover_path = images_dir / cover_filename

                    with open(cover_path, 'wb') as f:
                        f.write(content)
                    print(f"         📸 {cover_filename}")
            except Exception as e:
                print(f"         ⚠ Image error: {e}")

        # Features
        features = extract_features(about_data.get('fullText', ''))

        # Creator URL
        creator_url = ""
        if about_data.get('creator'):
            # Try to find creator link
            try:
                await page.goto(f"{group_url}/about", timeout=10000)
                creator_links = await page.query_selector_all('a')
                for link in creator_links:
                    text = await link.text_content()
                    href = await link.get_attribute('href')
                    if text and about_data['creator'] in text and href and '/@' in href:
                        creator_url = href if href.startswith('http') else f"https://www.skool.com{href}"
                        break
            except:
                pass

        group_info = GroupInfo(
            position=position,
            category=category,
            category_emoji=emoji,
            mrr_growth=mrr_growth,
            mrr_growth_value=mrr_value,
            name=about_data.get('title', ''),
            slug=group_url.split('/')[-1],
            url=group_url,
            about_url=f"{group_url}/about",
            about_description=about_data.get('description', ''),
            about_full_text=about_data.get('fullText', ''),
            members=about_data.get('members', '0'),
            members_count=parse_number(about_data.get('members', '0')),
            online=about_data.get('online', '0'),
            online_count=parse_number(about_data.get('online', '0')),
            price_display=about_data.get('price', '') or ('Free' if about_data.get('isFree') else 'N/A'),
            price_value=float(about_data.get('price', '').replace('$', '')) if about_data.get('price') and not about_data.get('isFree') else 0,
            is_free=about_data.get('isFree', False),
            is_public=about_data.get('isPublic', False),
            creator_name=about_data.get('creator', ''),
            creator_url=creator_url,
            cover_image_url=about_data.get('coverImage', ''),
            cover_image_base64=cover_base64,
            features=features,
            scraped_at=datetime.now().isoformat()
        )

        print(f"         ✓ {group_info.name}: {group_info.members} members | {group_info.price_display}")

        return group_info

    except Exception as e:
        print(f"         ✗ Error: {e}")
        return None


async def main():
    """Главная функция"""

    # Сначала запускаем базовый парсер для получения всех групп по всем категориям
    print("🚀 Шаг 1: Получаем список всех групп через базовый парсер...")

    # Импортируем базовый парсер
    import sys
    sys.path.insert(0, str(Path(__file__).parent))

    # Запускаем базовый парсер
    from skool_parser import parse_all_categories, COOKIES

    url = "https://www.skool.com/skoolers/-/games"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"skool_data_{timestamp}")
    output_dir.mkdir(exist_ok=True)

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
            print(f"📂 {emoji} {category}")
            print(f"{'='*70}")

            try:
                # Reload page for each category
                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)

                # Try to click category
                clicked = False
                for attempt in range(3):
                    try:
                        # Try clicking just the category name
                        await page.click(f'text="{category}"', timeout=5000)
                        clicked = True
                        await page.wait_for_timeout(2000)
                        break
                    except:
                        await page.wait_for_timeout(1000)

                if not clicked:
                    print(f"   ⚠ Could not click {category}, skipping...")
                    continue

                # Click See more if exists
                see_more = await page.query_selector('text="See more"')
                if see_more:
                    await see_more.click()
                    await page.wait_for_timeout(2000)

                # Get leaderboard
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
                                    winners.push({position, name, community, mrr});
                                }
                            }
                        }
                    }
                    return winners;
                }''')

                print(f"   Found {len(leaderboard)} winners")

                # Get group links
                group_links = await page.evaluate('''() => {
                    const links = Array.from(document.querySelectorAll('a'));
                    const seen = new Set();
                    const result = [];
                    links.forEach(a => {
                        const href = a.getAttribute('href');
                        const text = a.textContent.trim();
                        if (!href || href.includes('/-/') || href.startsWith('http') || href.startsWith('/@')) return;
                        if (href.startsWith('/') && href.length > 2 && text.length > 2) {
                            const fullUrl = 'https://www.skool.com' + href;
                            if (!seen.has(fullUrl)) {
                                seen.add(fullUrl);
                                result.push({name: text, url: fullUrl});
                            }
                        }
                    });
                    return result;
                }''')

                name_to_url = {link['name'].lower(): link['url'] for link in group_links}

                # Scrape each group's About page
                for winner in leaderboard[:20]:  # Limit to 20 per category for speed
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

                    if not group_url:
                        slug = community.lower().replace(' ', '-').replace('/', '-')
                        group_url = f"https://www.skool.com/{slug}"

                    if group_url in seen_urls:
                        continue
                    seen_urls.add(group_url)

                    print(f"   [{position}] {community}")

                    group_info = await scrape_group(
                        page, group_url, position, category, emoji, mrr, mrr_value, output_dir
                    )

                    if group_info:
                        all_groups.append(group_info)

                    await page.wait_for_timeout(1500)

            except Exception as e:
                print(f"   Error in {category}: {e}")
                continue

        await browser.close()

        # Save results
        output_data = {
            "scraped_at": datetime.now().isoformat(),
            "total_groups": len(all_groups),
            "categories": sorted(list(set([g['category'] for g in all_groups]))),
            "groups": [asdict(g) for g in all_groups]
        }

        json_file = output_dir / f"skool_all_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*70}")
        print("✅ DONE!")
        print(f"{'='*70}")
        print(f"📁 Directory: {output_dir}")
        print(f"📊 Groups: {len(all_groups)}")
        print(f"📂 Categories: {output_data['categories']}")
        print(f"📄 JSON: {json_file}")

        return all_groups


if __name__ == "__main__":
    asyncio.run(main())
