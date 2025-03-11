import boto3
import csv  # noqa: F401
import json
from datetime import datetime
from bs4 import BeautifulSoup

S3_BUCKET_INPUT = "landing-casas-c"
S3_BUCKET_OUTPUT = "casas-final-c"


def clean_price(price_str):
    """Limpia el precio, eliminando símbolos y puntos."""
    if "COP" in price_str:
        price_str = price_str.replace(" COP", "")
    return price_str.replace(".", "").strip()


def process_html():
    """Procesa los archivos HTML de S3, extrae datos y guarda un CSV."""
    s3 = boto3.client("s3")
    today = datetime.today().strftime("%Y-%m-%d")
    response = s3.list_objects_v2(
        Bucket=S3_BUCKET_INPUT, Prefix=f"{today}/"
    )
    files = [obj["Key"] for obj in response.get("Contents", [])]
    if not files:
        print("No se encontraron archivos en S3 para procesar.")
        return

    results = []
    for file_key in files:
        print(f"📂 Procesando archivo: {file_key}")
        obj = s3.get_object(Bucket=S3_BUCKET_INPUT, Key=file_key)
        html_content = obj["Body"].read().decode("utf-8")
        soup = BeautifulSoup(html_content, "html.parser")
        script_tag = soup.find("script", type="application/ld+json")
        if not script_tag:
            print(f"⚠️ No se encontró JSON en {file_key}")
            continue
        try:
            data = json.loads(script_tag.string)
            if isinstance(data, list) and data:
                properties = data[0].get("about", [])
            else:
                properties = []
        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌ Error procesando JSON en {file_key}: {e}")
            continue

        for prop in properties:
            try:
                address = prop.get("address", {})
                barrio = (
                    address.get("streetAddress", "N/A")
                    .split(",")[0].strip()
                )
                description = prop.get("description", "")
                if "$" in description:
                    valor_raw = (
                        description.split("$")[-1]
                        .split("\n")[0].strip()
                    )
                else:
                    valor_raw = "N/A"
                valor = (
                    clean_price(valor_raw)
                    if valor_raw != "N/A" else "N/A"
                )
                habitaciones = prop.get("numberOfBedrooms", "N/A")
                banos = prop.get("numberOfBathroomsTotal", "N/A")
                mts2 = prop.get("floorSize", {}).get("value", "N/A")
                results.append([
                    today, barrio, valor, habitaciones, banos, mts2
                ])
            except Exception as e:
                print(f"⚠️ Error procesando propiedad en {file_key}: {e}")
                continue

    if not results:
        print("⚠️ No se encontraron propiedades en los archivos procesados.")
        return

    csv_key = f"{today}/{today}.csv"
    csv_header = (
        "FechaDescarga;Barrio;Valor;NumHabitaciones;NumBanos,cts2\n"
    )
    csv_rows = "\n".join(
        [";".join(map(str, row)) for row in results]
    )
    s3.put_object(
        Bucket=S3_BUCKET_OUTPUT,
        Key=csv_key,
        Body=csv_header + csv_rows,
        ContentType="text/csv",
    )
    print(f"✅ Archivo guardado en {S3_BUCKET_OUTPUT}/{csv_key}")


def lambda_handler(event, context):
    """Función principal de AWS Lambda."""
    process_html()
    return {"statusCode": 200, "body": "Procesamiento completado"}
