import os
import json
import locale
from flask import Flask, request, jsonify
import cloudinary
import cloudinary.uploader
from openai import OpenAI, AssistantEventHandler
from typing_extensions import override
from datetime import datetime
import time
import logging

app = Flask(__name__)

# Установка локали для русского языка
locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')

# Настройки Cloudinary
app.config['CLOUDINARY_CLOUD_NAME'] = 'drkwqb4l9'
app.config['CLOUDINARY_API_KEY'] = '457966774888214'
app.config['CLOUDINARY_API_SECRET'] = 'WzNoppR487-PSNdXhAzbboFIE6M'

# Конфигурация Cloudinary
cloudinary.config(
    cloud_name=app.config['CLOUDINARY_CLOUD_NAME'],
    api_key=app.config['CLOUDINARY_API_KEY'],
    api_secret=app.config['CLOUDINARY_API_SECRET']
)

# Инициализация клиента OpenAI с указанием API-ключа напрямую
client = OpenAI(api_key="sk-proj-yjivXgLWXQx56BTflOKIT3BlbkFJUUw6b4mrXN89MOQ0I0vs")

# Определяем класс для обработки событий стриминга
class EventHandler(AssistantEventHandler):
    def __init__(self):
        self.response = ""
        super().__init__()

    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)
    
    @override
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)
        self.response += delta.value

# Функция для валидации формата изображения
def validate_image_format(image_path):
    valid_extensions = {".jpeg", ".jpg", ".png", ".gif", ".webp"}
    extension = os.path.splitext(image_path)[1].lower()
    if extension not in valid_extensions:
        raise ValueError(f"Неподдерживаемый формат файла: {extension}")

# Функция для преобразования строки даты в метку времени
def parse_date(date_str):
    formats = ["%d %B %Y", "%d %b %Y", "%d/%m/%y", "%d-%m-%Y"]
    for date_format in formats:
        try:
            return int(datetime.strptime(date_str, date_format).timestamp())
        except ValueError:
            continue
    raise ValueError(f"Невозможно преобразовать дату: {date_str}")

@app.route('/upload', methods=['POST'])
def upload_and_analyze():
    try:
        start_time = time.time()  # Запускаем таймер для подсчета времени обработки

        print("Step 1: Checking if file is present in the request")
        if 'file' not in request.files:
            print("Step 1: No file found in the request")
            return jsonify({"error": "No file part in the request"}), 400

        file = request.files['file']

        if file.filename == '':
            print("Step 1: No file selected")
            return jsonify({"error": "No selected file"}), 400

        # Валидация формата изображения
        validate_image_format(file.filename)

        print("Step 2: Uploading file to Cloudinary")
        upload_result = cloudinary.uploader.upload(file, folder='screenshots')
        image_url = upload_result['secure_url']
        image_path = upload_result['public_id']  # Получаем путь к файлу на Cloudinary
        print(f"Step 2: File uploaded to Cloudinary, URL: {image_url}")

        print("Step 3: Sending image URL to OpenAI for analysis")
        thread = client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this image."},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ],
                }
            ]
        )

        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id="asst_pRnFkXsxMjoQd6BOHJ2HPORc"
        )

        print("Step 4: Waiting for OpenAI to complete analysis")
        while run.status not in ["completed", "failed"]:
            time.sleep(5)
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        print("Step 5: Processing the response from OpenAI")
        event_handler = EventHandler()
        with client.beta.threads.runs.stream(
            thread_id=thread.id,
            assistant_id="asst_pRnFkXsxMjoQd6BOHJ2HPORc",
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

        # Декодирование JSON-строки в Python объект
        response_data = json.loads(event_handler.response)

        # Пример использования функции parse_date для преобразования даты
        if 'date' in response_data:
            response_data['timestamp'] = parse_date(response_data['date'])

        # Преобразование pace в формат "MM.SSSS"
        pace_str = response_data.get("pace")
        if pace_str:
            try:
                if ":" in pace_str:
                    minutes, seconds = map(float, pace_str.split(":"))
                    pace = minutes + seconds / 60
                    response_data["pace"] = f"{pace:.4f}"
                else:
                    response_data["pace"] = pace_str
            except ValueError as e:
                logging.error("Ошибка преобразования pace: %s", e)
                response_data["pace"] = None

        # Получаем критерии анализа и рассчитываем average_score
        criteria_analysis = response_data.get("criteria_analysis", {})
        total_score = sum(criteria_analysis.values())
        average_score = total_score / 90

        # Добавляем поля average_score, verified и processing_time
        response_data["average_score"] = average_score
        response_data["verified"] = average_score < 0.15
        processing_time = time.time() - start_time
        response_data["processing_time"] = round(processing_time, 2)
        response_data["file_path"] = image_path  # Добавляем путь к файлу

        print("Step 6: Returning the response from OpenAI to the user")
        return jsonify({"message": "Analysis completed", "response": response_data}), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Запуск приложения на порту 5001
    app.run(host='0.0.0.0', port=5001, debug=True)
