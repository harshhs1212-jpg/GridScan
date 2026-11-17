from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os
import random
import shutil
from datetime import datetime

app = FastAPI()

# Frontend se connect karne ke liye
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "defects.db"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- 1. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS defects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id TEXT UNIQUE,
            severity TEXT,
            confidence REAL,
            lat REAL,
            lon REAL,
            timestamp TEXT,
            snapshot_path TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- 2. MOCK DELHI GPS ---
# Delhi ke aas-paas ke coordinates - har pothole thoda aage badhega
def get_mock_gps(index):
    # Connaught Place ke aas-paas se start
    base_lat = 28.6139
    base_lon = 77.2090
    # Har naye pothole ke liye thoda aage badhao
    lat = base_lat + (index * 0.001) + random.uniform(-0.0005, 0.0005)
    lon = base_lon + (index * 0.001) + random.uniform(-0.0005, 0.0005)
    return round(lat, 6), round(lon, 6)

# --- 3. MOCK TRACKER (Member 1 ka kaam yahan aayega) ---
# Abhi ke liye hum nakli detection kar rahe hai
# Baad me yahan Member 1 ka YOLO tracker lag jayega
def mock_tracker(video_path):
    # Maan lo video me 3 pothole mile
    results = []
    for i in range(3):
        results.append({
            "track_id": f"TRACK_{random.randint(1000, 9999)}",
            "severity": random.choice(["High", "Medium", "Low"]),
            "confidence": round(random.uniform(0.75, 0.98), 2),
        })
    return results

# --- 4. POST /process-video/ ---
@app.post("/process-video/")
async def process_video(file: UploadFile = File(...)):
    # Video ko save karo
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Tracker chalao (abhi mock hai)
    detections = mock_tracker(file_path)

    conn = sqlite3.connect(DB_PATH)
    saved = []
    for idx, det in enumerate(detections):
        lat, lon = get_mock_gps(idx)
        timestamp = datetime.now().isoformat()
        snapshot_path = f"snapshots/{det['track_id']}.jpg"

        try:
            conn.execute("""
                INSERT INTO defects (track_id, severity, confidence, lat, lon, timestamp, snapshot_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (det['track_id'], det['severity'], det['confidence'], lat, lon, timestamp, snapshot_path))
            saved.append(det['track_id'])
        except sqlite3.IntegrityError:
            # Agar track_id pehle se hai to skip karo - duplicate nahi save karna
            pass

    conn.commit()
    conn.close()

    return {"message": "Video processed", "saved_defects": len(saved), "track_ids": saved}

# --- 5. GET /defects/ ---
@app.get("/defects/")
def get_defects():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM defects").fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- 6. DELETE /reset/ ---
@app.delete("/reset/")
def reset_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM defects")
    conn.commit()
    conn.close()
    return {"message": "All defects deleted, database reset"}

@app.get("/")
def home():
    return {"message": "Backend chal raha hai!"}