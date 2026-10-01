from flask import Flask, request, make_response, render_template_string, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'miyove_secret_secure_key_123' # Gucunga session z'abarinze kwinjira

# 🔒 DATABASE SETTING
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///miyove_farm_secure_v2.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 🗄️ DATABASE MODELS (ORM Layer)
class Umuhinzi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telephone = db.Column(db.String(20), nullable=False)
    indangamuntu = db.Column(db.String(20), nullable=False) # Inimero y'indangamuntu
    igihingwa = db.Column(db.String(50), nullable=False)
    ibiro = db.Column(db.String(20), nullable=False)
    igiciro = db.Column(db.String(20), nullable=False)

class UmuguziUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Kora Database na User w'igerageza mu mutekano
with app.app_context():
    db.create_all()
    # Kora admin user w'ubuguzi niba adahari (Username: admin, Password: adminMiyove123)
    if not UmuguziUser.query.filter_by(username='admin').first():
        hashed_password = generate_password_hash('adminMiyove123', method='pbkdf2:sha256')
        admin_user = UmuguziUser(username='admin', password=hashed_password)
        db.session.add(admin_user)
        db.session.commit()

# 🌐 1. WEB: LOGIN PAGE (Kurwanya ubujura)
@app.route("/login", methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = UmuguziUser.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('web_dashboard'))
        else:
            error = "Izina cyangwa Password sbyo! Ongera ugerageze."
            
    html_login = """
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Login - E-Muhinzi</title></head>
    <body style="font-family:sans-serif; background-color:#eec; padding:100px; text-align:center;">
        <div style="max-width:400px; margin:0 auto; background:white; padding:30px; border-radius:8px; box-shadow:0 4px 10px rgba(0,0,0,0.1);">
            <h2>Kwinjira muri E-Muhinzi 🔒</h2>
            {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
            <form method="POST">
                <input type="text" name="username" placeholder="Izina (Username)" style="width:90%; padding:10px; margin:10px 0;" required><br>
                <input type="password" name="password" placeholder="Ijambo ry'ibanga" style="width:90%; padding:10px; margin:10px 0;" required><br>
                <button type="submit" style="width:95%; padding:10px; background:#27ae60; color:white; border:none; border-radius:4px; font-weight:bold; cursor:pointer;">Ingira</button>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_login, error=error)

# 🌐 2. WEB: SECURE DASHBOARD FOR BUYERS
@app.route("/", methods=['GET', 'POST'])
def web_dashboard():
    if request.method == 'POST':
        return ussd_gateway(request)
        
    # Reba niba umuguzi yabanje kwinjira (Security Check)
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    abahinzi_bose = Umuhinzi.query.order_by(Umuhinzi.id.desc()).all()
    html_dashboard = """
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>E-Muhinzi Miyove</title></head>
    <body style="font-family:sans-serif; background:#f4f7f6; padding:20px;">
        <div style="max-width:900px; margin:0 auto; background:white; padding:30px; border-radius:8px;">
            <div style="display:flex; justify-content:between; align-items:center;">
                <h2>Sizitemu y'Abahinzi b'i Miyove 🌾</h2>
                <a href="/logout" style="color:red; text-decoration:none; font-weight:bold;">Sohoka (Logout)</a>
            </div>
            <p style="color:#7f8c8d;">Urubuga rurinzwe. Abaguzi bemewe gusa nibo babona aya makuru.</p>
            <table style="width:100%; border-collapse:collapse; margin-top:20px;">
                <tr style="background:#27ae60; color:white;">
                    <th style="padding:12px; text-align:left;">Indangamuntu (ID)</th>
                    <th style="padding:12px; text-align:left;">Igihingwa</th>
                    <th style="padding:12px; text-align:left;">Ibiro (Kg)</th>
                    <th style="padding:12px; text-align:left;">Igiciro</th>
                    <th style="padding:12px; text-align:left;">Telefone</th>
                </tr>
                {% for u in abahinzi %}
                <tr style="border-bottom:1px solid #ddd;">
                    <td style="padding:12px; color:#c0392b;"><b>{{ u.indangamuntu }}</b></td>
                    <td style="padding:12px;">{{ u.igihingwa }}</td>
                    <td style="padding:12px;">{{ u.ibiro }} Kg</td>
                    <td style="padding:12px;">{{ u.igiciro }} Frw</td>
                    <td style="padding:12px;"><a href="tel:{{ u.telephone }}">{{ u.telephone }}</a></td>
                </tr>
                {% else %}
                <tr><td colspan="5" style="text-align:center; padding:20px; color:#95a5a6;">Nta musaruro urandikwa mu madata.</td></tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_dashboard, abahinzi=abahinzi_bose)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# 📱 3. USSD GATEWAY WITH ID CHECK (Umutekano kuri Terefone)
