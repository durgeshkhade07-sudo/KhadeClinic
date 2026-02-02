import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from fpdf import FPDF

app = Flask(__name__)

# --- Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///khade_clinic.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)
db = SQLAlchemy(app)

if not os.path.exists('prescriptions'):
    os.makedirs('prescriptions')

# --- Database Models ---
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), unique=True, nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))
    department = db.Column(db.String(50))
    token_number = db.Column(db.Integer)
    date = db.Column(db.Date, default=datetime.utcnow().date())

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

@app.route('/book', methods=['POST'])
def book():
    data = request.json
    patient = Patient.query.filter_by(mobile=data['mobile']).first()
    
    if not patient:
        patient = Patient(
            name=data['name'], 
            mobile=data['mobile'], 
            age=data['age'], 
            gender=data['gender']
        )
        db.session.add(patient)
    else:
        patient.age = data['age']
        patient.gender = data['gender']
    
    db.session.commit()
    
    today = datetime.utcnow().date()
    token = Appointment.query.filter_by(date=today, department=data['department']).count() + 1
    new_app = Appointment(patient_id=patient.id, department=data['department'], token_number=token)
    db.session.add(new_app)
    db.session.commit()
    return jsonify({"token": token, "patient": patient.name, "dept": data['department']})

@app.route('/api/appointments')
def get_apps():
    today = datetime.utcnow().date()
    apps = db.session.query(Appointment, Patient).join(Patient).filter(Appointment.date == today).all()
    return jsonify([{
        "id": a.id, 
        "token": a.token_number, 
        "name": p.name, 
        "age": p.age, 
        "gender": p.gender, 
        "dept": a.department
    } for a, p in apps])

@app.route('/api/complete/<int:id>', methods=['DELETE'])
def complete(id):
    app_to_del = Appointment.query.get(id)
    if app_to_del:
        db.session.delete(app_to_del)
        db.session.commit()
    return jsonify({"status": "done"})

@app.route('/generate_pdf/<int:token>')
def generate_pdf(token):
    appt = Appointment.query.filter_by(token_number=token).first()
    patient = Patient.query.get(appt.patient_id)
    pdf = FPDF()
    pdf.add_page()
    
    # Professional Header
    pdf.set_fill_color(0, 74, 153)
    pdf.rect(0, 0, 210, 50, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 24)
    pdf.cell(200, 20, txt="KHADE CLINIC", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt="Main Road, Bank of India Bhiwapur 441201 | Helpline: 7709851625", ln=True, align='C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", size=12)
    pdf.ln(35)
    pdf.cell(200, 10, txt=f"Patient: {patient.name} ({patient.age}Y, {patient.gender})", ln=True)
    pdf.cell(200, 10, txt=f"Token: {token} | Dept: {appt.department}", ln=True)
    pdf.cell(200, 10, txt=f"Date: {appt.date}", ln=True)
    
    file_path = f"prescriptions/token_{token}.pdf"
    pdf.output(file_path)
    return send_from_directory('prescriptions', f"token_{token}.pdf")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)