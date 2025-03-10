import json
import datetime
import pytest
from unittest.mock import patch, MagicMock
from lambda_scraper import download_html
from lambda_parser import clean_price, process_html

# Test 1: Verificar que clean_price limpia correctamente el precio.
def test_clean_price():
    raw_price = "590.000 COP"
    expected = "590000"
    assert clean_price(raw_price) == expected

# Test 2: Verificar que download_html obtiene HTML y lo sube a S3
@patch("lambda_scraper.boto3.client")
@patch("lambda_scraper.requests.Session.get")  # Corregido para requests.Session
def test_download_html_success(mock_requests_get, mock_boto_client):
    # Simular respuesta de requests.get
    mock_response = MagicMock()
    sample_html = "<html><body><script type='application/ld+json'>[{\"about\": []}]</script></body></html>"
    mock_response.text = sample_html
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    # Simular cliente S3
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    # Ejecutar la función de descarga
    download_html({}, {})

    # Verificar que requests.get se llamó 10 veces
    assert mock_requests_get.call_count == 10, (
        f"requests.get fue llamado {mock_requests_get.call_count} veces, se esperaba 10"
    )
    
    # Verificar que se subieron 10 archivos a S3
    assert mock_s3.put_object.call_count == 10, (
        f"s3.put_object fue llamado {mock_s3.put_object.call_count} veces, se esperaba 10"
    )

# Test 3: Verificar que process_html genera un CSV en S3
@patch("lambda_parser.boto3.client")
def test_process_html(mock_boto_client):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    # Simular archivos en S3
    today = datetime.date.today().strftime("%Y-%m-%d")
    test_html_key = f"{today}/2025-03-10-page1.html"

    mock_s3.list_objects_v2.return_value = {
        "Contents": [{"Key": test_html_key}]
    }

    # Simular HTML con JSON válido
    sample_html = (
        "<html><body><script type='application/ld+json'>"
        "[{\"about\": [{\"address\": {\"streetAddress\": \"Barrio 1, Algún lugar\"},"
        "\"description\": \"Venta $590.000\\nMás info\","
        "\"numberOfBedrooms\": 2,"
        "\"numberOfBathroomsTotal\": 1,"
        "\"floorSize\": {\"value\": 50}}]}]"
        "</script></body></html>"
    )
    
    mock_s3.get_object.return_value = {
        "Body": MagicMock(read=MagicMock(return_value=sample_html.encode("utf-8")))
    }

    # Ejecutar la función process_html
    process_html()

    # Verificar que se intentó obtener el archivo HTML correcto desde el bucket
    mock_s3.get_object.assert_called_once_with(Bucket="landing-casas-c", Key=test_html_key)

    # Verificar que el CSV fue guardado en S3
    mock_s3.put_object.assert_called_once()
    
    # Verificar que el CSV contiene la información esperada
    csv_body = mock_s3.put_object.call_args.kwargs["Body"]
    assert "Barrio 1" in csv_body, "El CSV no contiene 'Barrio 1'"
    assert "590000" in csv_body, "El CSV no contiene el precio limpio '590000'"
