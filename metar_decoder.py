"""Fetch and decode METAR weather reports into plain English."""

import re
from datetime import datetime, timezone

import requests

METAR_API_URL = "https://aviationweather.gov/api/data/metar"

COMPASS_POINTS = [
    "North", "North-Northeast", "Northeast", "East-Northeast",
    "East", "East-Southeast", "Southeast", "South-Southeast",
    "South", "South-Southwest", "Southwest", "West-Southwest",
    "West", "West-Northwest", "Northwest", "North-Northwest",
]

CLOUD_COVER = {
    "SKC": "clear skies",
    "CLR": "clear skies",
    "NSC": "no significant clouds",
    "NCD": "no clouds detected",
    "FEW": "a few clouds",
    "SCT": "scattered clouds",
    "BKN": "broken clouds",
    "OVC": "overcast",
    "VV": "sky obscured",
}

WX_INTENSITY = {
    "-": "light",
    "+": "heavy",
    "VC": "nearby",
}

WX_DESCRIPTOR = {
    "MI": "shallow",
    "PR": "partial",
    "BC": "patchy",
    "DR": "low drifting",
    "BL": "blowing",
    "SH": "showers of",
    "TS": "thunderstorm with",
    "FZ": "freezing",
}

WX_PHENOMENON = {
    "DZ": "drizzle",
    "RA": "rain",
    "SN": "snow",
    "SG": "snow grains",
    "IC": "ice crystals",
    "PL": "ice pellets",
    "GR": "hail",
    "GS": "small hail",
    "UP": "unknown precipitation",
    "BR": "mist",
    "FG": "fog",
    "FU": "smoke",
    "VA": "volcanic ash",
    "DU": "widespread dust",
    "SA": "sand",
    "HZ": "haze",
    "PY": "spray",
    "PO": "dust or sand whirls",
    "SQ": "a squall",
    "FC": "a funnel cloud",
    "SS": "a sandstorm",
    "DS": "a duststorm",
}

FLIGHT_CATEGORY = {
    "VFR": "Visual Flight Rules (good flying weather)",
    "MVFR": "Marginal Visual Flight Rules (some flying caution advised)",
    "IFR": "Instrument Flight Rules (poor visibility, instruments required)",
    "LIFR": "Low Instrument Flight Rules (very poor visibility)",
}


class MetarError(Exception):
    """Raised when a METAR report can't be fetched or found."""


