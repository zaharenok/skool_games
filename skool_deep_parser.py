#!/usr/bin/env python3
"""
Skool Games Deep Parser - Полный парсер с картинками и markdown
"""
import asyncio
import json
import re
import os
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from dataclasses import dataclass, asdict
from typing import List, Optional
from urllib.parse import urljoin
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
class GroupDeepInfo:
    """Полная информация о группе"""
    # Leaderboard
    position: int
    category: str
    category_emoji: str
    mrr_growth: str
    mrr_growth_value: float

    # Main info
    name: str
    slug: str
    url: str
    about_url: str

    # About page content
    about_description: str
    about_full_text: str

    # Stats
    members: str
    members_count: int
    online: str
    online_count: int
    admins_count: int

    # Pricing
    price_display: str
    price_value: float
    is_free: bool
    trial_available: bool

    # Status
    is_public: bool
    status_text: str

    # Creator
    creator_name: str
    creator_url: str

    # Media
    cover_image_url: str
    cover_image_base64: str
    logo_url: str

    # Additional
    tags: List[str]
    features: List[str]

    # Markdown
    markdown_content: str

    # Metadata
    scraped_at: str


def sanitize_filename(name: str) -> str:
    """Очистка имени для файла"""
    name = name.replace('/', '-').replace('\\', '-')
    name = re.sub(r'[<>:"|?*]', '', name)
    name = name.replace(' ', '_')
    return name[:100]


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


def extract_features(text: str) -> List[str]:
    """Извлекает список фич из текста"""
    features = []
    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        # Ищем bullet points
        if line.startswith(('•', '-', '*', '✅', '🚀', '📚', '🎓')):
            feature = line.lstrip('•-*✅🚀📚🎓').strip()
            if feature and len(feature) > 5 and len(feature) < 200:
                features.append(feature)

    return features[:20]  # Максимум 20 фич


def create_markdown(group: 'GroupDeepInfo') -> str:
    """Создает markdown файл для группы"""
    md = f"""# {group.category_emoji} {group.name}

**Position:** #{group.position} in {group.category}
**MRR Growth:** {group.mrr_growth}
**URL:** [{group.url}]({group.url})

---

## 📊 Statistics

| Metric | Value |
|--------|-------|
| **Members** | {group.members} |
| **Online** | {group.online} |
| **Admins** | {group.admins_count} |
| **Price** | {group.price_display} |
| **Type** | {'Public' if group.is_public else 'Private'} |

---

## 👤 Creator

**Name:** {group.creator_name or 'N/A'}
**Profile:** [{group.creator_url or 'N/A'}]({group.creator_url or '#'})

---

## 📝 Description

{group.about_description or group.about_full_text[:500] + '...' if group.about_full_text else 'No description available'}

"""

    if group.features:
        md += "\n## ✨ Features\n\n"
        for feature in group.features:
            md += f"- {feature}\n"
        md += "\n"

    if group.cover_image_url:
        md += f"\n## 🖼 Cover Image\n\n![{group.name}]({group.cover_image_url})\n\n"

    md += f"""
---

## 📄 Full About Text

{group.about_full_text}

---

**Scraped:** {group.scraped_at}
**Source:** Skool Games Parser
"""

    return md


async def download_image(page, url: str, output_path: str) -> bool:
    """Скачивает картинку"""
    try:
        response = await page.request.get(url)
        if response.status == 200:
            content = await response.body()
            with open(output_path, 'wb') as f:
                f.write(content)
            return True
    except Exception as e:
        print(f"         ⚠ Image download error: {e}")
    return False


