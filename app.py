import os
from dataclasses import dataclass
from datetime import datetime

from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
import hashlib

from flask import Flask, render_template, redirect, url_for, request, session, abort, flash
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DBNAME")]


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_fallback_secret")

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)


    class User(UserMixin):
        def __init__(self, user_doc):
            self.id = str(user_doc["_id"])
            self.username = user_doc["username"]
            self.role = user_doc.get("role", "user")
            self.bio = user_doc.get("bio", "")

    @login_manager.user_loader
    def load_user(user_id):
        user_doc = db.users.find_one({"_id": ObjectId(user_id)})
        if user_doc:
            return User(user_doc)
        return None


    # ---------- Helpers ----------
    def oid(s: str) -> ObjectId:
        """Parse ObjectId or 404."""
        try:
            return ObjectId(s)
        except Exception:
            abort(404)

    def split_csv(s: str):
        """'a, b, c' -> ['a','b','c']"""
        if not s:
            return []
        return [x.strip() for x in s.split(",") if x.strip()]


    # ---------- Auth / entry ----------
    @app.get("/")
    def index():
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()


            user_doc = db.users.find_one({"username": username})
            hashed_input = hashlib.sha256(password.encode("utf-8")).hexdigest()

            if not user_doc or hashed_input != user_doc["password"]:
                flash("Invalid username or password.")
                return redirect(url_for("login"))

            login_user(User(user_doc))
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
        user_id = str(current_user.id)
        all_movies = list(db.movies.find())
        for m in all_movies:
            m["avg_rating"] = 0
            m["comment_count"] = db.comments.count_documents({"movie_id": m["_id"]})
            ratings = list(db.ratings.find({"movie_id": m["_id"]}))
            if ratings:
                m["avg_rating"] = sum(r["rating"] for r in ratings) / len(ratings)
            m["trending_score"] = m["avg_rating"] * 2 + len(ratings) + m["comment_count"]

        movies = sorted(all_movies, key=lambda x: x["trending_score"], reverse=True)[:3]

        if getattr(current_user, "role", "user") == "filmmaker":
            folders = list(db.folders.find({"user_id": user_id}))
            for f in folders:
                f["count"] = len(f.get("movie_ids", []))
            my_movies = list(db.movies.find({"created_by": ObjectId(current_user.id)}).sort("created_at", -1))
            for m in my_movies:
                m["comments_count"] = db.comments.count_documents({
                    "movie_id": m["_id"]
                })
            profile_data = {
                "display_name": current_user.username,
                "bio": current_user.bio or "No bio yet.",
                "stats": {
                    "movies_posted": len(my_movies),
                    "total_views": sum(m.get("views", 0) for m in my_movies),
                    "total_comments": db.comments.count_documents({
                        "author_id": user_id
                    }),
                },
                "my_movies": my_movies,
                "folders": folders
            }
        else:
            folders = list(db.folders.find({"user_id": user_id}))
            for f in folders:
                f["count"] = len(f.get("movie_ids", []))

            profile_data = {
                "display_name": current_user.username,
                "bio": current_user.bio or "No bio yet.",
                "folders": folders,
                "stats": {
                    "folders": len(folders),
                    "saved_movies": sum(len(f.get("movie_ids", [])) for f in folders),
                    "reviews_written": db.comments.count_documents({
                        "author_id": user_id
                    }),
                },
            }

        return render_template(
            "home.html",
            user=current_user,
            profile=profile_data,
            movies=movies,
        )
    # --------- Profile edit ----------
    @app.route("/profile/edit", methods=["GET", "POST"])
    @login_required
    def edit_profile():
        if request.method == "POST":
            new_bio = request.form.get("bio", "").strip()
            db.users.update_one(
                {"_id": ObjectId(current_user.id)},
                {"$set": {"bio": new_bio}}
            )
            flash("Profile updated!")
            return redirect(url_for("home"))

        return render_template("edit_profile.html", user=current_user)

    # ---------- Search pages (Kara) ----------
    @app.get("/search")
    @login_required
    def search():
        query = request.args.get("q", "").strip()

        movies = []
        if query:
            movies = list(db.movies.find({
                "$or": [
                    {"title": {"$regex": query, "$options": "i"}},
                    {"genre": {"$regex": query, "$options": "i"}},
                ]
            }))

        return render_template(
            "results.html",
            query=query,
            movies=movies,
            user=current_user,
        )


    # ---------- Add pages (Kara) ----------
    @app.route("/movies/new", methods=["GET", "POST"])
    @login_required
    def add_movie():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            year_raw = request.form.get("year", "").strip()
            genre = request.form.get("genre", "").strip()
            director = request.form.get("director", "").strip()
            poster = request.form.get("poster", "").strip()

            cast_raw = request.form.get("cast", "").strip()
            crew_raw = request.form.get("crew", "").strip()

            synopsis = request.form.get("synopsis", "").strip()
            reason = request.form.get("reason", "").strip()
            bts = request.form.get("bts", "").strip()

            if not title:
                return "Movie Title is required", 400
            if not director:
                return "Director is required", 400

            year = int(year_raw) if year_raw.isdigit() else None

            movie_doc = {
                "title": title,
                "year": year,
                "genre": genre or None,
                "director": director,
                "cast": split_csv(cast_raw),
                "crew": split_csv(crew_raw),
                "synopsis": synopsis or None,
                "reason": reason or None,
                "bts": bts or None,
                "poster": poster or None,
                "created_at": datetime.utcnow(),
                "created_by": getattr(current_user, "id", None),
            }

            result = db.movies.insert_one(movie_doc)
            print("Inserted movie:", result.inserted_id)

            return redirect(url_for("home"))

        return render_template("add_movie.html", user=current_user)


    # ---------- Movie detail + comments + ratings (Kara) ----------
    @app.get("/movie/<movie_id>")
    @login_required
    def movie_detail(movie_id):
        movie = db.movies.find_one({"_id": oid(movie_id)})
        if not movie:
            abort(404)

        comments = list(
            db.comments.find({"movie_id": movie["_id"]}).sort("created_at", -1)
        )


        # --- ratings: your rating + summary (avg, count) ---
        user_id = str(getattr(current_user, "id", ""))

        your_rating = db.ratings.find_one({
            "movie_id": movie["_id"],
            "user_id": user_id,
        })

        agg = list(db.ratings.aggregate([
            {"$match": {"movie_id": movie["_id"]}},
            {"$group": {"_id": "$movie_id", "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}},
        ]))

        rating_summary = {"avg": None, "count": 0}
        if agg:
            rating_summary["avg"] = agg[0]["avg"]
            rating_summary["count"] = agg[0]["count"]

        return render_template(
            "movie_detail.html",
            movie=movie,
            comments=comments,
            your_rating=your_rating,
            rating_summary=rating_summary,
            user=current_user,
        )


    @app.post("/movie/<movie_id>/rating")
    @login_required
    def rating_upsert(movie_id):
        movie_obj_id = oid(movie_id)

        rating_raw = request.form.get("rating", "").strip()
        if not rating_raw.isdigit():
            return "Rating must be 1-5", 400

        rating_val = int(rating_raw)
        if rating_val < 1 or rating_val > 5:
            return "Rating must be 1-5", 400

        user_id = str(getattr(current_user, "id", ""))
        now = datetime.utcnow()

        existing = db.ratings.find_one({"movie_id": movie_obj_id, "user_id": user_id})
        if existing:
            db.ratings.update_one(
                {"_id": existing["_id"]},
                {"$set": {"rating": rating_val, "updated_at": now}},
            )
        else:
            db.ratings.insert_one({
                "movie_id": movie_obj_id,
                "user_id": user_id,
                "rating": rating_val,
                "created_at": now,
                "updated_at": None,
            })

        return redirect(url_for("movie_detail", movie_id=movie_id))


    @app.post("/movie/<movie_id>/rating/delete")
    @login_required
    def rating_delete(movie_id):
        db.ratings.delete_one({
            "movie_id": oid(movie_id),
            "user_id": str(getattr(current_user, "id", "")),
        })
        return redirect(url_for("movie_detail", movie_id=movie_id))


    @app.post("/movie/<movie_id>/comments/new")
    @login_required
    def comment_new(movie_id):
        movie_obj_id = oid(movie_id)
        content = request.form.get("content", "").strip()
        if not content:
            return "Comment cannot be empty", 400

        doc = {
            "movie_id": movie_obj_id,
            "author_id": str(getattr(current_user, "id", "")),
            "author_name": getattr(current_user, "username", "user"),
            "content": content,
            "likes": 0,
            "created_at": datetime.utcnow(),
            "updated_at": None,
        }
        db.comments.insert_one(doc)
        return redirect(url_for("movie_detail", movie_id=movie_id))


    @app.post("/movie/<movie_id>/comments/<comment_id>/like")
    @login_required
    def comment_like(movie_id, comment_id):
        db.comments.update_one(
            {"_id": oid(comment_id), "movie_id": oid(movie_id)},
            {"$inc": {"likes": 1}},
        )
        return redirect(url_for("movie_detail", movie_id=movie_id))


    @app.post("/movie/<movie_id>/comments/<comment_id>/delete")
    @login_required
    def comment_delete(movie_id, comment_id):
        db.comments.delete_one(
            {
                "_id": oid(comment_id),
                "movie_id": oid(movie_id),
                "author_id": str(getattr(current_user, "id", "")),
            }
        )
        return redirect(url_for("movie_detail", movie_id=movie_id))


    @app.route("/movie/<movie_id>/comments/<comment_id>/edit", methods=["GET", "POST"])
    @login_required
    def comment_edit(movie_id, comment_id):
        comment = db.comments.find_one(
            {
                "_id": oid(comment_id),
                "movie_id": oid(movie_id),
                "author_id": str(getattr(current_user, "id", "")),
            }
        )
        if not comment:
            abort(404)

        if request.method == "POST":
            content = request.form.get("content", "").strip()
            if not content:
                return "Comment cannot be empty", 400

            db.comments.update_one(
                {"_id": comment["_id"]},
                {"$set": {"content": content, "updated_at": datetime.utcnow()}},
            )
            return redirect(url_for("movie_detail", movie_id=movie_id))

        return render_template(
            "comment_edit.html",
            comment=comment,
            movie_id=movie_id,
            user=current_user,
        )


    # ---------- POST Movie (Ginny) ----------
    @app.route("/post", methods=["GET", "POST"])
    @login_required
    def post_movie():
        if request.method == "POST":
            title = request.form.get('title')
            year = request.form.get('year')
            genre = request.form.get('genre')
            director = current_user.username
            logline = request.form.get('logline')
            runtime = request.form.get('runtime')

            cast_input = request.form.get('cast', '').split(',')
            cast = []
            for each_cast in cast_input:
                if ':' in each_cast:
                    name, role = each_cast.split(':', 1)
                    cast.append({
                        "name": name.strip(),
                        "role": role.strip()
                    })

            crew_input = request.form.get('crew', '').split(',')
            crew = []
            for each_crew in crew_input:
                if ':' in each_crew:
                    name, role = each_crew.split(':', 1)
                    crew.append({
                        'name': name.strip(),
                        'role': role.strip()
                    })

            awards = request.form.get('awards')

            poster_file = request.files.get('poster')
            stills_file = request.files.get('stills')
            bts_file = request.files.get('bts')

            poster_filename = None
            stills_filename = None
            bts_filename = None

            if poster_file and poster_file.filename:
                poster_file.save(f'images/movie_photos/{poster_file.filename}')
                poster_filename = poster_file.filename
            if stills_file and stills_file.filename:
                stills_file.save(f'images/movie_photos/{stills_file.filename}')
                stills_filename = stills_file.filename
            if bts_file and bts_file.filename:
                bts_file.save(f'images/movie_photos/{bts_file.filename}')
                bts_filename = bts_file.filename

            doc = {
                "title": title,
                "year": year,
                "genre": genre,
                "director": director,
                "logline": logline,
                "runtime": runtime,
                "cast": cast,
                "crew": crew,
                "status": "published",
                "awards": awards,
                "poster": poster_filename,
                "stills": stills_filename,
                "bts": bts_filename,
                "created_by": ObjectId(current_user.id),
                "created_at": datetime.utcnow(),
            }
            
            db.movies.insert_one(doc)
                
            return redirect(url_for("home"))
        
        return render_template("post_movie.html", movie=None, user=current_user)

    @app.route("/post/edit/<movie_id>", methods=["GET"])
    @login_required
    def edit_my_movie(movie_id):
        movie = db.movies.find_one({"_id": ObjectId(movie_id)})
        return render_template("post_movie.html", movie=movie, user=current_user)

    @app.route("/post/edit/<movie_id>", methods=["POST"])
    @login_required
    def update_my_movie(movie_id):
        title = request.form.get('title')
        year = request.form.get('year')
        genre = request.form.get('genre')
        director = current_user.username
        logline = request.form.get('logline')
        runtime = request.form.get('runtime')

        cast_input = request.form.get('cast', '').split(',')
        cast = []
        for each_cast in cast_input:
            if ':' in each_cast:
                name, role = each_cast.split(':', 1)
                cast.append({
                    "name": name.strip(),
                    "role": role.strip()
                })

        crew_input = request.form.get('crew', '').split(',')
        crew = []
        for each_crew in crew_input:
            if ':' in each_crew:
                name, role = each_crew.split(':', 1)
                crew.append({
                    'name': name.strip(),
                    'role': role.strip()
                })

        awards = request.form.get('awards')

        poster_file = request.files.get('poster')
        stills_file = request.files.get('stills')
        bts_file = request.files.get('bts')

        poster_filename = None
        stills_filename = None
        bts_filename = None

        if poster_file and poster_file.filename:
            poster_file.save(f'images/movie_photos/{poster_file.filename}')
            poster_filename = poster_file.filename
        if stills_file and stills_file.filename:
            stills_file.save(f'images/movie_photos/{stills_file.filename}')
            stills_filename = stills_file.filename
        if bts_file and bts_file.filename:
            bts_file.save(f'images/movie_photos/{bts_file.filename}')
            bts_filename = bts_file.filename

        doc = {
            "title": title,
            "year": year,
            "genre": genre,
            "director": director,
            "logline": logline,
            "runtime": runtime,
            "cast": cast,
            "crew": crew,
            "status": "published",
            "awards": awards,
            "poster": poster_filename,
            "stills": stills_filename,
            "bts": bts_filename,
            "created_by": ObjectId(current_user.id),
            "created_at": datetime.utcnow(),
        }
        
        db.movies.update_one({"_id": ObjectId(movie_id)}, {"$set": doc}) 
        return redirect(url_for("home"))          

    @app.route("/post/delete/<movie_id>")
    @login_required
    def delete_my_movie(movie_id):
        db.movies.delete_one({"_id": ObjectId(movie_id)})
        return redirect(url_for("home"))

    # ---------- My Movie (Ginny) ----------
    @app.route("/my-movie/<movie_id>")
    @login_required
    def my_movie(movie_id):
        movie = db.movies.find_one({'_id': ObjectId(movie_id)})
        comments = list(
            db.comments.find({"movie_id": ObjectId(movie_id)}).sort("created_at", -1)
        )
        return render_template("my_movie.html", movie=movie, comments=comments, user=current_user)

    @app.route("/my-movie/<movie_id>/<comment_id>", methods=["POST"])
    @login_required
    def reply_my_movie(movie_id, comment_id):
        reply = request.form.get('reply')
        db.comments.update_one({"_id": ObjectId(comment_id)}, {"$push": {"replies": reply}})
        movie = db.movies.find_one({"_id": ObjectId(movie_id)})
        return redirect(url_for('my_movie', movie_id=movie_id))

    # ---------- Folders (Harrison) ----------
    @app.route("/folders/new", methods=["GET", "POST"])
    @login_required
    def create_folder():
        user_id = str(current_user.id)

        if request.method == "POST":
            name = request.form.get("name", "").strip()

            if not name:
                flash("Please enter a folder name.")
                return redirect(url_for("create_folder"))

            doc = {
                "user_id": user_id,
                "name": name,
                "movie_ids": [],
                "created_at": datetime.utcnow(),
                "updated_at": None,
            }

            db.folders.insert_one(doc)

            return redirect(url_for("folders"))

        return render_template("create_folder.html", user=current_user)
    
    @app.route("/folders", methods=["GET"])
    @login_required
    def folders():
        user_id = str(current_user.id)
        folders_list = list(db.folders.find({"user_id": user_id}).sort("created_at", -1))
        for folder in folders_list:
            folder["count"] = len(folder.get("movie_ids", []))

        return render_template("folders.html", user=current_user, folders=folders_list)

    @app.post("/folders/<folder_id>/delete")
    @login_required
    def delete_folder(folder_id):
        db.folders.delete_one({
            "_id": oid(folder_id),
            "user_id": str(current_user.id)
        })
        return redirect(url_for("folders"))
    
    # ---------- Registers ---------
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            role = request.form.get("role", "user")


            if db.users.find_one({"username": username}):
                flash("Username already exists.")
                return redirect(url_for("register"))

            hashed = hashlib.sha256(password.encode("utf-8")).hexdigest()

            db.users.insert_one({
                "username": username,
                "password": hashed,
                "role": role,
                "bio": "",
                "created_at": datetime.utcnow(),
            })

            return redirect(url_for("login"))

        return render_template("register.html")
    return app

app = create_app()

if __name__ == "__main__":
    FLASK_PORT = os.getenv("FLASK_PORT", "5000")
    app.run(port=int(FLASK_PORT), debug=True)