def ussd_gateway(req):
    phone_number = req.values.get("phoneNumber", None)
    text = req.values.get("text", "")
    steps = text.split('*') if text else []
    
    # Paji ya 1
    if text == "":
        response = "CON Ikaze kwa Muhinzi-Digital Miyove!\n1. Gisha Umusaruro\n2. Reba Ibihingwa Bihari"
        
    # Paji ya 2: Guhitamo Gisha Umusaruro -> Guhita baka Indangamuntu
    elif text == "1":
        response = "CON Injiza Inimero y'Indangamuntu yawe (imibare 16):"
        
    # Paji ya 3: Amaze kwandika Indangamuntu -> Baka Igihingwa
    elif len(steps) == 2 and steps[0] == "1":
        id_number = steps[1].strip()
        # Kwemezako indangamuntu ifite imibare 16 (Basic Validation)
        if len(id_number) != 16 or not id_number.isdigit():
            response = "END Indangamuntu sbyo! Imibare igomba kuba 16. Ongera ugerageze kandi."
        else:
            response = "CON Injiza igihingwa (Urugero: Ibirayi, Ikawa):"
            
    # Paji ya 4: Baka Ibiro
    elif len(steps) == 3 and steps[0] == "1":
        response = f"CON Injiza ibiro (Kg) by'ubwo {steps[2]} ufite:"
        
    # Paji ya 5: Baka Igiciro
    elif len(steps) == 4 and steps[0] == "1":
        response = "CON Igiciro ku kilo kimwe ni Frw zingahe?"
        
    # Paji ya 6: KUBIKA MURI DATABASE Y'UMUTEKANO
    elif len(steps) == 5 and steps[0] == "1":
        indangamuntu = steps[1].strip()
        igihingwa = steps[2].strip()
        ibiro = steps[3].strip()
        igiciro = steps[4].strip()
        
        mushya = Umuhinzi(telephone=phone_number, indangamuntu=indangamuntu, igihingwa=igihingwa, ibiro=ibiro, igiciro=igiciro)
        db.session.add(mushya)
        db.session.commit()
        
        response = f"END Murakoze! Umusaruro wanyu winjiye mu buryo bw'umutekano n'Indangamuntu: {indangamuntu}."
        
    # Kureba amakuru (Kanda 2)
    elif text == "2":
        bose = Umuhinzi.query.order_by(Umuhinzi.id.desc()).limit(5).all()
        if not bose:
            response = "END Nta muhinzi urandikisha umusaruro uyu munsi."
        else:
            response = "CON Ibihingwa bihari:\n"
            for u in bose:
                response += f"- {u.igihingwa}: {u.ibiro}Kg (Tel: {u.telephone})\n"
            response += "\n0. Subira inyuma"
    elif text == "2*0":
        response = "CON Ikaze kwa Muhinzi-Digital Miyove!\n1. Gisha Umusaruro\n2. Reba Ibihingwa Bihari"
    else:
        response = "END Guhitamo siko. Ongera ugerageze kandi!"

    resp = make_response(response, 200)
    resp.headers['Content-Type'] = 'text/plain'
    return resp

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
