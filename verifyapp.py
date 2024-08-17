from openai import OpenAI, AssistantEventHandler
from typing_extensions import override
import time

# Инициализация клиента OpenAI с указанием API-ключа напрямую
client = OpenAI(api_key="API")

# Определяем класс для обработки событий стриминга
class EventHandler(AssistantEventHandler):
    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)
    
    @override
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)

# Создание потока с указанием URL изображения
thread = client.beta.threads.create(
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Analyze this image."},
                {"type": "image_url", "image_url": {"url": "https://res.cloudinary.com/drkwqb4l9/image/upload/v1723902829/test_image_diac6e.png"}}
            ],
        }
    ]
)

# Запуск ассистента с использованием стриминга
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id="asst_pRnFkXsxMjoQd6BOHJ2HPORc"
)

# Цикл ожидания завершения выполнения
while run.status not in ["completed", "failed"]:
    time.sleep(5)  # Ожидание 5 секунд перед следующим запросом
    run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

# Когда завершено, запускаем потоковую обработку
with client.beta.threads.runs.stream(
    thread_id=thread.id,
    assistant_id="asst_pRnFkXsxMjoQd6BOHJ2HPORc",
    event_handler=EventHandler(),
) as stream:
    stream.until_done()
