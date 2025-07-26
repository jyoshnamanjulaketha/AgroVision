from flask import Flask, request, render_template, redirect, url_for, session, flash, jsonify
import sqlite3
import secrets
import os
import numpy as np
import pandas as pd
import pickle
import warnings
from sklearn.exceptions import InconsistentVersionWarning
import smtplib
from email.message import EmailMessage

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=InconsistentVersionWarning)

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Initialize the database
def initialize_db():
    db_file = 'users.db'
    if not os.path.exists(db_file):
        conn = sqlite3.connect(db_file)
        with conn:
            conn.execute('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
            ''')
        print("Database initialized")
    else:
        print("Database already exists")

initialize_db()

def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and user['password'] == password:
            session['user_id'] = user['id']
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))

    return render_template('signin.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            conn.close()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists. Please choose a different username.', 'error')
            conn.close()

    return render_template('signup.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (email,)).fetchone()
        conn.close()

        if user:
            temp_password = secrets.token_hex(3)
            conn = get_db_connection()
            conn.execute('UPDATE users SET password = ? WHERE username = ?', (temp_password, email))
            conn.commit()
            conn.close()

            # Send email with temporary password
            try:
                sender_email = '22b01a4542@svecw.edu.in'
                sender_password = 'SVECW@2022'
                msg = EmailMessage()
                msg.set_content(f'Your temporary password is: {temp_password}')
                msg['Subject'] = 'Password Reset Request'
                msg['From'] = sender_email
                msg['To'] = email

                with smtplib.SMTP('smtp.gmail.com', 587) as server:
                    server.starttls()
                    server.login(sender_email, sender_password)
                    server.send_message(msg)

                flash('Temporary password sent to your email. Please check your inbox.', 'info')
            except Exception as e:
                flash('Error sending email. Please try again later.', 'error')

            return redirect(url_for('login'))
        else:
            flash('Email address not found', 'error')

    return render_template('forgot_password.html')

@app.route('/home')
def home():
    if 'user_id' in session:
        return render_template('home.html')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Load models and data
model = pickle.load(open('model.pkl', 'rb'))
sc = pickle.load(open('standscaler.pkl', 'rb'))
mx = pickle.load(open('minmaxscaler.pkl', 'rb'))
dtr = pickle.load(open('dtr.pkl', 'rb'))
preprocessor = pickle.load(open('preprocesser.pkl', 'rb'))

with open('state_district.pkl', 'rb') as f:
    state_district = pickle.load(f)

df_commodity = pd.read_csv("Commodity_prices.csv")
df_crop = pd.read_csv("Crop_recommendation11.csv")
df_rainfall = pd.read_csv("district wise rainfall normal.csv")

# Preprocess the crop data to match commodity data labels
df_crop["label"] = df_crop["label"].replace(
    ["rice", "papaya", "watermelon", "muskmelon", "apple", "orange", "coconut", "jute", "grapes", "mango", "banana",
     "pomegranate", "lentil", "blackgram", "maize", "mungbean", "mothbeans", "coffee", "cotton", "pigeonpeas",
     "kidneybeans", "chickpea"],
    ["Rice", "Papaya", "Water Melon", "Karbuja(Musk Melon)", "Apple", "Orange", "Coconut", "Jute", "Grapes", "Mango",
     "Banana", "Pomegranate", "Lentil (Masur)(Whole)", "Black Gram (Urd Beans)(Whole)", "Maize", 
     "Green Gram (Moong)(Whole)", "Moath Dal", "Tomato", "Cotton", "Pegeon Pea (Arhar Fali)", 
     "Niger Seed (Ramtil)", "Bengal Gram Dal (Chana Dal)"])
Crops = df_crop["label"].unique()

df_commodity = df_commodity[df_commodity["commodity"].isin(Crops)]

# Replace with your actual API key
API_KEY = '3846124984401b8fde0f76aa37362bba'
BASE_URL = 'http://api.openweathermap.org/data/2.5/weather'

@app.route('/')
def index():
    if 'user_id' in session:
        return render_template('home.html')
    return redirect(url_for('login'))

@app.route('/crop_recommendation')
def crop_recommendation():
    if 'user_id' in session:
        return render_template("index.html")
    return redirect(url_for('login'))

@app.route('/crop_prediction')
def crop_prediction():
    if 'user_id' in session:
        return render_template("web.html")
    return redirect(url_for('login'))

@app.route('/crop_prediction_rainfall')
def crop_prediction_rainfall():
    if 'user_id' in session:
        states = sorted(state_district.keys())
        return render_template('index1.html', states=states)
    return redirect(url_for('login'))

@app.route('/get_districts', methods=['POST'])
def get_districts():
    state = request.form['state']
    districts = state_district.get(state, [])
    return jsonify(districts)

@app.route("/predict_recommendation", methods=['POST'])
def predict_recommendation():
    if 'user_id' in session:
        N = request.form['Nitrogen']
        P = request.form['Phosphorus']
        K = request.form['Potassium']
        temp = request.form['Temperature']
        humidity = request.form['Humidity']
        ph = request.form['pH']
        rainfall = request.form['Rainfall']

        feature_list = [N, P, K, temp, humidity, ph, rainfall]
        single_pred = np.array(feature_list).reshape(1, -1)

        mx_features = mx.transform(single_pred)
        sc_mx_features = sc.transform(mx_features)
        prediction = model.predict(sc_mx_features)

        crop_dict = {0: "Rice", 1: "Maize", 2: "Jute", 3: "Cotton", 4: "Coconut", 5: "Papaya", 
                     6: "Orange", 7: "Apple", 8: "Muskmelon", 9: "Watermelon", 10: "Grapes", 
                     11: "Mango", 12: "Banana", 13: "Pomegranate", 14: "Lentil", 
                     15: "Blackgram", 16: "Mungbean", 17: "Mothbeans", 18: "Pigeonpeas", 
                     19: "Kidneybeans", 20: "Chickpea", 21: "Coffee"}

        if prediction[0] in crop_dict:
            crop = crop_dict[prediction[0]]
            result = "{} is the best crop to be cultivated right there".format(crop)
        else:
            result = "Sorry, we could not determine the best crop to be cultivated with the provided data."
        return render_template('index.html', result=result)
    return redirect(url_for('login'))

@app.route("/predict_crop", methods=['POST'])
def predict_crop():
    if 'user_id' in session:
        if request.method == 'POST':
            Year = request.form['Year']
            average_rain_fall_mm_per_year = request.form['average_rain_fall_mm_per_year']
            pesticides_tonnes = request.form['pesticides_tonnes']
            avg_temp = request.form['avg_temp']
            Area = request.form['Area']
            Item = request.form['Item']

            features = np.array([[Year, average_rain_fall_mm_per_year, pesticides_tonnes, avg_temp, Area, Item]], dtype=object)
            transformed_features = preprocessor.transform(features)
            prediction = dtr.predict(transformed_features).reshape(1, -1)

            return render_template('web.html', prediction=prediction[0][0])
    return redirect(url_for('login'))

@app.route('/results', methods=['POST'])
def results():
    state = request.form['state']
    district = request.form['district']
    season = request.form['season']

    # Extract rainfall data for the district and season
    test_rainfall = df_rainfall[df_rainfall["DISTRICT"] == district][season].to_numpy()
    test = test_rainfall / 2  # Adjust as needed

    # Convert crop data to numpy array
    dataset = df_crop.to_numpy()

    # Define KNN functions
    def euclidean_distance(row1, row2):
        distance = (row1[0] - row2[6]) ** 2
        return np.sqrt(distance)

    def get_neighbors(train, test_row, num_neighbors):
        distances = [(train_row, euclidean_distance(test_row, train_row)) for train_row in train]
        distances.sort(key=lambda tup: tup[1])
        neighbors = [distances[i][0] for i in range(num_neighbors)]
        return neighbors

    # Find neighbors and predict crops
    neighbors = get_neighbors(dataset, test, 100)
    pred = [neighbor[-1] for neighbor in neighbors]
    unique_crops = np.unique(pred)

    # Collect commodity data for the predicted crops
    crop_info = {}
    for crop in unique_crops:
        crop_data = df_commodity[df_commodity["commodity"] == crop]
        max_val = crop_data["max_price"].max()
        min_val = crop_data["min_price"].max()
        min_modal_price = crop_data["modal_price"].min()
        max_modal_price = crop_data["modal_price"].max()
        avg_modal_price = crop_data["modal_price"].mean()
        crop_info[crop] = {
            "Max Val": max_val,
            "Min Val": min_val,
            "Min Modal Price": min_modal_price,
            "Max Modal Price": max_modal_price,
            "Avg Modal Price": avg_modal_price
        }

    # Convert the crop_info dictionary to a DataFrame and sort by Avg Modal Price
    df_results = pd.DataFrame.from_dict(crop_info).transpose()
    df_sorted_results = df_results.sort_values("Avg Modal Price", ascending=False)

    return render_template('results.html', crop_info=df_sorted_results.to_dict('index'))

if __name__ == '__main__':
    app.run(debug=True)
