import boto3
import requests
import time
from datetime import datetime
from requests.exceptions import RequestException

S3_BUCKET = "landing-casas-c"


def download_html(event, context):
    """Descarga páginas HTML y las guarda en S3."""
    url = "https://casas.mitula.com.co/casas/bogota"
    s3 = boto3.client("s3")
    today = datetime.today().strftime("%Y-%m-%d")
    session = requests.Session()  # Mantener cookies y mejorar persistencia

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.google.com/",
    }

    for i in range(1, 11):
        attempt = 0
        while attempt < 3:  # Intentar hasta 3 veces
            try:
                response = session.get(
                    f"{url}?page={i}", headers=headers, timeout=10
                )
                response.raise_for_status()  # Verificar que la respuesta es 200 OK

                file_name = f"{today}-page{i}.html"
                s3.put_object(
                    Bucket=S3_BUCKET,
                    Key=f"{today}/{file_name}",
                    Body=response.text.encode("utf-8"),
                    ContentType="text/html",
                )
                print(f"✅ Guardado en S3: {file_name}")
                break  # Salir del loop si todo está bien

            except RequestException as e:
                attempt += 1
                print(f"⚠ Error en pág. {i}, intento {attempt}: {e}")
                time.sleep(2 ** attempt)  # Espera exponencial: 2s, 4s, 8s

        if attempt == 3:
            print(f"❌ Falló la descarga de la pág. {i} después de 3 intentos")


def lambda_handler(event, context):
    """Función Lambda para ejecutar la descarga de HTML."""
    download_html(event, context)
