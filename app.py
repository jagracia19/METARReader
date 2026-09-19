from flask import Flask, jsonify, render_template, request

from metar_decoder import MetarError, get_decoded_metar

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    report = None
    error = None
    airport_code = ""

    if request.method == "POST":
        airport_code = request.form.get("airport_code", "")
        try:
            report = get_decoded_metar(airport_code)
        except MetarError as exc:
            error = str(exc)

    return render_template(
        "index.html", report=report, error=error, airport_code=airport_code
    )


@app.route("/api/metar/<airport_code>")
def api_metar(airport_code):
    try:
        report = get_decoded_metar(airport_code)
    except MetarError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(report)


if __name__ == "__main__":
    app.run(debug=True)