async def scrape_group_deep(page, group_url: str, position: int, category: str, emoji: str, mrr_growth: str, mrr_value: float, output_dir: Path) -> Optional[GroupDeepInfo]:
    """Глубокий парсинг группы"""

    about_url = f"{group_url}/about"
    slug = group_url.split('/')[-1]

    try:
        # Main page
        await page.goto(group_url, timeout=15000)
        await page.wait_for_timeout(1500)

        # About page
        await page.goto(about_url, timeout=15000)
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
                hasTrial: false,
                isPublic: false,
                creator: '',
                coverImage: '',
                logo: '',
                slug: window.location.pathname.split('/').filter(Boolean).pop() || ''
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

            if (bodyText.includes('Free trial') || bodyText.includes('trial')) {
                result.hasTrial = true;
            }

            if (bodyText.includes('Public')) {
                result.isPublic = true;
            }

            // Price extraction
            const pricePatterns = [
                /\\$([\\d\\.]+)\\s*\\/\\s*month/i,
                /\\$([\\d\\.]+)\\s*per\\s*month/i,
                /JOIN\\s*\\$([\\d\\.]+)/i,
                /price.*?\\$([\\d\\.]+)/i
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

        # Creator URL
        creator_url = ""
        if data['creator']:
            try:
                # Кликаем на имя создателя для получения URL
                creator_elements = await page.query_selector_all(f'text="{data["creator"]}"')
                for el in creator_elements:
                    href = await el.get_attribute('href')
                    if href and '/@' in href:
                        creator_url = urljoin('https://www.skool.com', href)
                        break
            except:
                pass

        # Features
        features = extract_features(data['fullText'])

        # Cover image base64
        cover_base64 = ""
        cover_filename = ""
        if data['coverImage']:
            try:
                response = await page.request.get(data['coverImage'])
                if response.status == 200:
                    content = await response.body()
                    cover_base64 = base64.b64encode(content).decode('utf-8')

                    # Save image
                    images_dir = output_dir / 'images'
                    images_dir.mkdir(exist_ok=True)
                    safe_name = sanitize_filename(data['title'])
                    ext = data['coverImage'].split('.')[-1].split('?')[0]
                    cover_filename = f"{safe_name}_cover.{ext}"
                    cover_path = images_dir / cover_filename

                    with open(cover_path, 'wb') as f:
                        f.write(content)
                    print(f"         📸 Saved: {cover_filename}")
            except Exception as e:
                print(f"         ⚠ Cover save error: {e}")

        # Create group info
        group_info = GroupDeepInfo(
            position=position,
            category=category,
            category_emoji=emoji,
            mrr_growth=mrr_growth,
            mrr_growth_value=mrr_value,
            name=data['title'],
            slug=data['slug'],
            url=group_url,
            about_url=about_url,
            about_description=data['description'] or '',
            about_full_text=data['fullText'],
            members=data['members'],
            members_count=parse_number(data['members']),
            online=data['online'],
            online_count=parse_number(data['online']),
            admins_count=data['admins'],
            price_display=data['price'] or ('Free' if data['isFree'] else 'N/A'),
            price_value=float(data['price'].replace('$', '')) if data['price'] and not data['isFree'] else 0,
            is_free=data['isFree'],
            trial_available=data['hasTrial'],
            is_public=data['isPublic'],
            status_text='Public' if data['isPublic'] else 'Private',
            creator_name=data['creator'],
            creator_url=creator_url,
            cover_image_url=data['coverImage'],
            cover_image_base64=cover_base64,
            logo_url='',
            tags=[],
            features=features,
            markdown_content='',  # Will be set below
            scraped_at=datetime.now().isoformat()
        )

        # Create markdown
        group_info.markdown_content = create_markdown(group_info)

        # Save markdown
        md_dir = output_dir / 'markdown'
        md_dir.mkdir(exist_ok=True)
        safe_name = sanitize_filename(data['title'])
        md_path = md_dir / f"{safe_name}.md"

        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(group_info.markdown_content)
        print(f"         📝 Saved: {safe_name}.md")

        return group_info

    except Exception as e:
        print(f"         ✗ Error: {e}")
        return None


async def parse_deep():
    """Глубокий парсинг всех групп"""

    url = "https://www.skool.com/skoolers/-/games"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"skool_data_{timestamp}")
    output_dir.mkdir(exist_ok=True)

    print(f"📁 Output directory: {output_dir}")

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
                await page.goto(url, wait_until="networkidle")
                await page.wait_for_timeout(2000)

                await page.click(f'text="{emoji} {category}"', timeout=5000)
                await page.wait_for_timeout(2000)

                # See more
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

                # Scrape groups
                for winner in leaderboard[:10]:  # Limit for speed
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

                    group_info = await scrape_group_deep(
                        page, group_url, position, category, emoji, mrr, mrr_value, output_dir
                    )

                    if group_info:
                        all_groups.append(group_info)

                    await page.wait_for_timeout(1500)

            except Exception as e:
                print(f"   Error: {e}")
                continue

        await browser.close()

        # Save JSON
        output_data = {
            "scraped_at": datetime.now().isoformat(),
            "total_groups": len(all_groups),
            "output_directory": str(output_dir),
            "groups": [asdict(g) for g in all_groups]
        }

        json_file = output_dir / f"skool_deep_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        # Create index markdown
        index_md = f"# Skool Games Deep Data\n\n"
        index_md += f"**Scraped:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        index_md += f"**Groups:** {len(all_groups)}\n\n"
        index_md += "## All Groups\n\n"

        for g in all_groups:
            index_md += f"- [{g.category_emoji} {g.name}]({g.url}) - #{g.position} in {g.category}\n"
            index_md += f"  - {g.members} members | {g.price_display} | {g.mrr_growth}\n\n"

        with open(output_dir / "INDEX.md", 'w', encoding='utf-8') as f:
            f.write(index_md)

        print(f"\n{'='*70}")
        print("✅ DONE!")
        print(f"{'='*70}")
        print(f"📁 Directory: {output_dir}")
        print(f"📊 Groups: {len(all_groups)}")
        print(f"📝 Markdown: {output_dir / 'markdown'}")
        print(f"🖼 Images: {output_dir / 'images'}")
        print(f"📄 JSON: {json_file}")
        print(f"📋 Index: {output_dir / 'INDEX.md'}")

        return all_groups


if __name__ == "__main__":
    asyncio.run(parse_deep())
