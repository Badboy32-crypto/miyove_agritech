from flask import Flask, request, make_response, render_template_string
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# 🔒 DATABASE SETTING (SQLite file idasibana)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///miyove_farm_secure.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 🗄️ DATABASE TABLE
class Umuhinzi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telephone = db.Column(db.String(20), nullable=False)
    igihingwa = db.Column(db.String(50), nullable=False)
    ibiro = db.Column(db.String(20), nullable=False)
    igiciro = db.Column(db.String(20), nullable=False)

with app.app_context():
    db.create_all()

# 🌐 1. WEB DASHBOARD (Chrome / Edge Browser)
@app.route("/", methods=['GET', 'POST'])
def web_dashboard():
    if request.method == 'POST':
        return ussd_gateway(request)
        
    abahinzi_bose = Umuhinzi.query.order_by(Umuhinzi.id.desc()).all()
    html_template = """
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>E-Muhinzi Miyove</title></head>
    <body style="font-family:sans-serif; background:#f4f7f6; padding:20px;">
        <div style="max-width:800px; margin:0 auto; background:white; padding:30px; border-radius:8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h1 style="text-align:center; color:#2c3e50;">Sizitemu y'Abahinzi b'i Miyove 🌾</h1>
            <p style="text-align:center; color:#7f8c8d;">Urubuga rw'Abaguzi rwerekana umusaruro winjijwe binyuze kuri USSD</p>
            <table style="width:100%; border-collapse:collapse; margin-top:20px;">
                <tr style="background:#27ae60; color:white;">
                    <th style="padding:12px; text-align:left;">Igihingwa</th>
                    <th style="padding:12px; text-align:left;">Ibiro (Kg)</th>
                    <th style="padding:12px; text-align:left;">Igiciro (Frw/Kg)</th>
                    <th style="padding:12px; text-align:left;">Telefone y'Umuhinzi</th>
                </tr>
                {% for u in abahinzi %}
                <tr style="border-bottom:1px solid #ddd;">
                    <td style="padding:12px;"><b>{{ u.igihingwa }}</b></td>
                    <td style="padding:12px;">{{ u.ibiro }} Kg</td>
                    <td style="padding:12px;">{{ u.igiciro }} Frw</td>
                    <td style="padding:12px;"><a href="tel:{{ u.telephone }}">{{ u.telephone }}</a></td>
                </tr>
                {% else %}
                <tr><td colspan="4" style="text-align:center; color:#95a5a6; padding:20px;">Nta muhinzi urashira umusaruro ku isoko.</td></tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, abahinzi=abahinzi_bose)

# 📱 2. USSD LOGIC (Africa's Talking Gateway)
def ussd_gateway(req):
    phone_number = req.values.get("phoneNumber", None)
    text = req.values.get("text", "")
    steps = text.split('*') if text else []
    
    # Intambwe ya 1: Paji ya mbere
    if text == "":
        response = "CON Ikaze kwa Muhinzi-Digital Miyove!\n1. Gisha Umusaruro\n2. Reba Ibihingwa Bihari"
        
    # Intambwe ya 2: Yahisemo Gisha Umusaruro (Kanda 1)
    elif text == "1":
        response = "CON Injiza igihingwa (Urugero: Ibirayi, Ikawa):"
        
    # Intambwe ya 3: Amaze kwandika izina ry'igihingwa (Urugero: 1*Ibirayi)
    elif len(steps) == 2 and steps[0] == "1":
        response = f"CON Injiza ibiro (Kg) by'ubwo {steps[1]} ufite:"
        
    # Intambwe ya 4: Amaze kwandika ibiro (Urugero: 1*Ibirayi*500)
    elif len(steps) == 3 and steps[0] == "1":
        response = f"CON Igiciro ku kilo kimwe ni Frw zingahe?"
        
    # Intambwe ya 5: Amaze kwandika igiciro -> KUBIKA MURI DATABASE!
    elif len(steps) == 4 and steps[0] == "1":
        igihingwa = steps[1].strip()
        ibiro = steps[2].strip()
        igiciro = steps[3].strip()
        
        # Kubika mu buryo bw'umutekano muri SQLite
        mushya = Umuhinzi(telephone=phone_number, igihingwa=igihingwa, ibiro=ibiro, igiciro=igiciro)
        db.session.add(mushya)
        db.session.commit()
        
        response = f"END Murakoze! Umusaruro wanyu ({ibiro}Kg z'{igihingwa} kuri {igiciro}Frw/Kg) winjiye mu buryo bw'umutekano. Abaguzi baragushaka kuri {phone_number}."
        
    # Intambwe ya 6: Yahisemo Reba Ibihingwa Bihari (Kanda 2)
    elif text == "2":
        bose = Umuhinzi.query.order_by(Umuhinzi.id.desc()).limit(5).all()
        if not bose:
            response = "END Nta muhinzi urandikisha umusaruro uyu munsi. Garuka mu kanya!"
        else:
            response = "CON Ibihingwa bihari muri Database:\n"
            for u in bose:
                response += f"- {u.igihingwa}: {u.ibiro}Kg, {u.igiciro}Frw (Tel: {u.telephone})\n"
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
