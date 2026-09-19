"""Tests for the Flask routes in app.py.

metar_decoder.get_decoded_metar is mocked out (patched on the app
module, where it was imported) so these tests never make a real
network call to aviationweather.gov.
"""

from unittest.mock import patch

from metar_decoder import MetarError

MOCK_REPORT = {
    "station": "KHIO",
    "station_name": "Portland/Hillsboro Arpt, OR, US",
    "observed_at": "2026-09-18 20:53 UTC",
    "summary": "Overcast at 2,200 feet, 63.0°F, wind blowing from variable directions at 3.5 mph",
    "temperature_f": 63.0,
    "temperature_c": 17.2,
    "dewpoint_f": 52.0,
    "dewpoint_c": 11.1,
    "wind": "Wind blowing from variable directions at 3.5 mph",
    "visibility": "Visibility 10 miles or more (excellent visibility)",
    "sky_conditions": ["Overcast at 2,200 feet"],
    "weather_phrases": [],
    "pressure": "30.21 inHg (1023.1 hPa)",
    "flight_category": "MVFR",
    "flight_category_text": "Marginal Visual Flight Rules (some flying caution advised)",
    "raw_metar": "METAR KHIO 182053Z VRB03KT 10SM OVC022 17/11 A3021 RMK AO2 SLP229",
}


def test_get_index_shows_empty_search_form(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Get Weather" in response.data
    assert b"result-card" not in response.data


def test_post_valid_airport_code_shows_decoded_report(client):
    with patch("app.get_decoded_metar", return_value=MOCK_REPORT) as mock_decode:
        response = client.post("/", data={"airport_code": "khio"})

    mock_decode.assert_called_once_with("khio")
    assert response.status_code == 200
    assert b"Overcast at 2,200 feet" in response.data
    assert b"63.0" in response.data


def test_post_invalid_airport_code_shows_error_message(client):
    with patch("app.get_decoded_metar", side_effect=MetarError('No weather station found for airport code "ZZZZ".')):
        response = client.post("/", data={"airport_code": "ZZZZ"})

    assert response.status_code == 200
    assert b"No weather station found" in response.data


def test_api_metar_returns_decoded_json_on_success(client):
    with patch("app.get_decoded_metar", return_value=MOCK_REPORT):
        response = client.get("/api/metar/KHIO")

    assert response.status_code == 200
    assert response.get_json() == MOCK_REPORT


def test_api_metar_returns_404_with_error_on_failure(client):
    with patch("app.get_decoded_metar", side_effect=MetarError('"ZZZZ" doesn\'t look like a valid airport code.')):
        response = client.get("/api/metar/ZZZZ")

    assert response.status_code == 404
    assert response.get_json() == {"error": '"ZZZZ" doesn\'t look like a valid airport code.'}
