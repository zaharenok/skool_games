# Skool Games Parser & Dashboard

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.49%2B-red)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

Парсер и интерактивный дашборд для анализа данных Skool Games leaderboard.

## 📸 Скриншоты

![Dashboard](https://raw.githubusercontent.com/zaharenok/skool_games/main/screenshots/dashboard.png)

## ✨ Возможности

- **Парсинг данных** со страницы Skool Games leaderboard
- **9 категорий**: Hobbies, Music, Money, Spirituality, Tech, Health, Sports, Self-improvement, Relationships
- **Детальная информация** о каждой группе-победителе:
  - Название и описание
  - Количество участников
  - Цена (если платная)
  - Создатель
  - Статус (Private/Public)
  - Рост MRR и позиция в рейтинге
- **Интерактивный дашборд** на Streamlit
- **Экспорт** в JSON и CSV

## 🚀 Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/zaharenok/skool_games.git
cd skool_games
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Запуск парсера

```bash
python skool_parser.py
```

Данные сохранятся в `skool_games_*.json` и `skool_games_*.csv`

### 4. Запуск дашборда

```bash
streamlit run dashboard.py
```

Дашборд откроется по адресу http://localhost:8501

## 📁 Структура проекта

```
skool_games/
├── skool_parser.py         # Основной парсер leaderboard
├── skool_enhanced_parser.py # Расширенный парсер с данными о группах
├── dashboard.py             # Streamlit дашборд
├── requirements.txt         # Зависимости Python
├── README.md               # Этот файл
├── .gitignore              # Git ignore
└── data/                   # Папка для данных (создается автоматически)
    ├── skool_games_*.json
    ├── skool_games_*.csv
    ├── skool_groups_*.json
    └── skool_groups_*.csv
```

## 🎯 Использование

### Парсинг базовых данных leaderboard

```bash
python skool_parser.py
```

Собирает:
- Позицию в рейтинге
- Имя владельца
- Название сообщества
- Рост MRR
- Текущий MRR

### Парсинг расширенных данных о группах

```bash
python skool_enhanced_parser.py
```

Дополнительно собирает:
- URL группы
- Описание
- Количество участников
- Цена подписки
- Создатель (с ссылкой)
- Статус (Private/Public)

## 🔑 Настройка

Для работы парсера нужны cookies сессии Skool. Добавьте их в файлы:

**В `skool_parser.py`:**
```python
COOKIES = [
    {
        "name": "client_id",
        "value": "YOUR_CLIENT_ID",
        "domain": ".skool.com",
        ...
    }
]
```

**В `skool_enhanced_parser.py`:** аналогично

### Как получить cookies:

1. Откройте https://www.skool.com/skoolers/-/games в браузере
2. Войдите в аккаунт
3. Откройте DevTools (F12)
4. Перейдите в Application → Cookies
5. Скопируйте значения `client_id`, `auth_token`, `aws-waf-token`

## 📊 Дашборд

Дашборд включает:

- **Фильтрация** по категориям
- **Поиск** по имени или названию сообщества
- **Графики**:
  - Общий рост MRR по категориям
  - Количество участников по категориям
  - Топ-10 по росту MRR
  - Топ-10 по текущему MRR
- **Детальная таблица** со всеми данными
- **Экспорт** в CSV/JSON

## 🐛 Troubleshooting

### Playwright не устанавливается

```bash
playwright install chromium --with-deps
```

### Ошибка таймаута при парсинге

Увеличьте timeout в коде или уменьшите количество обрабатываемых групп.

### Cookies истекли

Обновите `COOKIES` в файлах парсера.

## 📝 Лицензия

MIT License - свободно используйте в своих проектах!

## 🤝 Контрибьюция

Пул реквесты приветствуются! Не стесняйтесь открывать issues.

## 👨‍💻 Автор

Создано с ❤️ для анализа Skool Games

---

**Важно:** Этот проект предназначен для образовательных целей. Соблюдайте условия использования Skool.com.
