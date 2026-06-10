from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'livestock_dss_secret_key_2024')

# ── Database: use PostgreSQL on Render, SQLite locally ──
DATABASE_URL = os.environ.get('DATABASE_URL', '')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL if DATABASE_URL else 'sqlite:///livestock.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ─────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Livestock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tag_number = db.Column(db.String(50), unique=True, nullable=False)
    animal_type = db.Column(db.String(50), nullable=False)
    breed = db.Column(db.String(100))
    gender = db.Column(db.String(20))
    age = db.Column(db.String(30))
    weight = db.Column(db.Float)
    date_acquired = db.Column(db.String(30))
    status = db.Column(db.String(30), default='Healthy')
    notes = db.Column(db.Text)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

class HealthRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    livestock_id = db.Column(db.Integer, db.ForeignKey('livestock.id'))
    tag_number = db.Column(db.String(50))
    animal_type = db.Column(db.String(50))
    symptom = db.Column(db.String(200))
    diagnosis = db.Column(db.Text)
    treatment = db.Column(db.Text)
    veterinary_officer = db.Column(db.String(100))
    date_recorded = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Under Treatment')

class FeedRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    animal_type = db.Column(db.String(50))
    feed_type = db.Column(db.String(100))
    quantity_kg = db.Column(db.Float)
    feeding_date = db.Column(db.String(30))
    recorded_by = db.Column(db.String(100))
    notes = db.Column(db.Text)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

class BreedingRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    female_tag = db.Column(db.String(50))
    male_tag = db.Column(db.String(50))
    animal_type = db.Column(db.String(50))
    breeding_date = db.Column(db.String(30))
    expected_delivery = db.Column(db.String(30))
    actual_delivery = db.Column(db.String(30))
    offspring_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='Pending')
    notes = db.Column(db.Text)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

class ProductionRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    animal_type = db.Column(db.String(50))
    production_type = db.Column(db.String(100))
    quantity = db.Column(db.Float)
    unit = db.Column(db.String(30))
    production_date = db.Column(db.String(30))
    recorded_by = db.Column(db.String(100))
    notes = db.Column(db.Text)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

class VaccinationRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tag_number = db.Column(db.String(50))
    animal_type = db.Column(db.String(50))
    vaccine_name = db.Column(db.String(100))
    date_administered = db.Column(db.String(30))
    next_due_date = db.Column(db.String(30))
    administered_by = db.Column(db.String(100))
    notes = db.Column(db.Text)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

