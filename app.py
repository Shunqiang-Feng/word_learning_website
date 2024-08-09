from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os, secrets
import pandas as pd
import time

app = Flask(__name__)
app.config["SECRET_KEY"] = secrets.token_hex(16)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

word_dic = {1:'NumberName', 2: 'Office',    3:'Shopping',   4:'Work', 
            5:'Travel',     6:'School',     7:'Society',    8:'Technology',
            9:'Environment',10:'Finance',   11:'Health',    12:'Unclassified'}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    words = db.relationship("Word", backref="owner", lazy=True)


class Word(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    chapter = db.Column(db.Integer, nullable=False)
    index = db.Column(db.Integer, nullable=False)
    word = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="new")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user:
            if check_password_hash(user.password, password):
                session["user_id"] = user.id
                session["username"] = user.username
                return redirect(url_for("home", username = username))
            else:
                flash("Invalid password",'error')
        else:
            flash("Username does not exist. Please register (Redirct in 2 seconds).",'error')
            
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        
        # check if user_id exists
        if User.query.filter_by(username=username).first():
            flash("Username exists. Please Login directly.", 'warning')
            return render_template("register.html")

        # create new user
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        

        # get user id
        user_id = new_user.id

        # transverse
        for chapter in range(1, 13):
            file_path = os.path.join('static', 'word_info', 'xlsx', f'c{chapter}_{word_dic[chapter]}.xlsx')
            if os.path.exists(file_path):
                # get xlsx file
                df = pd.read_excel(file_path, header=None)
                

                # add words to table
                for index, row in df.iterrows():
                    word = str(row[0])
                    
                    if pd.isna(word) or not word.strip():
                        continue
                    new_word = Word(user_id=user_id, chapter=chapter, index=index + 1, word=word)
                    db.session.add(new_word)
                    db.session.commit()
                
        
        return redirect(url_for("login"))
    
    return render_template("register.html")



@app.route("/<username>/home")
def home(username):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = db.session.get(User, user_id)
    if not user or user.username != username:
        return redirect(url_for("login"))

    progress_data = []
    for chapter in range(1, 13):
        total_words = Word.query.filter_by(user_id=user_id, chapter=chapter).count()
        correct_words = Word.query.filter_by(user_id=user_id, chapter=chapter, status="correct").count()
        wrong_words = Word.query.filter_by(user_id=user_id, chapter=chapter, status="wrong").count()
        new_words = total_words - correct_words - wrong_words
        progress_data.append({
            "chapter": chapter,
            "correct": correct_words,
            "wrong": wrong_words,
            "new": new_words
        })

    return render_template("home.html", username=username, progress_data=progress_data, word_dic = word_dic)
    

@app.route("/<username>/learn", methods=["GET", "POST"])
def learn(username):
    # Check if user is logged in
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    # Retrieve the logged-in user
    user = db.session.get(User, user_id)
    if not user or user.username != username:
        return redirect(url_for("login"))

    feedback_message = None
    feedback_class = None

    
    if request.method == "POST":
        word_id = request.form["word_id"]
        user_input = request.form["user_input"].strip().lower()
        word = Word.query.get(word_id)
        print(f'it should be  : {word.word}')
        if word and word.owner.id == session["user_id"]:
            if user_input:
                if user_input == word.word.lower():
                    word.status = "correct"
                    feedback_message = f"Correct: {word.word}"
                    feedback_class = "success"  # Green
                else:
                    word.status = "wrong"
                    feedback_message = f"Wrong: {word.word}"
                    feedback_class = "danger"  # Red
            else:
                feedback_message = f"No Entered: {word.word}"
                feedback_class = "warning"  # Yellow
            db.session.commit()

            return jsonify({'message': feedback_message, 'class': feedback_class}), 200

    # If GET request or no POST data, proceed to show the next word
    chapter = request.args.get('chapter', type=int, default=1)
    new_word = (
        Word.query.filter_by(user_id=user_id, chapter=chapter, status="new")
        .order_by(db.func.random())
        .first()
    )
    print(f'print(new_word) : {new_word.word}')

    if not new_word:
        return render_template("all_done.html", username=username, chapter=chapter)

    correct_words = Word.query.filter_by(user_id=user_id, chapter=chapter, status="correct").count()
    wrong_words = Word.query.filter_by(user_id=user_id, chapter=chapter, status="wrong").count()
    new_words = Word.query.filter_by(user_id=user_id, chapter=chapter, status="new").count()

    progress_data = {
        "correct": correct_words,
        "wrong": wrong_words,
        "new": new_words
    }

    return render_template(
        "word_learning.html", 
        username=username, 
        chapter=chapter, 
        word=new_word, 
        progress_data=progress_data
    )



@app.route("/audio/<int:chapter>/<int:index>")
def audio(chapter, index):

    relative_path = os.path.join("word_info", "audio", "c"+str(chapter), f"{index}.mp3")
    file_path = os.path.join("static", relative_path)
    if os.path.exists(file_path):
        print('*'*40)
        
        return redirect(url_for('static', filename=relative_path.replace('\\', '/')))
    return "", 404




@app.route("/<username>/review")
def review(username):
    if "user_id" not in session:
        return redirect(url_for("login"))

    chapter = request.args.get('chapter', type=int)
    user_id = session["user_id"]
    wrong_word = (
        Word.query.filter_by(user_id=user_id, chapter=chapter, status="wrong")
        .order_by(db.func.random())
        .first()
    )

    if wrong_word:
        return render_template(
            f"word_reviewing.html", username=username, word=wrong_word
        )
    else:
        flash("No words to review in this chapter.")
        return redirect(url_for("home", username=username))


@app.route("/<username>/progress")
def progress(username):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    total_words = Word.query.filter_by(user_id=user_id).count()
    learned_words = Word.query.filter_by(user_id=user_id, status="correct").count()
    wrong_words = Word.query.filter_by(user_id=user_id, status="wrong").count()

    return render_template(
        f"progress.html", total=total_words, learned=learned_words, wrong=wrong_words
    )


@app.route("/<username>/account", methods=["GET", "POST"])
def account(username):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user = User.query.get(user_id)

    if request.method == "POST":
        if "change_password" in request.form:
            old_password = request.form["old_password"]
            new_password = request.form["new_password"]
            confirm_password = request.form["confirm_password"]

            if (
                check_password_hash(user.password, old_password)
                and new_password == confirm_password
            ):
                user.password = generate_password_hash(new_password, method="sha256")
                db.session.commit()
                flash("Password updated successfully")
            else:
                flash("Password update failed")

        elif "delete_account" in request.form:
            db.session.delete(user)
            db.session.commit()
            session.pop("user_id", None)
            return redirect(url_for("index"))

    return render_template(f"account.html")


@app.route("/update_status", methods=["POST"])
def update_status():
    if "user_id" not in session:
        return redirect(url_for("login"))

    word_id = request.form["word_id"]
    status = request.form["status"]
    word = Word.query.get(word_id)

    if word and word.owner.id == session["user_id"]:
        word.status = status
        db.session.commit()

    return redirect(request.referrer)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
