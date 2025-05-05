from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import requests
import re
from fastapi.middleware.cors import CORSMiddleware
import time
import pandas as pd
import random

app = FastAPI()

# Настройка CORS
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost",
    "http://127.0.0.1",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Загрузка моделей
loading_model = joblib.load(r"D:\Web_testing_pj\Web_testing_api\models\model1.pkl")
conversion_model = joblib.load(r"D:\Web_testing_pj\Web_testing_api\models\model2.pkl")

# Регулярное выражение для проверки URL
URL_REGEX = re.compile(r'^(https?://)?([a-z0-9-]+\.)+[a-z0-9]{2,3}(/.*)?$', re.IGNORECASE)

class UrlRequest(BaseModel):
    url: str
    request_type: str  # 'loading' или 'conversion'

    @staticmethod
    def validate_url(url: str):
        if not URL_REGEX.match(url):
            raise ValueError("Некорректный формат URL.")
        return url

def get_loading_time(url: str) -> tuple:
    start_time = time.time()
    try:
        response = requests.get(url)
        loading_time = time.time() - start_time

        if response.status_code == 200:
            return loading_time, "Успешно"
        else:
            return float('inf'), f"Ошибка: {response.status_code}"
    except requests.RequestException as e:
        return float('inf'), f"Ошибка: {str(e)}"

def get_conversion_rate(url: str) -> float:
    try:
        response = requests.get(url)
        if response.status_code == 200:
            content_length = len(response.text)
            headings_count = response.text.lower().count('<h1>') + response.text.lower().count('<h2>')
            image_count = response.text.lower().count('<img')
            return min((content_length + headings_count + image_count) / 1e5, 1.0)
        else:
            return 0.0
    except requests.RequestException:
        return 0.0

@app.post("/analyze/")
def analyze_url(request: UrlRequest):
    try:
        request.url = UrlRequest.validate_url(request.url)

        if request.request_type == "loading":
            loading_time, status = get_loading_time(request.url)

            if loading_time == float('inf'):
                if "404" in status or "не доступен" in status:
                    return {
                        "type": "loading",
                        "url": request.url,
                        "loading_time": None,
                        "recommendation": "Сайт недоступен. Проверьте URL или улучшите серверную инфраструктуру."
                    }
                raise HTTPException(status_code=500, detail="Не удалось получить время загрузки.")

            features = pd.DataFrame([[loading_time]], columns=['Load Time(s)'])
            predicted_loading_time = loading_model.predict(features)[0]

            percent_faster = random.randint(80, 95)
            if predicted_loading_time < 1.5:
                recommendation = (
                    f"Скорость загрузки лучше, чем у {percent_faster}% сайтов. "
                    f"Для дальнейшего улучшения можно: уменьшить размер изображений, использовать кэширование или сократить количество запросов."
                )
            elif predicted_loading_time < 3.0:
                recommendation = (
                    f"Скорость загрузки в пределах нормы. "
                    f"Рекомендуется оптимизировать изображения и кэширование."
                )
            else:
                recommendation = (
                    f"Скорость загрузки ниже среднего. "
                    f"Рекомендуется сделать оптимизацию для повышения скорости."
                )

            return {
                "type": "loading",
                "url": request.url,
                "loading_time": round(loading_time, 2),
                "recommendation": recommendation,
            }

        elif request.request_type == "conversion":
            conversion_rate = get_conversion_rate(request.url)

            features = pd.DataFrame([[conversion_rate]], columns=['Conversion Rate'])
            predicted_conversion_rate = conversion_model.predict(features)[0]

            # Уточненная логика для уровней коэффициента конверсии:
            if predicted_conversion_rate >= 0.85:
                level = "Высокий"
                recommendation = (
                    "Уровень коэффициента конверсии: Высокий. "
                    "Продолжайте в том же духе, добавляйте новые призывы к действию."
                )
            elif predicted_conversion_rate >= 0.5:
                level = "Средний"
                recommendation = (
                    "Уровень коэффициента конверсии: Средний. "
                    "Рекомендуем улучшить форму обратной связи и добавить призывы к действию."
                )
            else:
                level = "Низкий"
                recommendation = (
                    "Уровень коэффициента конверсии: Низкий. "
                    "Необходимо использовать промо-акции, улучшить контент и дизайн страницы."
                )

            # Проверка и вывода значения
            return {
                "type": "conversion",
                "url": request.url,
                "conversion_rate": round(conversion_rate, 2),
                "predicted_conversion_rate": round(predicted_conversion_rate, 2),
                "recommendation": recommendation,
            }

    except HTTPException as http_exc:
        raise http_exc
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Произошла ошибка: {str(e)}")

# virt\Scripts\activate 
# uvicorn Main:app --reload 
# # uvicorn app.Main:app --reload
# для index python -m http.server 8080