# ─────────────────────────────────────────
# DISEASE KNOWLEDGE BASE
# ─────────────────────────────────────────
DISEASE_KB = {
    "fever, loss of appetite, weakness": {
        "diagnosis": "Possible Septicaemia or General Bacterial Infection",
        "treatment": (
            "1. Isolate the animal immediately from the rest of the herd.\n"
            "2. Administer Oxytetracycline injection — approximate cost: ₦800 – ₦1,500 per vial.\n"
            "3. Ensure constant supply of clean, cool water.\n"
            "4. Give oral Rehydration Salts (ORS) — available at local chemists for approximately ₦200 – ₦400.\n"
            "5. Contact the nearest Akinyele LGA Veterinary Clinic immediately.\n"
            "6. Estimated cost of full treatment: ₦3,000 – ₦8,000 depending on animal size."
        ),
        "severity": "High"
    },
    "diarrhea, dehydration, weakness": {
        "diagnosis": "Possible Enteritis, Salmonellosis or Colibacillosis",
        "treatment": (
            "1. Remove animal from herd and place in a clean, dry pen.\n"
            "2. Provide Oral Rehydration Salts (ORS) mixed in clean water — cost: ₦200 – ₦400/sachet.\n"
            "3. Administer Metronidazole (Flagyl) or Sulphadimidine — cost: ₦500 – ₦1,200.\n"
            "4. Disinfect feeding troughs with Izal or Dettol (₦600 – ₦900 per bottle).\n"
            "5. Estimated total treatment cost: ₦2,500 – ₦6,000."
        ),
        "severity": "Medium"
    },
    "coughing, nasal discharge, difficulty breathing": {
        "diagnosis": "Possible Pneumonia, Pasteurellosis or Respiratory Infection",
        "treatment": (
            "1. Move animal to a warm, well-ventilated shelter immediately.\n"
            "2. Administer Penicillin-Streptomycin injection — cost: ₦700 – ₦1,500 per vial.\n"
            "3. Alternatively use Oxytetracycline long-acting injection — cost: ₦1,000 – ₦2,000.\n"
            "4. Give anti-inflammatory drug (Flunixin Meglumine) — cost: ₦800 – ₦1,500.\n"
            "5. Contact Akinyele LGA Vet Clinic if no improvement within 48 hours.\n"
            "6. Estimated treatment cost: ₦3,500 – ₦9,000."
        ),
        "severity": "High"
    },
    "skin lesions, blisters, lameness": {
        "diagnosis": "Possible Foot and Mouth Disease (FMD) — NOTIFIABLE DISEASE",
        "treatment": (
            "⚠️ CRITICAL — THIS IS A NOTIFIABLE DISEASE IN NIGERIA.\n"
            "1. IMMEDIATELY quarantine ALL affected animals.\n"
            "2. Report to Akinyele LGA Agricultural Department and Oyo State Ministry of Agriculture.\n"
            "3. Disinfect farm premises with Sodium Hydroxide solution.\n"
            "4. Vaccinate unaffected animals — government-subsidised vaccines available at ₦500 – ₦1,500 per dose.\n"
            "5. Do NOT sell or move any animal until cleared by veterinary authorities."
        ),
        "severity": "Critical"
    },
    "sudden death, bloating, bloody discharge": {
        "diagnosis": "Possible Anthrax or Blackleg — NOTIFIABLE DISEASE",
        "treatment": (
            "⚠️ EXTREME DANGER — DO NOT TOUCH CARCASS WITH BARE HANDS.\n"
            "1. Wear protective gloves and mask before approaching.\n"
            "2. Do NOT slaughter or eat meat from any animal that died suddenly.\n"
            "3. Report IMMEDIATELY to Akinyele LGA Agricultural Department.\n"
            "4. Burn or bury the carcass at least 2 metres deep.\n"
            "5. Vaccinate remaining herd with Anthrax Spore Vaccine — cost: ₦500 – ₦1,000 per dose.\n"
            "6. Estimated emergency response cost: ₦15,000 – ₦50,000+."
        ),
        "severity": "Critical"
    },
    "reduced egg production, dull feathers, lethargy": {
        "diagnosis": "Possible Newcastle Disease or Gumboro Disease",
        "treatment": (
            "1. Immediately isolate sick birds from the flock.\n"
            "2. Vaccinate flock with Newcastle Disease (La Sota) vaccine — cost: ₦500 – ₦1,500 per vial.\n"
            "3. Add Multivitamins to drinking water (e.g. Vitastress) — cost: ₦600 – ₦1,200.\n"
            "4. Administer broad-spectrum antibiotics — cost: ₦800 – ₦2,000.\n"
            "5. Disinfect poultry house with Izal or Virkon — cost: ₦600 – ₦1,500.\n"
            "6. Estimated treatment cost for 100 birds: ₦5,000 – ₦15,000."
        ),
        "severity": "High"
    },
    "swollen joints, limping, reluctance to move": {
        "diagnosis": "Possible Arthritis, Joint Infection or Foot Rot",
        "treatment": (
            "1. Clean and examine the affected limb for wounds or abscesses.\n"
            "2. Administer Penicillin injection — cost: ₦700 – ₦1,200 per vial.\n"
            "3. Give anti-inflammatory drug (Flunixin or Aspirin) — cost: ₦500 – ₦1,200.\n"
            "4. For foot rot: apply Copper Sulphate foot bath — cost: ₦400 – ₦800.\n"
            "5. Estimated treatment cost: ₦2,000 – ₦6,500."
        ),
        "severity": "Medium"
    },
    "weight loss, pale gums, rough coat": {
        "diagnosis": "Possible Internal Parasites (Worms) or Anaemia",
        "treatment": (
            "1. Administer Albendazole (Valbazen) dewormer — cost: ₦800 – ₦1,500 per bottle.\n"
            "2. Alternatively use Ivermectin injection — cost: ₦1,000 – ₦2,500.\n"
            "3. If anaemic: give Iron Dextran injection — cost: ₦600 – ₦1,200.\n"
            "4. Add mineral supplement (Vitalyte or Rumivite) — cost: ₦1,000 – ₦2,500/kg.\n"
            "5. Repeat deworming after 3 weeks. Estimated cost: ₦2,500 – ₦7,000."
        ),
        "severity": "Medium"
    },
    "tick infestation, scratching, hair loss": {
        "diagnosis": "Possible Tick Infestation, Mange or Ectoparasite Infection",
        "treatment": (
            "1. Apply Amitraz (Triatix) dip — cost: ₦1,200 – ₦2,500 per litre.\n"
            "2. Alternatively use Cypermethrin spray — cost: ₦800 – ₦1,800 per bottle.\n"
            "3. For mange: apply Ivermectin injection — cost: ₦1,000 – ₦2,500.\n"
            "4. Clean and disinfect housing with Coopex or Butox — cost: ₦600 – ₦1,500.\n"
            "5. Repeat treatment after 14 days. Estimated cost: ₦2,000 – ₦6,000."
        ),
        "severity": "Low"
    },
    "milk reduction, swollen udder, pain on touch": {
        "diagnosis": "Possible Mastitis (Udder Infection)",
        "treatment": (
            "1. Strip the affected quarter completely 3–4 times daily.\n"
            "2. Apply intramammary antibiotic (Mastijet Fort or Orbenin) — cost: ₦1,500 – ₦3,500 per tube.\n"
            "3. Administer Penicillin/Amoxicillin injection — cost: ₦700 – ₦2,000.\n"
            "4. Give anti-inflammatory drug (Flunixin) — cost: ₦800 – ₦1,800.\n"
            "5. Do NOT sell milk during treatment (withdrawal period: 4–7 days).\n"
            "6. Estimated total treatment cost: ₦6,000 – ₦18,000 per animal."
        ),
        "severity": "High"
    },
}

