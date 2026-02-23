from flask import Flask, render_template, request

app = Flask(__name__)


# HOME PAGE
@app.route("/")
def home():
    return render_template("home.html")


# SEARCH RESULTS PAGE
@app.route("/search")
def search():
    query = request.args.get("q", "")
    return render_template("results.html", query=query)


# MOVIE DETAIL PAGE
@app.route("/movie/<movie_id>")
def movie_detail(movie_id):
    return render_template("movie_detail.html", movie_id=movie_id)


# ADD MOVIE PAGE
@app.route("/movies/new", methods=["GET", "POST"])
def add_movie():
    if request.method == "POST":
        # dummy for now
        print("Movie submitted")
    return render_template("add_movie.html")


if __name__ == "__main__":
    app.run(debug=True)