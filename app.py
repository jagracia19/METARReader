"""Flask application for the METAR Reader.

Exposes a small web UI and a JSON API that let a user look up an
airport's current METAR weather observation and read it back as a
plain-English summary instead of the raw, coded report.
"""

from flask import Flask, jsonify, render_template, request

from metar_decoder import MetarError, get_decoded_metar

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    """Render the search form and, on submit, the decoded weather report.

    GET requests show an empty search form. POST requests read the
    submitted airport code, fetch and decode its METAR, and re-render
    the same page with either the report or a user-friendly error
    message.
    """
    report = None
    error = None
    airport_code = ""

    if request.method == "POST":
        airport_code = request.form.get("airport_code", "")
        try:
            report = get_decoded_metar(airport_code)
        except MetarError as exc:
            # Expected failures (bad code, no station, upstream API issue)
            # are shown to the user instead of raising a 500 error.
            error = str(exc)

    return render_template(
        "index.html", report=report, error=error, airport_code=airport_code
    )


@app.route("/api/metar/<airport_code>")
def api_metar(airport_code):
    """Return the decoded METAR report for an airport code as JSON.

    Args:
        airport_code: ICAO airport identifier from the URL path, e.g. "KHIO".

    Returns:
        A JSON body of the decoded report on success, or
        ``{"error": "..."}`` with a 404 status if the code is invalid
        or no station could be found.
    """
    try:
        report = get_decoded_metar(airport_code)
    except MetarError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(report)


if __name__ == "__main__":
    # debug=True enables the auto-reloader and interactive debugger for
    # local development. Do not use it when running in production.
    app.run(debug=True)