def get_disease_advice(symptoms_input):
    symptoms_lower = symptoms_input.lower().strip()
    for key, value in DISEASE_KB.items():
        key_words = key.split(", ")
        matches = sum(1 for word in key_words if word in symptoms_lower)
        if matches >= 2 or (len(key_words) == 1 and key_words[0] in symptoms_lower):
            return value
    return {
        "diagnosis": "Symptoms not clearly identified in database",
        "treatment": "Please contact a qualified veterinary officer immediately for proper diagnosis and treatment.",
        "severity": "Unknown"
    }

# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────
@app.route('/')
def index():
    if 'admin' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    admin = Admin.query.filter_by(username=username).first()
    if admin and check_password_hash(admin.password, password):
        session['admin'] = username
        flash('Welcome back, ' + username + '!', 'success')
        return redirect(url_for('dashboard'))
    flash('Invalid username or password.', 'error')
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

@app.route('/dashboard')
@login_required
def dashboard():
    total_livestock = Livestock.query.count()
    healthy = Livestock.query.filter_by(status='Healthy').count()
    sick = Livestock.query.filter_by(status='Sick').count()
    total_health = HealthRecord.query.count()
    total_breeding = BreedingRecord.query.count()
    total_production = ProductionRecord.query.count()
    total_vaccination = VaccinationRecord.query.count()
    recent_health = HealthRecord.query.order_by(HealthRecord.date_recorded.desc()).limit(5).all()
    recent_livestock = Livestock.query.order_by(Livestock.date_added.desc()).limit(5).all()
    animal_counts = {}
    for a in ['Cattle','Goat','Sheep','Poultry','Pig','Rabbit']:
        animal_counts[a] = Livestock.query.filter_by(animal_type=a).count()
    return render_template('dashboard.html',
        total_livestock=total_livestock, healthy=healthy, sick=sick,
        total_health=total_health, total_breeding=total_breeding,
        total_production=total_production, total_vaccination=total_vaccination,
        recent_health=recent_health, recent_livestock=recent_livestock,
        animal_counts=animal_counts)

