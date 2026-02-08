from flask import Flask, render_template, send_from_directory, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sys
import asyncio

# CRITICAL for Vercel: Redirect Prisma binaries to a local writeable folder
os.environ['PRISMA_PY_BINARY_CACHE_DIR'] = os.path.join(os.getcwd(), '.prisma_binaries')

# Ensure local path is in sys.path for Vercel environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from generated_prisma import Prisma

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key_change_me')

# Prisma Client Initialization
prisma = Prisma()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, team_obj):
        self.id = str(team_obj.id)
        self.team = team_obj
        self.name = team_obj.name

@login_manager.user_loader
def load_user(user_id):
    # Flask-Login's user_loader needs to be sync, so we use a helper
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    team = loop.run_until_complete(prisma.team.find_unique(where={'id': int(user_id)}))
    loop.close()
    return User(team) if team else None

# Initialize Database
async def init_db():
    if not await prisma.challenge.find_first():
        print("DEBUG: Seeding database with challenges...")
        challenges = [
            {"title": "The Source", "category": "Reverse Engineering", "difficulty": "Easy", "points": 100, 
             "description": "Can you reverse this script and find the flag? It seems to be hidden in the logic.",
             "file_url": "rev_challenge.py", "flag": "flag{Typo_and_Sympo}"},
            {"title": "Binary Whisperer", "category": "OSINT", "difficulty": "Medium", "points": 250, 
             "description": 'The challenge begins long before you think it does: <a href="https://chat.whatsapp.com/Hb02gXqFZtF2K8EOInsOQ2" target="_blank" style="color: var(--primary-color); text-decoration: underline;">click me</a>', "file_url": None, "flag": "Flag{OSINT_Made_Easy}"},
            {"title": "Client Side Truth", "category": "Web Exploitation", "difficulty": "Medium", "points": 300, 
             "description": 'Can you find the truth hidden on the client side? Explore the portal here: <a href="https://ques-mu.vercel.app/" target="_blank" style="color: var(--primary-color); text-decoration: underline;">click here</a>', "file_url": None, "flag": "flag{cl13nt_s1d3_truth}"},
            {"title": "Hidden in Plain Sight", "category": "Steganography", "difficulty": "Hard", "points": 500, 
             "description": "Some information prefers curiosity over attention. Find what’s quietly waiting to be discovered.", "file_url": "stego_challenge.jpg", "flag": "flag{Simply_Scan_Me}"}
        ]
        for c in challenges:
            await prisma.challenge.create(data=c)
        
        # Seed a default team
        if not await prisma.team.find_unique(where={"name": "AdminTeam"}):
             password_hash = generate_password_hash("admin123")
             await prisma.team.create(data={
                 "name": "AdminTeam",
                 "email": "admin@hackerz.com",
                 "score": 100,
                 "password_hash": password_hash
             })
        
        print("DEBUG: Database seeded successfully.")

# Setup Prisma connection before first request
@app.before_request
def startup():
    if not prisma.is_connected():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(prisma.connect())
        loop.run_until_complete(init_db())
        loop.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
async def login():
    if current_user.is_authenticated:
        return redirect(url_for('ctf'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        team = await prisma.team.find_unique(where={'email': email})
        
        if team and check_password_hash(team.password_hash, password):
            login_user(User(team))
            return redirect(url_for('ctf'))
        else:
            flash('Invalid email or password')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
async def register():
    if current_user.is_authenticated:
        return redirect(url_for('ctf'))

    if request.method == 'POST':
        team_name = request.form['team_name']
        email = request.form['email']
        password = request.form['password']
        
        if await prisma.team.find_unique(where={'email': email}):
            flash('Email already registered')
            return redirect(url_for('register'))
        
        if await prisma.team.find_unique(where={'name': team_name}):
            flash('Team name already taken')
            return redirect(url_for('register'))
            
        password_hash = generate_password_hash(password)
        new_team = await prisma.team.create(data={
            "name": team_name,
            "email": email,
            "password_hash": password_hash
        })
        
        login_user(User(new_team))
        return redirect(url_for('ctf'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/ctf')
@login_required
async def ctf():
    challenges = await prisma.challenge.find_many()
    # Get solved challenge IDs for current user
    solves = await prisma.solve.find_many(where={'team_id': int(current_user.id)})
    solved_ids = [s.challenge_id for s in solves]
    return render_template('ctf.html', challenges=challenges, solved_ids=solved_ids)

@app.route('/leaderboard')
@login_required
async def leaderboard():
    teams = await prisma.team.find_many(order={'score': 'desc'}, take=10)
    return render_template('leaderboard.html', leaderboard=teams)

@app.route('/api/solve', methods=['POST'])
@login_required
async def solve_challenge():
    data = request.json
    print(f"DEBUG: Received solve request from {current_user.name}: {data}")
    
    flag_input = data.get('flag')
    challenge_id = data.get('challenge_id')

    if not all([flag_input, challenge_id]):
        return jsonify({'success': False, 'message': 'Missing data'})

    challenge = await prisma.challenge.find_unique(where={'id': int(challenge_id)})
    if not challenge:
        return jsonify({'success': False, 'message': 'Challenge not found'})

    if flag_input.strip() == challenge.flag:
        # Check if already solved
        solved = await prisma.solve.find_unique(where={
            'team_id_challenge_id': {
                'team_id': int(current_user.id),
                'challenge_id': challenge.id
            }
        })
        
        if solved:
            return jsonify({'success': False, 'message': 'Already solved!', 'score': current_user.team.score})
        
        # Add Score and Solve record in a transaction if possible, or sequential
        async with prisma.tx() as transaction:
            await transaction.team.update(
                where={'id': int(current_user.id)},
                data={'score': {'increment': challenge.points}}
            )
            await transaction.solve.create(data={
                'team_id': int(current_user.id),
                'challenge_id': challenge.id
            })
        
        # Refresh current user score (in-memory or re-fetch)
        updated_team = await prisma.team.find_unique(where={'id': int(current_user.id)})
        current_user.team = updated_team
        
        print(f"DEBUG: Score updated for {current_user.name}. New Score: {updated_team.score}")
        return jsonify({'success': True, 'message': 'Correct! Flag Accepted.', 'score': updated_team.score})
    
    return jsonify({'success': False, 'message': 'Incorrect Flag.'})

@app.route('/download/<filename>')
def download_file(filename):
    upload_folder = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'downloads')
    return send_from_directory(upload_folder, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
