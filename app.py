from flask import Flask, render_template, send_from_directory, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from generated_prisma import Prisma
import os
import asyncio
import traceback

# -------------------------------------------------
# APP CONFIG
# -------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# -------------------------------------------------
# PRISMA + GLOBAL EVENT LOOP (CRITICAL FIX)
# -------------------------------------------------

prisma = Prisma()

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

def run_async(coro):
    return loop.run_until_complete(coro)

# Connect Prisma ONCE
run_async(prisma.connect())

# -------------------------------------------------
# DATABASE INITIALIZATION (RUNS ONCE)
# -------------------------------------------------

def init_db():
    try:
        if run_async(prisma.challenge.count()) > 0:
            return

        challenges = [
            {
                "title": "The Source",
                "category": "Reverse Engineering",
                "difficulty": "Easy",
                "points": 100,
                "description": "Can you reverse this script and find the flag?",
                "file_url": "rev_challenge.py",
                "flag": "flag{Typo_and_Sympo}"
            },
            {
                "title": "Binary Whisperer",
                "category": "OSINT",
                "difficulty": "Medium",
                "points": 250,
                "description": "Hidden clues are everywhere.",
                "file_url": None,
                "flag": "Flag{OSINT_Made_Easy}"
            },
            {
                "title": "Client Side Truth",
                "category": "Web Exploitation",
                "difficulty": "Medium",
                "points": 300,
                "description": "Look at the client side carefully.",
                "file_url": None,
                "flag": "flag{cl13nt_s1d3_truth}"
            },
            {
                "title": "Hidden in Plain Sight",
                "category": "Steganography",
                "difficulty": "Hard",
                "points": 500,
                "description": "Some things hide quietly.",
                "file_url": "stego_challenge.jpg",
                "flag": "flag{Simply_Scan_Me}"
            }
        ]

        for c in challenges:
            run_async(prisma.challenge.create(data=c))

        if not run_async(prisma.team.find_unique(where={"name": "AdminTeam"})):
            run_async(prisma.team.create(data={
                "name": "AdminTeam",
                "email": "admin@hackerz.com",
                "password_hash": generate_password_hash(
                    os.environ.get("ADMIN_PASSWORD", "admin123")
                ),
                "score": 0
            }))

        print("Database initialized successfully")

    except Exception:
        print(traceback.format_exc())

# Run once at startup
init_db()

# -------------------------------------------------
# LOGIN MANAGER
# -------------------------------------------------

class User(UserMixin):
    def __init__(self, team):
        self.id = str(team.id)
        self.team = team

@login_manager.user_loader
def load_user(user_id):
    team = run_async(prisma.team.find_unique(where={"id": int(user_id)}))
    return User(team) if team else None

# -------------------------------------------------
# ROUTES
# -------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        team = run_async(prisma.team.find_unique(where={"email": email}))
        if team and check_password_hash(team.password_hash, password):
            login_user(User(team))
            return redirect(url_for("ctf"))

        flash("Invalid email or password")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        team_name = request.form.get("team_name")
        email = request.form.get("email")
        password = request.form.get("password")

        if not team_name or not email or not password:
            flash("All fields required")
            return redirect(url_for("register"))

        if run_async(prisma.team.find_unique(where={"email": email})):
            flash("Email already registered")
            return redirect(url_for("register"))

        if run_async(prisma.team.find_unique(where={"name": team_name})):
            flash("Team name already taken")
            return redirect(url_for("register"))

        team = run_async(prisma.team.create(data={
            "name": team_name,
            "email": email,
            "password_hash": generate_password_hash(password),
            "score": 0
        }))

        login_user(User(team))
        return redirect(url_for("ctf"))

    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/ctf")
@login_required
def ctf():
    challenges = run_async(prisma.challenge.find_many())
    solves = run_async(prisma.solve.find_many(
        where={"team_id": int(current_user.id)}
    ))
    solved_ids = [s.challenge_id for s in solves]

    return render_template(
        "ctf.html",
        challenges=challenges,
        solved_ids=solved_ids
    )

@app.route("/leaderboard")
@login_required
def leaderboard():
    teams = run_async(
        prisma.team.find_many(order={"score": "desc"})
    )
    return render_template("leaderboard.html", leaderboard=teams)

@app.route("/api/solve", methods=["POST"])
@login_required
def solve():
    data = request.json
    flag_input = data.get("flag")
    challenge_id = int(data.get("challenge_id"))

    challenge = run_async(
        prisma.challenge.find_unique(where={"id": challenge_id})
    )

    if not challenge or flag_input.strip() != challenge.flag:
        return jsonify({"success": False, "message": "Wrong flag"})

    solved = run_async(prisma.solve.find_unique(where={
        "team_id_challenge_id": {
            "team_id": int(current_user.id),
            "challenge_id": challenge.id
        }
    }))

    if solved:
        return jsonify({"success": False, "message": "Already solved"})

    run_async(prisma.team.update(
        where={"id": int(current_user.id)},
        data={"score": {"increment": challenge.points}}
    ))

    run_async(prisma.solve.create(data={
        "team_id": int(current_user.id),
        "challenge_id": challenge.id
    }))

    updated = run_async(prisma.team.find_unique(
        where={"id": int(current_user.id)}
    ))

    current_user.team = updated

    return jsonify({
        "success": True,
        "message": "Correct flag!",
        "score": updated.score
    })

@app.route("/download/<filename>")
def download_file(filename):
    path = os.path.join(app.root_path, "static", "downloads")
    return send_from_directory(path, filename, as_attachment=True)

# -------------------------------------------------
# ERROR HANDLER
# -------------------------------------------------

@app.errorhandler(Exception)
def handle_exception(e):
    print(traceback.format_exc())
    return "Internal Server Error", 500
