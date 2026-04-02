#!/bin/bash
# Запуск Streamlit Dashboard на хосте

cd "$(dirname "$0")"

# Активировать виртуальное окружение
source venv/bin/activate

# Проверить, есть ли данные
if [ ! -f "skool_games_*.json" ] && [ ! -f "skool_groups_enhanced_*.json" ]; then
    echo "⚠️  Нет JSON данных для отображения."
    echo "Запустите сначала: python skool_parser.py или python skool_enhanced_parser.py"
    exit 1
fi

# Порт по умолчанию
PORT=${1:-8501}

echo "================================================"
echo "🚀 Запуск Streamlit Dashboard"
echo "   Порт: $PORT"
echo "   Доступ: http://0.0.0.0:$PORT"
echo "================================================"
echo ""

# Запуск на всех интерфейсах (0.0.0.0)
streamlit run dashboard.py \
    --server.address 0.0.0.0 \
    --server.port $PORT \
    --server.enableCORS false \
    --server.enableXsrfProtection true \
    --browser.gatherUsageStats false