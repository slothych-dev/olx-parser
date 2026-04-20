import requests
from bs4 import BeautifulSoup
import csv
import os
import time
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

URLS_FILE = "monitored_urls.json"   # тут зберігаються всі посилання
CSV_FILE = "price_history.csv"      # тут зберігається історія цін
CHECK_INTERVAL = 5 * 60            # перевірка кожні 5 хвилин


# === РОБОТА З ФАЙЛАМИ ===

def save_price_history(url, price):
    """Зберігає тільки 2 останні ціни для кожного оголошення"""
    history = {}

    # Читаємо існуючу історію
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # пропускаємо заголовок
            for row in reader:
                if len(row) == 3:
                    if row[1] not in history:
                        history[row[1]] = []
                    history[row[1]].append(row)

    # Додаємо новий запис
    if url not in history:
        history[url] = []
    history[url].append([datetime.now().strftime("%Y-%m-%d %H:%M"), url, price])

    # Залишаємо тільки 2 останні
    history[url] = history[url][-2:]

    # Перезаписуємо файл
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Час", "Посилання", "Ціна"])
        for url_records in history.values():
            writer.writerows(url_records)


# === TELEGRAM ===

def send_telegram(message):
    """Надсилає повідомлення в Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    })


def get_updates(offset=None):
    """Отримує нові повідомлення від користувача"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    response = requests.get(url, params=params)
    return response.json().get("result", [])


# === ПАРСИНГ ===

def get_price(url):
    """Отримує поточну ціну з оголошення OLX"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        price_tag = soup.find("div", attrs={"data-testid": "ad-price-container"})
        if price_tag:
            return price_tag.text.strip()
    except:
        pass
    return None


def get_title(url):
    """Отримує назву оголошення"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.find("h4")
        if title:
            return title.text.strip()
    except:
        pass
    return url  # якщо не знайшло назву — повертає посилання


# === ПЕРЕВІРКА ЦІН ===

def check_all_prices():
    """Перевіряє ціни всіх збережених оголошень"""
    urls = load_urls()

    if not urls:
        return

    print(f"[{datetime.now().strftime('%H:%M')}] Перевіряємо {len(urls)} оголошень...")

    for url, data in urls.items():
        current_price = get_price(url)

        if not current_price:
            print(f"  ❌ Не вдалось отримати ціну: {url}")
            continue

        last_price = data.get("last_price")
        title = data.get("title", url)

        save_price_history(url, current_price)

        if last_price is None:
            print(f"  ✅ Перша перевірка: {title} — {current_price}")
        elif current_price != last_price:
            print(f"  ⚡ Ціна змінилась: {title}")
            send_telegram(
                f"⚡ <b>Ціна змінилась!</b>\n\n"
                f"📦 {title}\n"
                f"📉 Було: {last_price}\n"
                f"💰 Стало: {current_price}\n"
                f"🔗 {url}"
            )
        else:
            print(f"  — Без змін: {title} — {current_price}")

        # Оновлюємо збережену ціну
        urls[url]["last_price"] = current_price

    save_urls(urls)


# === ОБРОБКА КОМАНД ===

def handle_message(text):
    """Обробляє повідомлення від користувача"""
    urls = load_urls()
    text = text.strip()

    # Додати нове оголошення
    if text.startswith("http"):
        if text in urls:
            send_telegram("⚠️ Це оголошення вже відслідковується!")
            return

        title = get_title(text)
        price = get_price(text)

        if not price:
            send_telegram("❌ Не вдалось отримати ціну. Перевір посилання.")
            return

        urls[text] = {
            "title": title,
            "last_price": price,
            "added": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        save_urls(urls)
        send_telegram(
            f"✅ <b>Додано до моніторингу!</b>\n\n"
            f"📦 {title}\n"
            f"💰 Поточна ціна: {price}"
        )

    # Показати всі оголошення
    elif text == "/list":
        if not urls:
            send_telegram("📋 Список порожній. Надішли посилання на OLX щоб додати.")
            return

        message = "📋 <b>Відслідковую:</b>\n\n"
        for i, (url, data) in enumerate(urls.items(), 1):
            message += f"{i}. {data.get('title', 'Без назви')}\n"
            message += f"   💰 {data.get('last_price', '?')}\n"
            message += f"   🔗 {url}\n\n"
        send_telegram(message)

    # Видалити оголошення
    elif text.startswith("/delete "):
        url_to_delete = text.replace("/delete ", "").strip()
        if url_to_delete in urls:
            title = urls[url_to_delete].get("title", url_to_delete)
            del urls[url_to_delete]
            save_urls(urls)
            send_telegram(f"🗑 Видалено: {title}")
        else:
            send_telegram("❌ Такого посилання немає в списку.")

    # Допомога
    elif text == "/start" or text == "/help":
        send_telegram(
            "👋 <b>OLX Price Monitor</b>\n\n"
            "Що я вмію:\n"
            "🔗 Надішли посилання на OLX — додам до моніторингу\n"
            "/list — показати всі оголошення\n"
            "/delete [посилання] — видалити оголошення\n\n"
            "Перевіряю ціни кожні 30 хвилин 🕐"
        )
    else:
        send_telegram("❓ Не розумію. Надішли /help")


# === ГОЛОВНИЙ ЦИКЛ ===

print("Бот запущено! Відкрий Telegram і напиши /start")
send_telegram("✅ Бот запущено і готовий до роботи!")

offset = None
last_check = 0

while True:
    # Слухаємо повідомлення від користувача
    updates = get_updates(offset)
    for update in updates:
        offset = update["update_id"] + 1
        message = update.get("message", {})
        text = message.get("text", "")
        if text:
            print(f"Отримано: {text}")
            handle_message(text)

    # Перевіряємо ціни кожні 30 хвилин
    if time.time() - last_check > CHECK_INTERVAL:
        check_all_prices()
        last_check = time.time()

    time.sleep(3)