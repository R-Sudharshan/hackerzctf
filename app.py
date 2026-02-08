from flask import Flask, render_template, send_from_directory, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key_change_me')

# Database Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
db_url = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'hackerz.db'))

# Fix for SQLAlchemy 1.4+ / 2.0+ which requires 'postgresql://' instead of 'postgres://'
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'downloads')

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Model
class Team(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255)) # Increased from 128 to 255
    score = db.Column(db.Integer, default=0)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Challenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    points = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)
    file_url = db.Column(db.String(200), nullable=True)
    flag = db.Column(db.String(100), nullable=False)

class Solve(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenge.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return Team.query.get(int(user_id))

# Initialize Database
def init_db():
    with app.app_context():
        db.create_all()
        if not Challenge.query.first():
            print("DEBUG: Seeding database with challenges...")
            challenges = [
                Challenge(title="The Source", category="Reverse Engineering", difficulty="Easy", points=100, 
                          description="Can you reverse this script and find the flag? It seems to be hidden in the logic.",
                          file_url="rev_challenge.py", flag="flag{Typo_and_Sympo}"),
                Challenge(title="Binary Whisperer", category="OSINT", difficulty="Medium", points=250, 
                          description='The challenge begins long before you think it does: <a href="https://chat.whatsapp.com/Hb02gXqFZtF2K8EOInsOQ2" target="_blank" style="color: var(--primary-color); text-decoration: underline;">click me</a>', file_url=None, flag="Flag{OSINT_Made_Easy}"),
                Challenge(title="Client Side Truth", category="Web Exploitation", difficulty="Medium", points=300, 
                          description='Can you find the truth hidden on the client side? Explore the portal here: <a href="https://ques-mu.vercel.app/" target="_blank" style="color: var(--primary-color); text-decoration: underline;">click here</a>', file_url=None, flag="flag{cl13nt_s1d3_truth}"),
                Challenge(title="Hidden in Plain Sight", category="Steganography", difficulty="Hard", points=500, 
                          description="Some information prefers curiosity over attention. Find what’s quietly waiting to be discovered.", file_url="stego_challenge.jpg", flag="flag{Simply_Scan_Me}")
            ]
            db.session.add_all(challenges)
            
            # Seed a default team
            if not Team.query.filter_by(name="AdminTeam").first():
                 admin = Team(name="AdminTeam", email="admin@hackerz.com", score=100)
                 admin.set_password("admin123")
                 db.session.add(admin)
            
            db.session.commit()
            print("DEBUG: Database seeded successfully.")

# Run DB Init
try:
    init_db()
except Exception as e:
    print(f"ERROR: Database initialization failed: {e}")
    # We continue so the app can start and hopefully be repaired via /reset-db

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('ctf'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = Team.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('ctf'))
        else:
            flash('Invalid email or password')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('ctf'))

    if request.method == 'POST':
        team_name = request.form['team_name']
        email = request.form['email']
        password = request.form['password']
        
        if Team.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        if Team.query.filter_by(name=team_name).first():
            flash('Team name already taken')
            return redirect(url_for('register'))
            
        new_team = Team(name=team_name, email=email)
        new_team.set_password(password)
        db.session.add(new_team)
        db.session.commit()
        
        login_user(new_team)
        return redirect(url_for('ctf'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# TEMPORARY: Route to fix database schema on Vercel
@app.route('/reset-db')
def reset_db_route():
    try:
        db.drop_all()
        db.create_all()
        return "Database reset successful! Your tables have been recreated with the correct sizes. Go to / and it will seed automatically."
    except Exception as e:
        return f"Error resetting database: {str(e)}"

@app.route('/ctf')
@login_required
def ctf():
    challenges = Challenge.query.all()
    # Get solved challenge IDs for current user to possibly style them differently
    solved_ids = [s.challenge_id for s in Solve.query.filter_by(team_id=current_user.id).all()]
    return render_template('ctf.html', challenges=challenges, solved_ids=solved_ids)

@app.route('/leaderboard')
@login_required
def leaderboard():
    teams = Team.query.order_by(Team.score.desc()).limit(10).all()
    return render_template('leaderboard.html', leaderboard=teams)

@app.route('/api/solve', methods=['POST'])
@login_required
def solve_challenge():
    data = request.json
    print(f"DEBUG: Received solve request from {current_user.name}: {data}")
    
    flag_input = data.get('flag')
    challenge_id = data.get('challenge_id')

    if not all([flag_input, challenge_id]):
        return jsonify({'success': False, 'message': 'Missing data'})

    challenge = Challenge.query.get(challenge_id)
    if not challenge:
        return jsonify({'success': False, 'message': 'Challenge not found'})

    if flag_input.strip() == challenge.flag:
        # Check if already solved
        solved = Solve.query.filter_by(team_id=current_user.id, challenge_id=challenge.id).first()
        if solved:
            return jsonify({'success': False, 'message': 'Already solved!', 'score': current_user.score})
        
        # Add Score
        current_user.score += challenge.points
        solve_record = Solve(team_id=current_user.id, challenge_id=challenge.id)
        db.session.add(solve_record)
        db.session.commit()
        
        print(f"DEBUG: Score updated for {current_user.name}. New Score: {current_user.score}")
        return jsonify({'success': True, 'message': 'Correct! Flag Accepted.', 'score': current_user.score})
    
    return jsonify({'success': False, 'message': 'Incorrect Flag.'})

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
