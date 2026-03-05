# Web Application Exercise

A little exercise to build a web application following an agile development process. See the [instructions](instructions.md) for more detail.

## Product vision statement

Our product is a software that provides movie enthusiasts a film forum to search and discover trending movies, rate and comment on films, save to folders and build their own collections and presents independent filmmakers a platform to submit and showcase films they directed.

## User stories

The User Stories can be found [here](https://github.com/swe-students-spring2026/2-web-app-crimson_comets/issues). 
They are all the issues that are labeled with the "user story" label.

## Steps necessary to run the software

### 1. Clone the Repository

```bash
git clone https://github.com/swe-students-spring2026/2-web-app-crimson_comets.git
cd 2-web-app-crimson_comets
```

### 2. Install Dependencies

Open the project in your preferred IDE (e.g., VS Code), then run in the terminal:
```bash
pip install -r requirements.txt
```

### 3. Set Up MongoDB Atlas

1. Go to [https://cloud.mongodb.com](https://cloud.mongodb.com) and create a free account.
2. Create a new cluster.
3. Go to **Database Access** → **Add New Database User**. Choose password authentication and note down the username and password.
4. Go to **Network Access** → **Add IP Address** → **Allow Access from Anywhere** (`0.0.0.0/0`).
5. Go back to your cluster → click **Connect** → **Drivers** → copy the connection string.

### 4. Create the `.env` File

In the project root directory (same level as `app.py`), create a file called `.env` with the following content:

```
MONGO_URI=mongodb+srv://YOUR_USERNAME:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/movie_app?retryWrites=true&w=majority
MONGO_DBNAME=movie_app
FLASK_SECRET_KEY=any-random-string-here
```

**Important:**
- Replace `YOUR_USERNAME`, `YOUR_PASSWORD`, and `cluster0.xxxxx.mongodb.net` with your actual MongoDB Atlas credentials.
- Add `/movie_app` after `.mongodb.net` and before `?` in the URI.

### 5. Run the Application

```bash
python app.py
```

The app will be available at [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Task boards

The Task Boards can be found [here](https://github.com/swe-students-spring2026/2-web-app-crimson_comets/projects?query=is%3Aopen).

## Team members

[Harrison Wong](https://github.com/harrisonmangitwong)
[Kara Jin](https://github.com/cynikjinchen)
[Xiongfeng Li](https://github.com/DaobaRoger12)
[Ginny (Chenyu) Jiang](https://github.com/ginny1536)
[Alan Wu](https://github.com/aw4630)
