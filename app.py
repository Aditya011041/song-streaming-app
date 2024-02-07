from flask import Flask, g, jsonify, render_template, request, redirect, url_for
from ytmusicapi import YTMusic
import sqlite3
import requests

app = Flask(__name__)

# Initialize YTMusic API
yt = YTMusic('oauth.json')

# Function to get the database connection
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('myplaylist.db')
        db.row_factory = sqlite3.Row
    return db

# Function to close the database connection
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Function to execute a query and fetch all rows
def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

# Function to execute a query and commit changes
def execute_db(query, args=()):
    db = get_db()
    db.execute(query, args)
    db.commit()

# Create table to store songs if not exists
def create_table():
    execute_db('''
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY,
            title TEXT,
            video_id TEXT,
            mp3_link TEXT
        )
    ''')

@app.before_first_request
def initialize_database():
    create_table()  # Ensure table exists when the app starts

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.form['query']
    search_results = yt.search(query)
    top_5_results = search_results[:6]  # Slice to get only the top 5 results
    return render_template('results.html', results=top_5_results)

@app.route('/add_to_playlist', methods=['POST'])
def add_to_playlist():
    video_id = request.form['video_id']
    title = request.form['title']
    gaana_url = request.form['gaana_url']
    
    # Fetch MP3 link from Gaana API
    response = requests.get(f'http://127.0.0.1:8080/result/?url={gaana_url}')
    if response.status_code == 200:
        song_data = response.json()
        mp3_link = song_data.get('link')
    else:
        mp3_link = None
    
    # Insert song into SQLite database
    execute_db("INSERT INTO songs (title, video_id, mp3_link) VALUES (?, ?, ?)", (title, video_id, mp3_link))
    
    return redirect(url_for('index'))

@app.route('/saved_songs')
def saved_songs():
    songs = query_db("SELECT * FROM songs")
    return render_template('saved_songs.html', songs=songs)

@app.route('/remove_from_playlist/<int:song_id>', methods=['POST'])
def remove_from_playlist(song_id):
    # Remove song from SQLite database
    execute_db("DELETE FROM songs WHERE id = ?", (song_id,))
    return redirect(url_for('saved_songs'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
