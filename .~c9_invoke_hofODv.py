import boto3
import requests
from datetime import datetime

def download_html(event, context):
    url = "https://casas.mitula.com.co/casas/bogota"
    s3 = boto3.client("s3")
    today = datetime.today().strftime('%Y-%m-%d')

    for i in range(1, 11):
        try:
            response = requests.get(f"{url}?page={i}", timeout=10)
            response.raise_for_status()  # Lanza un error si el status_code no es 200

            file_name = f"{today}-page{i}.html"
            s3.put_object(
                Bucket="landing-casas-c",
                Key=f"{today}/{file_name}",
                Body=response.text
            )
            print(f"Guardado en S3: {file_name}")
        
        except requests.exceptions.RequestException as e:
            print(f"Error descargando página {i}: {e}")

