import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

# ─── DB Connection ────────────────────────────────────────────────────────────

def get_db():
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'pet_adoption'),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

# ─── Admin User Model ─────────────────────────────────────────────────────────

class Admin(UserMixin):
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email

    @property
    def initials(self):
        parts = self.name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return self.name[:2].upper()

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT id, name, email FROM admins WHERE id = %s", (user_id,))
            row = cur.fetchone()
            if row:
                return Admin(row['id'], row['name'], row['email'])
    finally:
        db.close()
    return None

# ─── Helper ───────────────────────────────────────────────────────────────────

def get_setting(key, default=''):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE `key` = %s", (key,))
            row = cur.fetchone()
            return row['value'] if row else default
    finally:
        db.close()

# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        db = get_db()
        try:
            with db.cursor() as cur:
                cur.execute("SELECT id, name, email, password_hash FROM admins WHERE email = %s", (email,))
                admin = cur.fetchone()
        finally:
            db.close()

        if admin and check_password_hash(admin['password_hash'], password):
            user = Admin(admin['id'], admin['name'], admin['email'])
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM pets")
            total_pets = cur.fetchone()['cnt']

            cur.execute("SELECT COUNT(*) AS cnt FROM pets WHERE status = 'available'")
            available_pets = cur.fetchone()['cnt']

            cur.execute("SELECT COUNT(*) AS cnt FROM adopters")
            total_adopters = cur.fetchone()['cnt']

            cur.execute("SELECT COUNT(*) AS cnt FROM adoption_requests WHERE status = 'pending'")
            pending_requests = cur.fetchone()['cnt']

            cur.execute("""
                SELECT ar.id, p.name AS pet_name, a.name AS adopter_name,
                       ar.request_date, ar.status
                FROM adoption_requests ar
                JOIN pets p ON ar.pet_id = p.id
                JOIN adopters a ON ar.adopter_id = a.id
                ORDER BY ar.request_date DESC LIMIT 5
            """)
            recent_requests = cur.fetchall()

            cur.execute("""
                SELECT species, COUNT(*) AS cnt FROM pets GROUP BY species
            """)
            species_rows = cur.fetchall()
            species_data = {r['species'].lower(): r['cnt'] for r in species_rows}

            cur.execute("""
                SELECT id, title, message, posted_date FROM notices
                ORDER BY posted_date DESC LIMIT 3
            """)
            latest_notices = cur.fetchall()

    finally:
        db.close()

    org_name = get_setting('org_name', 'PawsHome Adoption Center')
    return render_template('dashboard.html',
        total_pets=total_pets,
        available_pets=available_pets,
        total_adopters=total_adopters,
        pending_requests=pending_requests,
        recent_requests=recent_requests,
        species_data=species_data,
        latest_notices=latest_notices,
        org_name=org_name
    )

# ─── Pets ─────────────────────────────────────────────────────────────────────

@app.route('/pets')
@login_required
def pets():
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'all')
    db = get_db()
    try:
        with db.cursor() as cur:
            query = "SELECT * FROM pets WHERE 1=1"
            params = []
            if search:
                query += " AND (name LIKE %s OR species LIKE %s OR breed LIKE %s)"
                params += [f'%{search}%', f'%{search}%', f'%{search}%']
            if status_filter in ('available', 'adopted'):
                query += " AND status = %s"
                params.append(status_filter)
            query += " ORDER BY added_date DESC"
            cur.execute(query, params)
            pets_list = cur.fetchall()
    finally:
        db.close()
    return render_template('pets.html', pets=pets_list, search=search, status_filter=status_filter)

