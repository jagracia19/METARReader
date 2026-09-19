"""Unit tests for metar_decoder.decode_metar().

Each test feeds decode_metar() a mock METAR JSON record - shaped like
the records returned by aviationweather.gov's ?format=json API - and
checks that it's translated into the expected plain-English report.
No network calls are made.
"""

import pytest

from metar_decoder import FLIGHT_CATEGORY, decode_metar

# A mock record based on a real KHIO observation: calm/variable wind,
# overcast skies, no weather phenomena.
KHIO_CALM_OVERCAST = {
    "icaoId": "KHIO",
    "name": "Portland/Hillsboro Arpt, OR, US",
    "obsTime": 1789764780,  # 2026-09-18T21:53:00Z
    "temp": 17.2,
    "dewp": 11.1,
    "wdir": "VRB",
    "wspd": 3,
    "visib": "10+",
    "altim": 1023.1,
    "clouds": [{"cover": "OVC", "base": 2200}],
    "fltCat": "MVFR",
    "rawOb": "METAR KHIO 182053Z VRB03KT 10SM OVC022 17/11 A3021 RMK AO2 SLP229",
}

# A mock record based on a real KDEN observation: a numeric wind
# direction, a gust, and multiple cloud layers.
KDEN_GUSTY_SCATTERED = {
    "icaoId": "KDEN",
    "name": "Denver Intl, CO, US",
    "obsTime": 1789764780,
    "temp": 28.3,
    "dewp": 9.4,
    "wdir": 110,
    "wspd": 9,
    "wgst": 14,
    "visib": "10+",
    "altim": 1020.1,
    "clouds": [
        {"cover": "SCT", "base": 7000},
        {"cover": "SCT", "base": 10000},
        {"cover": "BKN", "base": 20000},
    ],
    "fltCat": "VFR",
    "rawOb": "METAR KDEN 182053Z 11009G14KT 10SM SCT070 SCT100 BKN200 28/09 A3012",
}

# A mock record based on a real KMIA observation: light rain reported
# in the weather string.
KMIA_LIGHT_RAIN = {
    "icaoId": "KMIA",
    "name": "Miami Intl, FL, US",
    "obsTime": 1789764780,
    "temp": 25,
    "dewp": 23.3,
    "wdir": 80,
    "wspd": 5,
    "visib": "10+",
    "altim": 1016.3,
    "wxString": "-RA",
    "clouds": [
        {"cover": "FEW", "base": 2000},
        {"cover": "SCT", "base": 9000},
        {"cover": "OVC", "base": 11000},
    ],
    "fltCat": "VFR",
    "rawOb": "METAR KMIA 182053Z 08005KT 10SM -RA FEW020 SCT090 OVC110 25/23 A3001",
}


def test_decode_calm_variable_wind_and_overcast_sky():
    report = decode_metar(KHIO_CALM_OVERCAST)

    assert report["station"] == "KHIO"
    assert report["temperature_f"] == 63.0
    assert report["temperature_c"] == 17.2
    assert report["dewpoint_f"] == 52.0
    assert report["wind"] == "Wind blowing from variable directions at 3.5 mph"
    assert report["visibility"] == "Visibility 10 miles or more (excellent visibility)"
    assert report["sky_conditions"] == ["Overcast at 2,200 feet"]
    assert report["weather_phrases"] == []
    assert report["pressure"] == "30.21 inHg (1023.1 hPa)"
    assert report["flight_category"] == "MVFR"
    assert report["flight_category_text"] == FLIGHT_CATEGORY["MVFR"]
    assert report["observed_at"] == "2026-09-18 20:53 UTC"


def test_decode_numeric_wind_direction_with_gust():
    report = decode_metar(KDEN_GUSTY_SCATTERED)

    assert report["wind"] == (
        "Wind blowing from the East-Southeast (110°) at 10.4 mph, gusting to 16.1 mph"
    )
    assert report["sky_conditions"] == [
        "Scattered clouds at 7,000 feet",
        "Scattered clouds at 10,000 feet",
        "Broken clouds at 20,000 feet",
    ]
    assert report["flight_category_text"] == FLIGHT_CATEGORY["VFR"]


def test_decode_weather_phenomena_and_summary():
    report = decode_metar(KMIA_LIGHT_RAIN)

    assert report["weather_phrases"] == ["Light rain"]
    # Weather phenomena take priority over sky conditions in the summary.
    assert report["summary"].startswith("Light rain")
    assert "77.0°F" in report["summary"]


@pytest.mark.parametrize(
    "wdir, wspd, wgst, expected",
    [
        (0, 0, None, "Calm winds"),
        (None, None, None, "Calm winds"),
        (0, 5, None, "Wind blowing from the North (0°) at 5.8 mph"),
        (270, 10, None, "Wind blowing from the West (270°) at 11.5 mph"),
        (200, 15, 25, "Wind blowing from the South-Southwest (200°) at 17.3 mph, gusting to 28.8 mph"),
        ("VRB", 4, None, "Wind blowing from variable directions at 4.6 mph"),
    ],
)
def test_decode_wind_variations(wdir, wspd, wgst, expected):
    data = {"wdir": wdir, "wspd": wspd}
    if wgst is not None:
        data["wgst"] = wgst

    report = decode_metar(data)
    assert report["wind"] == expected


@pytest.mark.parametrize(
    "visib, expected",
    [
        ("10+", "Visibility 10 miles or more (excellent visibility)"),
        ("1/2", "Visibility 1/2 miles (poor visibility)"),
        ("2", "Visibility 2 miles (reduced visibility)"),
        ("6", "Visibility 6 miles (good visibility)"),
        ("M1/4", "Visibility less than 1/4 miles (very poor visibility)"),
    ],
)
def test_decode_visibility_variations(visib, expected):
    report = decode_metar({"visib": visib})
    assert report["visibility"] == expected


def test_decode_missing_visibility_reports_unknown():
    report = decode_metar({})
    assert report["visibility"] == "Visibility not reported"


@pytest.mark.parametrize(
    "wx_string, expected_phrases",
    [
        ("-RA", ["Light rain"]),
        ("+TSRA", ["Heavy thunderstorm with rain"]),
        ("BR", ["Mist"]),
        ("VCFG", ["Nearby fog"]),
        ("-SN BR", ["Light snow", "Mist"]),
    ],
)
def test_decode_weather_string_variations(wx_string, expected_phrases):
    report = decode_metar({"wxString": wx_string})
    assert report["weather_phrases"] == expected_phrases


def test_decode_no_clouds_reported():
    report = decode_metar({"clouds": []})
    assert report["sky_conditions"] == ["No clouds reported"]


def test_decode_clear_sky_cover_code():
    report = decode_metar({"clouds": [{"cover": "CLR"}]})
    assert report["sky_conditions"] == ["Clear skies"]


def test_decode_missing_temperature_is_none_not_zero():
    report = decode_metar({})
    assert report["temperature_f"] is None
    assert report["temperature_c"] is None


def test_decode_negative_temperature():
    report = decode_metar({"temp": -12.0})
    assert report["temperature_f"] == 10.4


def test_decode_missing_pressure_reports_none():
    report = decode_metar({})
    assert report["pressure"] is None


def test_decode_unknown_flight_category_falls_back():
    report = decode_metar({"fltCat": None})
    assert report["flight_category"] is None
    assert report["flight_category_text"] == "Unknown"


def test_decode_falls_back_to_sky_conditions_when_no_weather_phrases():
    report = decode_metar({"clouds": [{"cover": "FEW", "base": 3000}]})
    assert report["summary"].startswith("A few clouds at 3,000 feet")