@app.route('/livestock')
@login_required
def livestock():
    animals = Livestock.query.order_by(Livestock.date_added.desc()).all()
    return render_template('livestock.html', animals=animals)

@app.route('/livestock/add', methods=['GET','POST'])
@login_required
def add_livestock():
    if request.method == 'POST':
        animal = Livestock(
            tag_number=request.form['tag_number'], animal_type=request.form['animal_type'],
            breed=request.form['breed'], gender=request.form['gender'],
            age=request.form['age'], weight=float(request.form['weight'] or 0),
            date_acquired=request.form['date_acquired'], status=request.form['status'],
            notes=request.form['notes'])
        db.session.add(animal); db.session.commit()
        flash('Livestock record added successfully!', 'success')
        return redirect(url_for('livestock'))
    return render_template('add_livestock.html')

@app.route('/livestock/delete/<int:id>')
@login_required
def delete_livestock(id):
    animal = Livestock.query.get_or_404(id)
    db.session.delete(animal); db.session.commit()
    flash('Record deleted.', 'success')
    return redirect(url_for('livestock'))

@app.route('/health')
@login_required
def health():
    records = HealthRecord.query.order_by(HealthRecord.date_recorded.desc()).all()
    return render_template('health.html', records=records)

@app.route('/health/add', methods=['GET','POST'])
@login_required
def add_health():
    animals = Livestock.query.all()
    if request.method == 'POST':
        record = HealthRecord(
            livestock_id=request.form.get('livestock_id'), tag_number=request.form['tag_number'],
            animal_type=request.form['animal_type'], symptom=request.form['symptom'],
            diagnosis=request.form['diagnosis'], treatment=request.form['treatment'],
            veterinary_officer=request.form['veterinary_officer'], status=request.form['status'])
        db.session.add(record); db.session.commit()
        flash('Health record added!', 'success')
        return redirect(url_for('health'))
    return render_template('add_health.html', animals=animals)

@app.route('/health/delete/<int:id>')
@login_required
def delete_health(id):
    record = HealthRecord.query.get_or_404(id)
    db.session.delete(record); db.session.commit()
    flash('Record deleted.', 'success')
    return redirect(url_for('health'))

@app.route('/firstaid', methods=['GET','POST'])
@login_required
def firstaid():
    result = None; symptoms_input = ''
    if request.method == 'POST':
        symptoms_input = request.form.get('symptoms', '')
        result = get_disease_advice(symptoms_input)
    return render_template('firstaid.html', result=result, symptoms_input=symptoms_input)

@app.route('/feeding')
@login_required
def feeding():
    records = FeedRecord.query.order_by(FeedRecord.date_added.desc()).all()
    return render_template('feeding.html', records=records)

@app.route('/feeding/add', methods=['GET','POST'])
@login_required
def add_feeding():
    if request.method == 'POST':
        record = FeedRecord(
            animal_type=request.form['animal_type'], feed_type=request.form['feed_type'],
            quantity_kg=float(request.form['quantity_kg'] or 0), feeding_date=request.form['feeding_date'],
            recorded_by=request.form['recorded_by'], notes=request.form['notes'])
        db.session.add(record); db.session.commit()
        flash('Feeding record added!', 'success')
        return redirect(url_for('feeding'))
    return render_template('add_feeding.html')

@app.route('/feeding/delete/<int:id>')
@login_required
def delete_feeding(id):
    record = FeedRecord.query.get_or_404(id)
    db.session.delete(record); db.session.commit()
    flash('Record deleted.', 'success')
    return redirect(url_for('feeding'))

@app.route('/breeding')
@login_required
def breeding():
    records = BreedingRecord.query.order_by(BreedingRecord.date_added.desc()).all()
    return render_template('breeding.html', records=records)