def fetch_metar(airport_code: str) -> dict:
    """Fetch the latest METAR for an airport code from aviationweather.gov."""
    code = airport_code.strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{3,4}", code):
        raise MetarError(f'"{airport_code}" doesn\'t look like a valid airport code.')

    try:
        response = requests.get(
            METAR_API_URL,
            params={"ids": code, "format": "json"},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise MetarError(f"Couldn't reach the weather service: {exc}") from exc

    if response.status_code == 204 or not response.text.strip():
        raise MetarError(f'No weather station found for airport code "{code}".')

    try:
        data = response.json()
    except ValueError as exc:
        raise MetarError("The weather service returned an unexpected response.") from exc

    if not data:
        raise MetarError(f'No weather station found for airport code "{code}".')

    return data[0]


def _degrees_to_compass(degrees: float) -> str:
    index = round(degrees / 22.5) % 16
    return COMPASS_POINTS[index]


def _knots_to_mph(knots: float) -> float:
    return round(knots * 1.15078, 1)


def _celsius_to_fahrenheit(celsius: float) -> float:
    return round(celsius * 9 / 5 + 32, 1)


def _hpa_to_inhg(hpa: float) -> float:
    return round(hpa / 33.8639, 2)


def _decode_wind(data: dict) -> str:
    wdir = data.get("wdir")
    wspd = data.get("wspd")
    wgst = data.get("wgst")

    if wspd in (None, 0) and wdir in (None, 0):
        return "Calm winds"

    if wdir == "VRB":
        direction_text = "variable directions"
    elif isinstance(wdir, (int, float)):
        direction_text = f"the {_degrees_to_compass(wdir)} ({int(wdir)}°)"
    else:
        direction_text = "an unknown direction"

    mph = _knots_to_mph(wspd) if wspd is not None else 0
    text = f"Wind blowing from {direction_text} at {mph} mph"

    if wgst:
        text += f", gusting to {_knots_to_mph(wgst)} mph"

    return text


def _decode_visibility(data: dict) -> str:
    visib = data.get("visib")
    if visib is None:
        return "Visibility not reported"

    visib_str = str(visib)
    if visib_str.endswith("+"):
        return f"Visibility {visib_str.rstrip('+')} miles or more (excellent visibility)"
    if visib_str.startswith("M"):
        return f"Visibility less than {visib_str[1:]} miles (very poor visibility)"

    descriptor = ""
    try:
        value = _visibility_to_float(visib_str)
        if value is not None:
            if value < 1:
                descriptor = " (poor visibility)"
            elif value < 3:
                descriptor = " (reduced visibility)"
            else:
                descriptor = " (good visibility)"
    except (ValueError, ZeroDivisionError):
        descriptor = ""

    return f"Visibility {visib_str} miles{descriptor}"


def _visibility_to_float(visib_str: str):
    visib_str = visib_str.strip()
    if not visib_str:
        return None
    parts = visib_str.split()
    total = 0.0
    for part in parts:
        if "/" in part:
            num, denom = part.split("/")
            total += float(num) / float(denom)
        else:
            total += float(part)
    return total


def _decode_clouds(data: dict) -> list:
    clouds = data.get("clouds") or []
    if not clouds:
        return ["No clouds reported"]

    descriptions = []
    for layer in clouds:
        cover = layer.get("cover", "")
        base = layer.get("base")
        label = CLOUD_COVER.get(cover, cover)

        if cover in ("SKC", "CLR", "NSC", "NCD"):
            descriptions.append(label.capitalize())
            continue

        if base is not None:
            descriptions.append(f"{label.capitalize()} at {base:,} feet")
        else:
            descriptions.append(label.capitalize())

    return descriptions


def _decode_weather_string(wx_string: str) -> list:
    if not wx_string:
        return []

    phrases = []
    for token in wx_string.split():
        remaining = token
        intensity = ""

        if remaining.startswith(("-", "+")):
            intensity = WX_INTENSITY[remaining[0]]
            remaining = remaining[1:]
        elif remaining.startswith("VC"):
            intensity = WX_INTENSITY["VC"]
            remaining = remaining[2:]

        descriptor = ""
        for code, text in WX_DESCRIPTOR.items():
            if remaining.startswith(code):
                descriptor = text
                remaining = remaining[len(code):]
                break

        phenomena = []
        while len(remaining) >= 2:
            code = remaining[:2]
            phenomena.append(WX_PHENOMENON.get(code, code))
            remaining = remaining[2:]

        parts = [p for p in [intensity, descriptor, " and ".join(phenomena)] if p]
        if parts:
            phrases.append(" ".join(parts))

    return phrases


def _build_summary(temp_f, wind_text, sky_descriptions, weather_phrases) -> str:
    if weather_phrases:
        condition = weather_phrases[0].capitalize()
    elif sky_descriptions:
        condition = sky_descriptions[0]
    else:
        condition = "Conditions unavailable"

    summary = condition
    if temp_f is not None:
        summary += f", {temp_f}°F"
    summary += f", {wind_text[0].lower()}{wind_text[1:]}"
    return summary


def decode_metar(data: dict) -> dict:
    """Turn a raw METAR JSON record into a plain-English weather report."""
    temp_c = data.get("temp")
    dewp_c = data.get("dewp")
    temp_f = _celsius_to_fahrenheit(temp_c) if temp_c is not None else None
    dewp_f = _celsius_to_fahrenheit(dewp_c) if dewp_c is not None else None

    wind_text = _decode_wind(data)
    visibility_text = _decode_visibility(data)
    sky_descriptions = _decode_clouds(data)
    weather_phrases = _decode_weather_string(data.get("wxString", ""))

    altim_hpa = data.get("altim")
    pressure_text = None
    if altim_hpa is not None:
        pressure_text = f"{_hpa_to_inhg(altim_hpa)} inHg ({round(altim_hpa, 1)} hPa)"

    obs_time = None
    if data.get("obsTime"):
        obs_time = datetime.fromtimestamp(data["obsTime"], tz=timezone.utc)

    flight_category = data.get("fltCat")

    return {
        "station": data.get("icaoId", "Unknown"),
        "station_name": data.get("name", ""),
        "observed_at": obs_time.strftime("%Y-%m-%d %H:%M UTC") if obs_time else "Unknown",
        "summary": _build_summary(temp_f, wind_text, sky_descriptions, weather_phrases),
        "temperature_f": temp_f,
        "temperature_c": temp_c,
        "dewpoint_f": dewp_f,
        "dewpoint_c": dewp_c,
        "wind": wind_text,
        "visibility": visibility_text,
        "sky_conditions": sky_descriptions,
        "weather_phrases": [p.capitalize() for p in weather_phrases],
        "pressure": pressure_text,
        "flight_category": flight_category,
        "flight_category_text": FLIGHT_CATEGORY.get(flight_category, "Unknown"),
        "raw_metar": data.get("rawOb", ""),
    }


def get_decoded_metar(airport_code: str) -> dict:
    """Fetch and decode a METAR report for the given airport code."""
    raw_data = fetch_metar(airport_code)
    return decode_metar(raw_data)
