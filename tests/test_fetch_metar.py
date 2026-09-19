"""Tests for metar_decoder.fetch_metar() and get_decoded_metar().

requests.get is mocked throughout, so no real network calls are made.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from metar_decoder import MetarError, fetch_metar, get_decoded_metar


def _mock_response(status_code=200, json_data=None, text=None, json_error=False):
    """Build a Mock standing in for a requests.Response."""
    response = Mock()
    response.status_code = status_code
    response.text = text if text is not None else ("" if json_data is None else "non-empty")
    response.raise_for_status = Mock()
    if json_error:
        response.json = Mock(side_effect=ValueError("not JSON"))
    else:
        response.json = Mock(return_value=json_data)
    return response


@pytest.mark.parametrize("bad_code", ["", "AB", "TOOLONG", "K H", "!!!!"])
def test_fetch_metar_rejects_invalid_codes_without_calling_network(bad_code):
    with patch("metar_decoder.requests.get") as mock_get:
        with pytest.raises(MetarError, match="doesn't look like a valid airport code"):
            fetch_metar(bad_code)

    mock_get.assert_not_called()


def test_fetch_metar_uppercases_and_strips_the_code():
    response = _mock_response(json_data=[{"icaoId": "KHIO"}])
    with patch("metar_decoder.requests.get", return_value=response) as mock_get:
        fetch_metar(" khio ")

    _, kwargs = mock_get.call_args
    assert kwargs["params"]["ids"] == "KHIO"


def test_fetch_metar_returns_first_record_on_success():
    record = {"icaoId": "KHIO", "temp": 17.2}
    response = _mock_response(json_data=[record])
    with patch("metar_decoder.requests.get", return_value=response):
        result = fetch_metar("KHIO")

    assert result == record


def test_fetch_metar_raises_on_204_no_content():
    response = _mock_response(status_code=204, text="")
    with patch("metar_decoder.requests.get", return_value=response):
        with pytest.raises(MetarError, match="No weather station found"):
            fetch_metar("ZZZZ")


def test_fetch_metar_raises_on_empty_body():
    response = _mock_response(status_code=200, text="   ")
    with patch("metar_decoder.requests.get", return_value=response):
        with pytest.raises(MetarError, match="No weather station found"):
            fetch_metar("ZZZZ")


def test_fetch_metar_raises_on_empty_json_array():
    response = _mock_response(status_code=200, text="[]", json_data=[])
    with patch("metar_decoder.requests.get", return_value=response):
        with pytest.raises(MetarError, match="No weather station found"):
            fetch_metar("ZZZZ")


def test_fetch_metar_raises_on_invalid_json():
    response = _mock_response(status_code=200, text="not json", json_error=True)
    with patch("metar_decoder.requests.get", return_value=response):
        with pytest.raises(MetarError, match="unexpected response"):
            fetch_metar("KHIO")


def test_fetch_metar_raises_when_request_fails():
    with patch("metar_decoder.requests.get", side_effect=requests.ConnectionError("boom")):
        with pytest.raises(MetarError, match="Couldn't reach the weather service"):
            fetch_metar("KHIO")


def test_fetch_metar_raises_on_http_error_status():
    response = Mock()
    response.raise_for_status = Mock(side_effect=requests.HTTPError("500 Server Error"))
    with patch("metar_decoder.requests.get", return_value=response):
        with pytest.raises(MetarError, match="Couldn't reach the weather service"):
            fetch_metar("KHIO")


def test_get_decoded_metar_fetches_then_decodes():
    record = {"icaoId": "KHIO", "temp": 17.2, "wdir": 0, "wspd": 0}
    response = _mock_response(json_data=[record])
    with patch("metar_decoder.requests.get", return_value=response):
        report = get_decoded_metar("KHIO")

    assert report["station"] == "KHIO"
    assert report["temperature_f"] == 63.0
    assert report["wind"] == "Calm winds"