@app.route('/pets/add', methods=['GET', 'POST'])
@login_required
def add_pet():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        species = request.form.get('species', '').strip()
        breed = request.form.get('breed', '').strip()
        age = request.form.get('age', '').strip()
        gender = request.form.get('gender', 'Unknown')
        description = request.form.get('description', '').strip()

        if not name or not species:
            flash('Name and species are required.', 'danger')
            return render_template('add_pet.html')

        try:
            age_val = float(age) if age else None
        except ValueError:
            age_val = None

        db = get_db()
        try:
            with db.cursor() as cur:
                cur.execute("""
                    INSERT INTO pets (name, species, breed, age, gender, description)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (name, species, breed or None, age_val, gender, description or None))
        finally:
            db.close()
        flash(f'Pet "{name}" added successfully!', 'success')
        return redirect(url_for('pets'))

    return render_template('add_pet.html')

@app.route('/pets/<int:pet_id>')
@login_required
def pet_detail(pet_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM pets WHERE id = %s", (pet_id,))
            pet = cur.fetchone()
            if not pet:
                flash('Pet not found.', 'danger')
                return redirect(url_for('pets'))

            cur.execute("""
                SELECT ar.id, ar.request_date, ar.status, ar.resolved_date,
                       a.id AS adopter_id, a.name AS adopter_name, a.email AS adopter_email, a.phone AS adopter_phone
                FROM adoption_requests ar
                JOIN adopters a ON ar.adopter_id = a.id
                WHERE ar.pet_id = %s
                ORDER BY ar.request_date DESC
            """, (pet_id,))
            history = cur.fetchall()

            current_adopter = None
            if pet['status'] == 'adopted':
                for h in history:
                    if h['status'] == 'approved':
                        current_adopter = h
                        break
    finally:
        db.close()
    return render_template('pet_detail.html', pet=pet, history=history, current_adopter=current_adopter)

@app.route('/pets/<int:pet_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_pet(pet_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM pets WHERE id = %s", (pet_id,))
            pet = cur.fetchone()
        if not pet:
            flash('Pet not found.', 'danger')
            return redirect(url_for('pets'))

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            species = request.form.get('species', '').strip()
            breed = request.form.get('breed', '').strip()
            age = request.form.get('age', '').strip()
            gender = request.form.get('gender', 'Unknown')
            description = request.form.get('description', '').strip()
            status = request.form.get('status', 'available')

            try:
                age_val = float(age) if age else None
            except ValueError:
                age_val = None

            with db.cursor() as cur:
                cur.execute("""
                    UPDATE pets SET name=%s, species=%s, breed=%s, age=%s,
                    gender=%s, description=%s, status=%s WHERE id=%s
                """, (name, species, breed or None, age_val, gender, description or None, status, pet_id))
            flash('Pet updated successfully!', 'success')
            return redirect(url_for('pet_detail', pet_id=pet_id))
    finally:
        db.close()
    return render_template('add_pet.html', pet=pet, edit=True)

@app.route('/pets/<int:pet_id>/delete', methods=['POST'])
@login_required
def delete_pet(pet_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT name FROM pets WHERE id = %s", (pet_id,))
            pet = cur.fetchone()
            if pet:
                cur.execute("DELETE FROM pets WHERE id = %s", (pet_id,))
                flash(f'Pet "{pet["name"]}" deleted successfully.', 'success')
            else:
                flash('Pet not found.', 'danger')
    finally:
        db.close()
    return redirect(url_for('pets'))

# ─── Adopters ─────────────────────────────────────────────────────────────────

@app.route('/adopters')
@login_required
def adopters():
    search = request.args.get('search', '').strip()
    db = get_db()
    try:
        with db.cursor() as cur:
            if search:
                cur.execute("""
                    SELECT a.*, COUNT(ar.id) AS total_adoptions
                    FROM adopters a
                    LEFT JOIN adoption_requests ar ON a.id = ar.adopter_id AND ar.status = 'approved'
                    WHERE a.name LIKE %s OR a.email LIKE %s
                    GROUP BY a.id ORDER BY a.registered_date DESC
                """, (f'%{search}%', f'%{search}%'))
            else:
                cur.execute("""
                    SELECT a.*, COUNT(ar.id) AS total_adoptions
                    FROM adopters a
                    LEFT JOIN adoption_requests ar ON a.id = ar.adopter_id AND ar.status = 'approved'
                    GROUP BY a.id ORDER BY a.registered_date DESC
                """)
            adopters_list = cur.fetchall()
    finally:
        db.close()
    return render_template('adopters.html', adopters=adopters_list, search=search)

@app.route('/adopters/add', methods=['GET', 'POST'])
@login_required
def add_adopter():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()

        if not name or not email:
            flash('Name and email are required.', 'danger')
            return render_template('add_adopter.html')

        db = get_db()
        try:
            with db.cursor() as cur:
                cur.execute("SELECT id FROM adopters WHERE email = %s", (email,))
                if cur.fetchone():
                    flash('An adopter with this email already exists.', 'danger')
                    return render_template('add_adopter.html')
                cur.execute("""
                    INSERT INTO adopters (name, email, phone, address)
                    VALUES (%s, %s, %s, %s)
                """, (name, email, phone or None, address or None))
        finally:
            db.close()
        flash(f'Adopter "{name}" added successfully!', 'success')
        return redirect(url_for('adopters'))

    return render_template('add_adopter.html')

@app.route('/adopters/<int:adopter_id>')
@login_required
def adopter_detail(adopter_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM adopters WHERE id = %s", (adopter_id,))
            adopter = cur.fetchone()
            if not adopter:
                flash('Adopter not found.', 'danger')
                return redirect(url_for('adopters'))

            cur.execute("""
                SELECT ar.id, ar.request_date, ar.status, ar.resolved_date,
                       p.id AS pet_id, p.name AS pet_name, p.species, p.breed
                FROM adoption_requests ar
                JOIN pets p ON ar.pet_id = p.id
                WHERE ar.adopter_id = %s
                ORDER BY ar.request_date DESC
            """, (adopter_id,))
            history = cur.fetchall()
    finally:
        db.close()
    return render_template('adopter_detail.html', adopter=adopter, history=history)

@app.route('/adopters/<int:adopter_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_adopter(adopter_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM adopters WHERE id = %s", (adopter_id,))
            adopter = cur.fetchone()
        if not adopter:
            flash('Adopter not found.', 'danger')
            return redirect(url_for('adopters'))

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            address = request.form.get('address', '').strip()

            with db.cursor() as cur:
                cur.execute("""
                    UPDATE adopters SET name=%s, email=%s, phone=%s, address=%s WHERE id=%s
                """, (name, email, phone or None, address or None, adopter_id))
            flash('Adopter updated successfully!', 'success')
            return redirect(url_for('adopter_detail', adopter_id=adopter_id))
    finally:
        db.close()
    return render_template('add_adopter.html', adopter=adopter, edit=True)

@app.route('/adopters/<int:adopter_id>/delete', methods=['POST'])
@login_required
def delete_adopter(adopter_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT name FROM adopters WHERE id = %s", (adopter_id,))
            adopter = cur.fetchone()
            if adopter:
                cur.execute("DELETE FROM adopters WHERE id = %s", (adopter_id,))
                flash(f'Adopter "{adopter["name"]}" deleted successfully.', 'success')
            else:
                flash('Adopter not found.', 'danger')
    finally:
        db.close()
    return redirect(url_for('adopters'))

# ─── Adoption Requests ────────────────────────────────────────────────────────

@app.route('/adoption-requests')
@login_required
def adoption_requests():
    status_filter = request.args.get('status', 'all')
    db = get_db()
    try:
        with db.cursor() as cur:
            query = """
                SELECT ar.id, ar.request_date, ar.status, ar.resolved_date,
                       p.id AS pet_id, p.name AS pet_name, p.species,
                       a.id AS adopter_id, a.name AS adopter_name, a.email AS adopter_email
                FROM adoption_requests ar
                JOIN pets p ON ar.pet_id = p.id
                JOIN adopters a ON ar.adopter_id = a.id
            """
            params = []
            if status_filter in ('pending', 'approved', 'rejected'):
                query += " WHERE ar.status = %s"
                params.append(status_filter)
            query += " ORDER BY ar.request_date DESC"
            cur.execute(query, params)
            requests_list = cur.fetchall()

            cur.execute("SELECT COUNT(*) AS cnt FROM adoption_requests WHERE status = 'pending'")
            pending_count = cur.fetchone()['cnt']

            # Available pets and adopters for add form
            cur.execute("SELECT id, name, species FROM pets WHERE status = 'available' ORDER BY name")
            available_pets = cur.fetchall()
            cur.execute("SELECT id, name, email FROM adopters ORDER BY name")
            all_adopters = cur.fetchall()
    finally:
        db.close()
    return render_template('adoption_requests.html',
        requests=requests_list,
        status_filter=status_filter,
        pending_count=pending_count,
        available_pets=available_pets,
        all_adopters=all_adopters
    )

@app.route('/adoption-requests/add', methods=['POST'])
@login_required
def add_adoption_request():
    pet_id = request.form.get('pet_id')
    adopter_id = request.form.get('adopter_id')
    if not pet_id or not adopter_id:
        flash('Pet and adopter are required.', 'danger')
        return redirect(url_for('adoption_requests'))

    db = get_db()
    try:
        with db.cursor() as cur:
            # Check for existing pending request
            cur.execute("""
                SELECT id FROM adoption_requests
                WHERE pet_id = %s AND adopter_id = %s AND status = 'pending'
            """, (pet_id, adopter_id))
            if cur.fetchone():
                flash('A pending request already exists for this pet and adopter.', 'warning')
                return redirect(url_for('adoption_requests'))
            cur.execute("""
                INSERT INTO adoption_requests (pet_id, adopter_id) VALUES (%s, %s)
            """, (pet_id, adopter_id))
    finally:
        db.close()
    flash('Adoption request created successfully!', 'success')
    return redirect(url_for('adoption_requests'))

@app.route('/adoption-requests/<int:req_id>/approve', methods=['POST'])
@login_required
def approve_request(req_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM adoption_requests WHERE id = %s", (req_id,))
            req = cur.fetchone()
            if not req or req['status'] != 'pending':
                flash('Request not found or already processed.', 'danger')
                return redirect(url_for('adoption_requests'))
            cur.execute("""
                UPDATE adoption_requests SET status='approved', resolved_date=%s WHERE id=%s
            """, (datetime.now(), req_id))
            cur.execute("UPDATE pets SET status='adopted' WHERE id=%s", (req['pet_id'],))
            # Reject all other pending requests for same pet
            cur.execute("""
                UPDATE adoption_requests SET status='rejected', resolved_date=%s
                WHERE pet_id=%s AND id != %s AND status='pending'
            """, (datetime.now(), req['pet_id'], req_id))
    finally:
        db.close()
    flash('Adoption request approved! Pet status updated to adopted.', 'success')
    return redirect(url_for('adoption_requests'))

@app.route('/adoption-requests/<int:req_id>/reject', methods=['POST'])
@login_required
def reject_request(req_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM adoption_requests WHERE id = %s", (req_id,))
            req = cur.fetchone()
            if not req or req['status'] != 'pending':
                flash('Request not found or already processed.', 'danger')
                return redirect(url_for('adoption_requests'))
            cur.execute("""
                UPDATE adoption_requests SET status='rejected', resolved_date=%s WHERE id=%s
            """, (datetime.now(), req_id))
    finally:
        db.close()
    flash('Adoption request rejected.', 'info')
    return redirect(url_for('adoption_requests'))

@app.route('/adoption-requests/<int:req_id>/delete', methods=['POST'])
@login_required
def delete_request(req_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM adoption_requests WHERE id = %s", (req_id,))
    finally:
        db.close()
    flash('Adoption request deleted.', 'success')
    return redirect(url_for('adoption_requests'))

# ─── Notices ──────────────────────────────────────────────────────────────────

@app.route('/notices')
@login_required
def notices():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT n.*, a.name AS admin_name
                FROM notices n
                LEFT JOIN admins a ON n.admin_id = a.id
                ORDER BY n.posted_date DESC
            """)
            notices_list = cur.fetchall()
    finally:
        db.close()
    return render_template('notices.html', notices=notices_list)