@app.route('/breeding/add', methods=['GET','POST'])
@login_required
def add_breeding():
    if request.method == 'POST':
        record = BreedingRecord(
            female_tag=request.form['female_tag'], male_tag=request.form['male_tag'],
            animal_type=request.form['animal_type'], breeding_date=request.form['breeding_date'],
            expected_delivery=request.form['expected_delivery'],
            actual_delivery=request.form.get('actual_delivery',''),
            offspring_count=int(request.form.get('offspring_count',0)),
            status=request.form['status'], notes=request.form['notes'])
        db.session.add(record); db.session.commit()
        flash('Breeding record added!', 'success')
        return redirect(url_for('breeding'))
    return render_template('add_breeding.html')

@app.route('/breeding/delete/<int:id>')
@login_required
def delete_breeding(id):
    record = BreedingRecord.query.get_or_404(id)
    db.session.delete(record); db.session.commit()
    flash('Record deleted.', 'success')
    return redirect(url_for('breeding'))

@app.route('/production')
@login_required
def production():
    records = ProductionRecord.query.order_by(ProductionRecord.date_added.desc()).all()
    return render_template('production.html', records=records)

@app.route('/production/add', methods=['GET','POST'])
@login_required
def add_production():
    if request.method == 'POST':
        record = ProductionRecord(
            animal_type=request.form['animal_type'], production_type=request.form['production_type'],
            quantity=float(request.form['quantity'] or 0), unit=request.form['unit'],
            production_date=request.form['production_date'], recorded_by=request.form['recorded_by'],
            notes=request.form['notes'])
        db.session.add(record); db.session.commit()
        flash('Production record added!', 'success')
        return redirect(url_for('production'))
    return render_template('add_production.html')

@app.route('/production/delete/<int:id>')
@login_required
def delete_production(id):
    record = ProductionRecord.query.get_or_404(id)
    db.session.delete(record); db.session.commit()
    flash('Record deleted.', 'success')
    return redirect(url_for('production'))

@app.route('/vaccination')
@login_required
def vaccination():
    records = VaccinationRecord.query.order_by(VaccinationRecord.date_added.desc()).all()
    return render_template('vaccination.html', records=records)

@app.route('/vaccination/add', methods=['GET','POST'])
@login_required
def add_vaccination():
    animals = Livestock.query.all()
    if request.method == 'POST':
        record = VaccinationRecord(
            tag_number=request.form['tag_number'], animal_type=request.form['animal_type'],
            vaccine_name=request.form['vaccine_name'], date_administered=request.form['date_administered'],
            next_due_date=request.form['next_due_date'], administered_by=request.form['administered_by'],
            notes=request.form['notes'])
        db.session.add(record); db.session.commit()
        flash('Vaccination record added!', 'success')
        return redirect(url_for('vaccination'))
    return render_template('add_vaccination.html', animals=animals)

@app.route('/vaccination/delete/<int:id>')
@login_required
def delete_vaccination(id):
    record = VaccinationRecord.query.get_or_404(id)
    db.session.delete(record); db.session.commit()
    flash('Record deleted.', 'success')
    return redirect(url_for('vaccination'))

@app.route('/api/chart-data')
@login_required
def chart_data():
    animal_counts = {}
    for a in ['Cattle','Goat','Sheep','Poultry','Pig','Rabbit']:
        animal_counts[a] = Livestock.query.filter_by(animal_type=a).count()
    return jsonify(animal_counts)

# ─────────────────────────────────────────
# INIT DB
# ─────────────────────────────────────────
def init_db():
    with app.app_context():
        db.create_all()
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(username='admin', password=generate_password_hash('admin123'))
            db.session.add(admin)
            db.session.commit()
            print("Default admin created: username=admin, password=admin123")

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

# Auto-initialize database on startup (needed for Render)
with app.app_context():
    try:
        db.create_all()
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(username='admin', password=generate_password_hash('admin123'))
            db.session.add(admin)
            db.session.commit()
    except Exception as e:
        print(f"DB init error: {e}")
