from flask import Flask, request, render_template, jsonify
from datetime import datetime, timedelta
import requests

app = Flask(__name__)  # Corrected this line

API_KEY = "09f8d2e5a2a3468b8cf10657250601"
BASE_URL = "https://api.weatherapi.com/v1/history.json"

def fetch_weather_data(location, start_date, end_date):
    current_date = start_date
    temp_sum = humidity_sum = rainfall_sum = 0
    count = 0

    while current_date <= end_date:
        formatted_date = current_date.strftime("%Y-%m-%d")
        response = requests.get(
            BASE_URL,
            params={
                "key": API_KEY,
                "q": location,
                "dt": formatted_date,
            },
            verify=False
        )

        if response.status_code == 200:
            data = response.json()
            day_data = data.get("forecast", {}).get("forecastday", [])[0].get("day", {})
            temp_sum += day_data.get("avgtemp_c", 0)
            humidity_sum += day_data.get("avghumidity", 0)
            rainfall_sum += day_data.get("totalprecip_mm", 0)
            count += 1
        else:
            print(f"Error fetching data for {formatted_date}: {response.status_code}, {response.text}")
        current_date += timedelta(days=1)

    if count == 0:
        return None

    avg_temp = temp_sum / count
    avg_humidity = humidity_sum / count
    avg_rainfall = rainfall_sum / count

    return {
        "average_temperature": avg_temp,
        "average_humidity": avg_humidity,
        "average_rainfall": avg_rainfall
    }

@app.route("/")
def home():
    return render_template("weather_form.html")

@app.route("/fetch_weather", methods=["POST"])
def fetch_weather():
    location = request.form.get("location")
    reference_date = datetime.strptime(request.form.get("date"), "%Y-%m-%d")
    six_months_ago = reference_date - timedelta(days=6 * 30)

    weather_data = fetch_weather_data(location, six_months_ago, reference_date)
    if weather_data:
        return jsonify(weather_data)
    else:
        return "No weather data available for the given range.", 404

if __name__ == "__main__":  # Corrected this line
    app.run(debug=True)
