# METAR Reader

A small Flask web app that turns cryptic airport weather reports
(METARs) into plain English.

Type in an airport code — for example `KHIO`, `KJFK`, or `KDEN` — and
the app fetches the latest METAR from the [National Weather Service's
Aviation Weather Center](https://aviationweather.gov/) and decodes it
into a friendly summary, such as:

> Overcast at 2,200 feet, 63.0°F, wind blowing from variable
> directions at 3.5 mph

## Features

- Look up any airport with a published METAR by its ICAO code
  (e.g. `KHIO`, `KSEA`, `KMIA`).
- Plain-English decoding of:
  - Temperature and dew point (°F and °C)
  - Wind direction and speed, including gusts
  - Visibility
  - Sky conditions / cloud layers
  - Weather phenomena (rain, snow, fog, thunderstorms, etc.)
  - Barometric pressure
  - Flight category (VFR / MVFR / IFR / LIFR)
- The original raw METAR is still shown for reference.
- A simple JSON API endpoint (`/api/metar/<code>`) for programmatic use.
- Friendly error messages for invalid or unknown airport codes.

## How it works

The app calls the public
[aviationweather.gov data API](https://aviationweather.gov/data/api/)
for the requested airport code and receives the observation as
structured JSON. `metar_decoder.py` translates the coded fields
(wind direction in degrees, cloud cover abbreviations, weather
phenomena codes, etc.) into readable sentences, which `app.py` renders
through a Flask template.

## Requirements

- Python 3.9+
- Internet access (to reach aviationweather.gov)

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/jagracia19/METARReader.git
   cd KodeKloud-METAR-Reader
   ```

2. **Create and activate a virtual environment**

   On macOS/Linux:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

   On Windows (PowerShell):

   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**

   ```bash
   python app.py
   ```

5. Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## Usage

Enter an airport's ICAO code (e.g. `KHIO` for Portland-Hillsboro, OR)
into the search box and click **Get Weather**. The decoded report
appears below the form, with the raw METAR available under "Show raw
METAR" for comparison.

### JSON API

You can also query the decoded report directly:

```bash
curl http://127.0.0.1:5000/api/metar/KHIO
```

This returns a JSON object with the same fields shown on the web page
(temperature, wind, visibility, sky conditions, pressure, etc.), or a
`404` with an `"error"` message if the airport code is invalid or has
no current report.

## Running the tests

Unit tests cover the METAR decoding logic (using mock weather records)
and the Flask routes (with the decoder mocked out, so no real network
calls are made).

```bash
pip install -r requirements-dev.txt
pytest
```

## Project structure

```
.
├── app.py                    # Flask routes (web form + JSON API)
├── metar_decoder.py          # Fetches METARs and decodes them into plain English
├── requirements.txt          # Python dependencies
├── requirements-dev.txt      # Additional dependencies for running tests
├── conftest.py                # Shared pytest fixtures (Flask test client)
├── tests/
│   ├── test_metar_decoder.py # Decoding logic tests, using mock METAR records
│   └── test_app.py           # Flask route tests
├── templates/
│   └── index.html            # Search form and results page
└── static/
    └── style.css              # Page styling
```

## Notes

- This app depends on the free, public aviationweather.gov API and
  has no API key requirement, but that also means it's subject to
  that service's availability and rate limits.
- `app.py` runs Flask's built-in development server with
  `debug=True`. This is convenient for local use but should **not**
  be used as-is in production — use a production WSGI server (e.g.
  Gunicorn or Waitress) and disable debug mode if you deploy this
  publicly.

## License

This project is licensed under the [MIT License](LICENSE).