@app.route('/notices/add', methods=['POST'])
@login_required
def add_notice():
    title = request.form.get('title', '').strip()
    message = request.form.get('message', '').strip()
    if not title or not message:
        flash('Title and message are required.', 'danger')
        return redirect(url_for('notices'))
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                INSERT INTO notices (title, message, admin_id) VALUES (%s, %s, %s)
            """, (title, message, current_user.id))
    finally:
        db.close()
    flash('Notice posted successfully!', 'success')
    return redirect(url_for('notices'))

@app.route('/notices/<int:notice_id>/delete', methods=['POST'])
@login_required
def delete_notice(notice_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM notices WHERE id = %s", (notice_id,))
    finally:
        db.close()
    flash('Notice deleted.', 'success')
    return redirect(url_for('notices'))

# ─── Settings ─────────────────────────────────────────────────────────────────

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    db = get_db()
    try:
        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'change_password':
                current_pw = request.form.get('current_password', '')
                new_pw = request.form.get('new_password', '')
                confirm_pw = request.form.get('confirm_password', '')

                with db.cursor() as cur:
                    cur.execute("SELECT password_hash FROM admins WHERE id = %s", (current_user.id,))
                    row = cur.fetchone()

                if not row or not check_password_hash(row['password_hash'], current_pw):
                    flash('Current password is incorrect.', 'danger')
                elif new_pw != confirm_pw:
                    flash('New passwords do not match.', 'danger')
                elif len(new_pw) < 6:
                    flash('New password must be at least 6 characters.', 'danger')
                else:
                    new_hash = generate_password_hash(new_pw)
                    with db.cursor() as cur:
                        cur.execute("UPDATE admins SET password_hash = %s WHERE id = %s",
                                    (new_hash, current_user.id))
                    flash('Password changed successfully!', 'success')

            elif action == 'update_org':
                org_name = request.form.get('org_name', '').strip()
                if org_name:
                    with db.cursor() as cur:
                        cur.execute("""
                            INSERT INTO settings (`key`, value) VALUES ('org_name', %s)
                            ON DUPLICATE KEY UPDATE value = %s
                        """, (org_name, org_name))
                    flash('Organization name updated!', 'success')
                else:
                    flash('Organization name cannot be empty.', 'danger')

        with db.cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE `key` = 'org_name'")
            row = cur.fetchone()
            org_name = row['value'] if row else 'PawsHome Adoption Center'
    finally:
        db.close()

    return render_template('settings.html', org_name=org_name)

# ─── Database Init ────────────────────────────────────────────────────────────

def init_db():
    """
    Create all tables if they don't exist, then seed default data.
    Safe to run on every startup — uses IF NOT EXISTS and ON DUPLICATE KEY.
    """
    db = get_db()
    try:
        with db.cursor() as cur:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(150) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS pets (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    species VARCHAR(50) NOT NULL,
                    breed VARCHAR(100),
                    age DECIMAL(4,1),
                    gender ENUM('Male','Female','Unknown') DEFAULT 'Unknown',
                    description TEXT,
                    status ENUM('available','adopted') DEFAULT 'available',
                    added_date DATETIME DEFAULT CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS adopters (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(150) NOT NULL UNIQUE,
                    phone VARCHAR(20),
                    address TEXT,
                    registered_date DATETIME DEFAULT CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS adoption_requests (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    pet_id INT NOT NULL,
                    adopter_id INT NOT NULL,
                    request_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status ENUM('pending','approved','rejected') DEFAULT 'pending',
                    resolved_date DATETIME,
                    FOREIGN KEY (pet_id) REFERENCES pets(id) ON DELETE CASCADE,
                    FOREIGN KEY (adopter_id) REFERENCES adopters(id) ON DELETE CASCADE
                ) CHARACTER SET utf8mb4
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS notices (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    message TEXT NOT NULL,
                    posted_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    admin_id INT,
                    FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE SET NULL
                ) CHARACTER SET utf8mb4
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    `key` VARCHAR(100) NOT NULL UNIQUE,
                    value TEXT
                ) CHARACTER SET utf8mb4
            """)

            # Default admin with proper hash
            pw_hash = generate_password_hash('admin123')
            cur.execute("""
                INSERT INTO admins (name, email, password_hash)
                VALUES ('Admin', 'admin@petadopt.com', %s)
                ON DUPLICATE KEY UPDATE
                    password_hash = IF(
                        CHAR_LENGTH(password_hash) < 40,
                        VALUES(password_hash),
                        password_hash
                    )
            """, (pw_hash,))

            # Default setting
            cur.execute("""
                INSERT INTO settings (`key`, value) VALUES ('org_name', 'PawsHome Adoption Center')
                ON DUPLICATE KEY UPDATE `key` = `key`
            """)

            # Sample pets (only if table is empty)
            cur.execute("SELECT COUNT(*) AS cnt FROM pets")
            if cur.fetchone()['cnt'] == 0:
                cur.executemany("""
                    INSERT INTO pets (name, species, breed, age, gender, description, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [
                    ('Buddy',    'Dog',    'Golden Retriever', 2.0, 'Male',   'Friendly and energetic, loves fetch.',        'available'),
                    ('Whiskers', 'Cat',    'Persian',          3.5, 'Female', 'Calm and affectionate, great with kids.',     'available'),
                    ('Max',      'Dog',    'German Shepherd',  4.0, 'Male',   'Loyal and intelligent, well trained.',        'available'),
                    ('Luna',     'Cat',    'Siamese',          1.5, 'Female', 'Playful Siamese kitten, very social.',        'available'),
                    ('Charlie',  'Dog',    'Beagle',           3.0, 'Male',   'Curious Beagle, loves outdoor adventures.',  'available'),
                    ('Bella',    'Rabbit', 'Holland Lop',      1.0, 'Female', 'Sweet Holland Lop, gentle and easy to care.','available'),
                ])

            # Sample adopters (only if table is empty)
            cur.execute("SELECT COUNT(*) AS cnt FROM adopters")
            if cur.fetchone()['cnt'] == 0:
                cur.executemany("""
                    INSERT INTO adopters (name, email, phone, address) VALUES (%s, %s, %s, %s)
                """, [
                    ('John Smith',    'john.smith@email.com', '555-0101', '123 Oak Street, Springfield'),
                    ('Sarah Johnson', 'sarah.j@email.com',    '555-0102', '456 Maple Ave, Riverside'),
                    ('Mike Davis',    'mike.davis@email.com', '555-0103', '789 Pine Road, Lakewood'),
                ])

            # Sample notices (only if table is empty)
            cur.execute("SELECT COUNT(*) AS cnt FROM notices")
            if cur.fetchone()['cnt'] == 0:
                cur.execute("SELECT id FROM admins WHERE email = 'admin@petadopt.com'")
                admin = cur.fetchone()
                if admin:
                    cur.executemany("""
                        INSERT INTO notices (title, message, admin_id) VALUES (%s, %s, %s)
                    """, [
                        ('Welcome to PawsHome!',      'We are excited to help you find your perfect furry companion!', admin['id']),
                        ('Adoption Event This Weekend','Join us Saturday for our special adoption event.',              admin['id']),
                        ('New Pets Available',         'Several new pets are looking for loving homes. Check them out!',admin['id']),
                    ])

        print("[startup] Database initialised successfully.")
    except Exception as e:
        print(f"[startup] DB init error: {e}")
    finally:
        db.close()


# Runs on import — works for both gunicorn workers and flask dev server
try:
    init_db()
except Exception as e:
    print(f"[startup] init_db skipped: {e}")


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
