import os
from dataclasses import dataclass
from dotenv import load_dotenv

from flask import Flask, render_template, redirect, url_for, request
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_fallback_secret")

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)


    @dataclass
    class DummyUser(UserMixin):
        id: str
        username: str
        role: str


    DUMMY_USERS = {
        "u1": DummyUser(id="u1", username="roger_user", role="user"),
        "f1": DummyUser(id="f1", username="roger_filmmaker", role="filmmaker"),
    }


    @login_manager.user_loader
    def load_user(user_id: str):
        return DUMMY_USERS.get(user_id)


    # ---------- Auth / entry ----------
    @app.get("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("login"))
        return "User is not authenticated"

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            role = request.form.get("role", "user")
            username = (request.form.get("username") or "").strip() or (
                "roger_user" if role == "user" else "roger_filmmaker"
            )

            user_obj = DUMMY_USERS["u1"] if role == "user" else DUMMY_USERS["f1"]
            user_obj.username = username
            login_user(user_obj)
            return redirect(url_for("home"))

        return render_template("login.html")


    @app.get("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))


    # ---------- Home ----------
    @app.get("/home")
    @login_required
    def home():
        if getattr(current_user, "role", "user") == "filmmaker":
            profile_data = {
                "display_name": current_user.username,
                "bio": "Filmmaker profile (dummy). Post movies and track audience engagement.",
                "stats": {
                    "movies_posted": 6,
                    "total_views": 12840,
                    "total_comments": 912,
                    "avg_rating": 4.6,
                },
                "folders": [
                    {"name": "My Inspirations", "count": 9},
                    {"name": "My Favorites", "count": 14},
                    {"name": "Cool stuff", "count": 6},
                ],
                "my_movies": [
                    {"title": "My Short Film A", "status": "Published", "views": 3200, "comments": 210},
                ],
            }
        else:
            profile_data = {
                "display_name": current_user.username,
                "bio": "Movie lover profile (dummy). Save films, organize folders, and write reviews.",
                "folders": [
                    {"name": "Watch Later", "count": 12},
                    {"name": "Top Rated", "count": 8},
                    {"name": "Comedy Nights", "count": 5},
                ],
                "stats": {
                    "folders": 3,
                    "saved_movies": 25,
                    "reviews_written": 4,
                },
            }

        return render_template("home.html", user=current_user, profile=profile_data)


    # ---------- Search pages (Kara) ----------
    @app.get("/search")
    @login_required
    def search():
        query = request.args.get("q", "")
        return render_template("results.html", query=query, user=current_user)


    @app.get("/movie/<movie_id>")
    @login_required
    def movie_detail(movie_id):
        return render_template("movie_detail.html", movie_id=movie_id, user=current_user)


    @app.route("/movies/new", methods=["GET", "POST"])
    @login_required
    def add_movie():
        if request.method == "POST":
            # dummy for now
            print("Movie submitted (dummy).")
            return redirect(url_for("home"))

        return render_template("add_movie.html", user=current_user)

    DUMMY_MOVIE = {
        "_id": 3,
        "title": "XXX",
        "year": 2025,
        "genre": "Comedy",
        "logline": "A film about a student struggling in software engineering class",
        "runtime": "20 min",
        "director": "Roger(you)",
        "cast": [
            {"name": "Timothée Chalamet", "role": "Lead Actor"}, 
            {"name": "Zendaya", "role": "Supporting Actor"}, 
        ],
        "crew": [
            {"name": "Roger Geakins", "role": "Cinematographer"},
            {"name": "Michael P. Shawver", "role": "Editor"},
        ],
        "poster": "https://via.placeholder.com/120x180?text=Poster",
        "awards": "Oscar Best Cinematography",
        "avg_rating": 4.4,
        "total_ratings": 123,
    }

    DUMMY_COMMENTS = [
        {
            "_id": "c1",
            "author": "alice",
            "time": "2 days ago",
            "text": "Incredible cinematography and sound design. Slow pace but worth it.",
            "likes": 38,
        },
        {
            "_id": "c2",
            "author": "ginny",
            "time": "1 hour ago",
            "text": "Outstanding in the Indie Film world",
            "likes": 4,
        },
    ]


    # ---------- POST Movie (Ginny) ----------
    @app.route("/post", methods=["GET", "POST"])
    @login_required
    def post_movie():
        if request.method == "POST":
            #dummy for now
            print("Your film is successfullt posted!")
            return redirect(url_for("home"))
        
        return render_template("post_movie.html", movie=None, user=current_user)

    @app.route("/post/edit/<movie_id>", methods=["GET", "POST"])
    @login_required
    def edit_my_movie(movie_id):
        return render_template("post_movie.html", movie=DUMMY_MOVIE, user=current_user)

    # ---------- My Movie (Ginny) ----------
    @app.route("/my-movie/<movie_id>")
    @login_required
    def my_movie(movie_id):
        return render_template("my_movie.html", movie=DUMMY_MOVIE, comments=DUMMY_COMMENTS, user=current_user)

    # ---------- Folders (Harrison) ----------
    @app.get("/folders")
    @login_required
    def folders():
        return render_template("folders.html", user=current_user)

    return app




app = create_app()

if __name__ == "__main__":
    FLASK_PORT = os.getenv("FLASK_PORT", "5000")

    app.run(port=FLASK_PORT, debug=True)
