from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask, daemon=True)
    t.start()
