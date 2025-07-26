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
                    email TEXT UNIQUE NOT NULL,
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
        username = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (username,)).fetchone()
        conn.close()

        if user and user['password'] == password:
            session['user_id'] = user['id']
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))

    return render_template('signin.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, password))
            conn.commit()
            conn.close()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists. Please choose a different email.', 'error')
            conn.close()

    return render_template('signup.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user:
            temp_password = secrets.token_hex(3)
            conn = get_db_connection()
            conn.execute('UPDATE users SET password = ? WHERE email = ?', (temp_password, email))
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

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        current_password = request.form['current_password']  # Changed from old_password
        new_password = request.form['new_password']
        confirm_new_password = request.form['confirm_new_password']

        # Check if new passwords match
        if new_password != confirm_new_password:
            flash('New passwords do not match', 'error')
            return redirect(url_for('change_password'))

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

        if user and user['password'] == current_password:
            conn.execute('UPDATE users SET password = ? WHERE id = ?', (new_password, session['user_id']))
            conn.commit()
            conn.close()
            flash('Password updated successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Current password is incorrect', 'error')
            conn.close()

    return render_template('change_password.html')



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
# Load models and data
model = pickle.load(open('model.pkl', 'rb'))
sc = pickle.load(open('standscaler.pkl', 'rb'))
mx = pickle.load(open('minmaxscaler.pkl', 'rb'))
dtr = pickle.load(open('dtr.pkl', 'rb'))
preprocessor = pickle.load(open('preprocesser.pkl', 'rb'))


# Fertilizer prediction model
fertilizer_model = pickle.load(open('classifier.pkl', 'rb'))
fertilizer_classifier = pickle.load(open('fertilizer.pkl', 'rb'))



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

       # Define English and Telugu crop names
        crop_dict = {
            0: ("Rice", "వరి"),
            1: ("Maize", "మొక్కజొన్న"),
            2: ("Jute", "జూట్"),
            3: ("Cotton", "పత్తి"),
            4: ("Coconut", "కొబ్బరి"),
            5: ("Papaya", "బొప్పాయి"),
            6: ("Orange", "నారింజ"),
            7: ("Apple", "ఆపిల్"),
            8: ("Muskmelon", "కర్బూజ"),
            9: ("Watermelon", "పుచ్చకాయ"),
            10: ("Grapes", "ద్రాక్ష"),
            11: ("Mango", "మామిడి"),
            12: ("Banana", "అరటి"),
            13: ("Pomegranate", "దానిమ్మ"),
            14: ("Lentil", "మసూరి పప్పు"),
            15: ("Blackgram", "మినుము"),
            16: ("Mungbean", "పెసర పప్పు"),
            17: ("Mothbeans", "మోత్ పప్పు"),
            18: ("Pigeonpeas", "కందులు"),
            19: ("Kidneybeans", "రాజ్మా"),
            20: ("Chickpea", "సెనగలు"),
            21: ("Coffee", "కాఫీ")
        }


        if prediction[0] in crop_dict:
            crop_eng, crop_tel = crop_dict[prediction[0]]
            result = f"{crop_eng} ({crop_tel}) is the best crop to be cultivated right there."
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

@app.route("/predict_fertilizer", methods=['GET', 'POST'])
def predict_fertilizer():
    if 'user_id' in session:
        prediction = None
        error = None

        if request.method == 'POST':
            try:
                # Get the form data from the POST request and convert to appropriate types
                temp = float(request.form.get('temp'))
                humi = float(request.form.get('humid'))
                mois = float(request.form.get('mois'))
                soil = int(request.form.get('soil'))
                crop = int(request.form.get('crop'))
                nitro = float(request.form['nitro'])
                pota = float(request.form['pota'])
                phos = float(request.form['phos'])

                # Fertilizer mapping
                fertilizer_mapping = {
                    0: "10-26-26",
                    1: "14-35-14",
                    2: "17-17-17",
                    3: "20-20",
                    4: "28-28",
                    5: "DAP",
                    6: "Urea"
                }

                # Prepare the input data
                data = np.array([[temp, humi, mois, soil, crop, nitro, pota, phos]])

                # Predict using the model
                pred = fertilizer_model.predict(data)[0]

                # Map the prediction to fertilizer name
                prediction = fertilizer_mapping.get(pred, "Unknown Fertilizer")

            except Exception as e:
                # Handle errors and provide meaningful feedback
                error = f"An error occurred: {e}"

        # Render the input page with prediction or error
        return render_template(
            'fertilizer_result.html',
            prediction=prediction,
            error=error
        )

    # Redirect to login page if user is not logged in
    return redirect(url_for('login'))



if __name__ == '__main__':
    app.run(debug=True)

