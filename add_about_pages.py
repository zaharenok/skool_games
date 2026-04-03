#!/usr/bin/env python3
"""
Добавляет About страницы к данным базового парсера
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
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


async def add_about_to_basic_data():
    """Добавляет About страницы к данным из базового парсера"""

    # Находим последний JSON от базового парсера
    json_files = list(Path('.').glob('skool_games_*.json'))
    if not json_files:
        print("❌ Не найден файл skool_games_*.json")
        return

    latest_json = max(json_files, key=lambda p: p.stat().st_mtime)
    print(f"📄 Использую: {latest_json}")

    with open(latest_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"skool_data_{timestamp}")
    output_dir.mkdir(exist_ok=True)

    images_dir = output_dir / 'images'
    images_dir.mkdir(exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await context.add_cookies(COOKIES)

        page = await context.new_page()

        all_groups_enhanced = []

        # Проходим по всем категориям и группам
        for cat in data['categories']:
            category_name = cat['name']
            category_emoji = cat['emoji']

            print(f"\n{'='*70}")
            print(f"📂 {category_emoji} {category_name}")
            print(f"{'='*70}")

            for winner in cat['winners']:
                community = winner['community']
                position = winner['position']
                mrr_growth = winner['mrr_growth']
                mrr_value = winner['mrr_growth_value']

                # Build URL
                slug = community.lower().replace(' ', '-').replace('/', '-').replace('?', '').replace('!', '').replace('(', '').replace(')', '')
                group_url = f"https://www.skool.com/{slug}"

                print(f"   [{position}] {community}")
                print(f"      URL: {group_url}")

                try:
                    # Go to About page
                    about_url = f"{group_url}/about"
                    await page.goto(about_url, timeout=15000)
                    await page.wait_for_timeout(1500)

                    # Scrape data
                    group_data = await page.evaluate('''() => {
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

                        // OG image
                        const ogImage = document.querySelector('meta[property="og:image"]');
                        if (ogImage) {
                            result.coverImage = ogImage.getAttribute('content') || '';
                        }

                        const bodyText = result.fullText;

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

                        // Price
                        if (bodyText.includes('Free')) {
                            result.isFree = true;
                            result.price = 'Free';
                        }

                        const priceMatch = bodyText.match(/\\$([\\d\\.]+)\\s*\\/\\s*month/i);
                        if (priceMatch) {
                            result.price = '$' + priceMatch[1];
                        }

                        // Public
                        if (bodyText.includes('Public')) {
                            result.isPublic = true;
                        }

                        // Creator
                        const creatorMatch = bodyText.match(/by\\s+([A-Z][^\\n]{1,40})/i);
                        if (creatorMatch) {
                            result.creator = creatorMatch[1].trim();
                        }

                        return result;
                    }''')

                    # Download cover image
                    cover_base64 = ""
                    if group_data['coverImage']:
                        try:
                            safe_name = re.sub(r'[<>:"|?*\\/]', '_', group_data['title'])
                            safe_name = safe_name.replace(' ', '_')[:100]
                            ext = group_data['coverImage'].split('.')[-1].split('?')[0]
                            if ext.lower() not in ['png', 'jpg', 'jpeg', 'webp']:
                                ext = 'png'

                            cover_filename = f"{safe_name}_cover.{ext}"
                            cover_path = images_dir / cover_filename

                            # Download and save
                            response = await page.request.get(group_data['coverImage'])
                            if response.status == 200:
                                content = await response.body()
                                with open(cover_path, 'wb') as f:
                                    f.write(content)
                                cover_base64 = base64.b64encode(content).decode('utf-8')
                                print(f"         📸 {cover_filename}")
                        except Exception as e:
                            print(f"         ⚠ Image error: {e}")

                    # Extract features
                    features = []
                    lines = group_data['fullText'].split('\n')
                    for line in lines:
                        line = line.strip()
                        if line.startswith(('•', '-', '*', '✅', '🚀', '📚', '🎓')):
                            feature = line.lstrip('•-*✅🚀📚🎓').strip()
                            if feature and 5 < len(feature) < 200:
                                features.append(feature)
                    features = features[:15]

                    # Create enhanced group data
                    enhanced_group = {
                        **winner,
                        'url': group_url,
                        'about_url': about_url,
                        'about_title': group_data['title'],
                        'about_description': group_data['description'],
                        'about_full_text': group_data['fullText'],
                        'members': group_data['members'],
                        'members_count': int(group_data['members'].replace('K', '000').replace(',', '')) if group_data['members'] != '0' else 0,
                        'online': group_data['online'],
                        'online_count': int(group_data['online'].replace('K', '000').replace(',', '')) if group_data['online'] != '0' else 0,
                        'price_display': group_data['price'] or 'N/A',
                        'price_value': float(group_data['price'].replace('$', '')) if group_data['price'] and group_data['price'] != 'Free' else 0,
                        'is_free': group_data['isFree'],
                        'is_public': group_data['isPublic'],
                        'creator_name': group_data['creator'],
                        'creator_url': '',
                        'cover_image_url': group_data['coverImage'],
                        'cover_image_base64': cover_base64,
                        'features': features,
                        'scraped_at': datetime.now().isoformat()
                    }

                    all_groups_enhanced.append(enhanced_group)
                    print(f"         ✓ {group_data['title']}: {group_data['members']} members | {group_data['price']}")

                except Exception as e:
                    print(f"         ✗ Error: {e}")
                    # Add original data without about info
                    enhanced_group = {
                        **winner,
                        'url': group_url,
                        'about_url': about_url,
                        'about_title': community,
                        'about_description': '',
                        'about_full_text': '',
                        'members': '0',
                        'members_count': 0,
                        'online': '0',
                        'online_count': 0,
                        'price_display': 'N/A',
                        'price_value': 0,
                        'is_free': False,
                        'is_public': False,
                        'creator_name': '',
                        'creator_url': '',
                        'cover_image_url': '',
                        'cover_image_base64': '',
                        'features': [],
                        'scraped_at': datetime.now().isoformat()
                    }
                    all_groups_enhanced.append(enhanced_group)

                await page.wait_for_timeout(1000)

        await browser.close()

        # Organize by category
        categories_enhanced = {}
        for group in all_groups_enhanced:
            cat = group['category']
            if cat not in categories_enhanced:
                categories_enhanced[cat] = {
                    'name': cat,
                    'emoji': group.get('category_emoji', ''),
                    'winners': []
                }
            categories_enhanced[cat]['winners'].append(group)

        # Save enhanced data
        output_data = {
            "scraped_at": datetime.now().isoformat(),
            "total_groups": len(all_groups_enhanced),
            "categories": list(categories_enhanced.keys()),
            "categories_data": list(categories_enhanced.values())
        }

        json_file = output_dir / f"skool_enhanced_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*70}")
        print("✅ DONE!")
        print(f"{'='*70}")
        print(f"📁 Directory: {output_dir}")
        print(f"📊 Groups: {len(all_groups_enhanced)}")
        print(f"📂 Categories: {output_data['categories']}")
        print(f"📄 JSON: {json_file}")


if __name__ == "__main__":
    asyncio.run(add_about_to_basic_data())
