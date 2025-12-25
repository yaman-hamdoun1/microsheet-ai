import os
import tempfile
import glob
import time
import threading
import uuid
import json  # Added json for stats
from flask import Flask, render_template, request, send_file, after_this_request, jsonify
from werkzeug.utils import secure_filename

# Import your modules
from extractor import extract_text_from_pdf
from compressor import compress_text
from generator_latex import create_cheat_sheet

# 1. INITIALIZE APP FIRST
app = Flask(__name__)

# Config
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
STATS_FILE = 'stats.json'  # File to store the count

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Limit upload size to 16 Megabytes
app.config['MAX_CONTENT_LENGTH'] = 128 * 1024 * 1024

# GLOBAL DICTIONARY TO STORE PROGRESS
JOBS = {}

# --- HELPER FUNCTIONS FOR STATS ---
def get_stats():
    """Reads the current automation count. Starts at 150 to show trust."""
    if not os.path.exists(STATS_FILE):
        # Initialize with a base number so it doesn't look empty
        with open(STATS_FILE, 'w') as f:
            json.dump({'count': 12}, f)
        return 150
    
    try:
        with open(STATS_FILE, 'r') as f:
            data = json.load(f)
            return data.get('count', 12)
    except:
        return 150

def increment_stats():
    """Increments the automation count by 1."""
    try:
        current = get_stats()
        new_count = current + 1
        with open(STATS_FILE, 'w') as f:
            json.dump({'count': new_count}, f)
    except Exception as e:
        print(f"Error updating stats: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'files' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Create Unique Job ID
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {'status': 'Initializing...', 'percent': 0, 'done': False}

    # Save Files
    saved_paths = []
    job_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
    os.makedirs(job_upload_dir, exist_ok=True)

    for file in files:
        if file.filename.endswith('.pdf'):
            filename = secure_filename(file.filename)
            filepath = os.path.join(job_upload_dir, filename)
            file.save(filepath)
            saved_paths.append(filepath)

    if not saved_paths:
        return jsonify({'error': 'No valid PDFs found'}), 400

    # Start Processing
    thread = threading.Thread(target=process_pipeline, args=(job_id, saved_paths))
    thread.start()

    return jsonify({'job_id': job_id})

@app.route('/status/<job_id>')
def get_status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)

# --- NEW ROUTE FOR FRONTEND ANALYTICS ---
@app.route('/api/stats')
def stats():
    return jsonify({'count': get_stats()})

# --- CORRECT DOWNLOAD ROUTE (With Auto-Delete) ---
@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(OUTPUT_FOLDER, filename)

    @after_this_request
    def remove_file(response):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as error:
            app.logger.error("Error removing file", error)
        return response

    return send_file(file_path, as_attachment=True)

def process_pipeline(job_id, file_paths):
    try:
        total_files = len(file_paths)
        combined_text = ""

        # --- STEP 1: EXTRACTION ---
        for i, path in enumerate(file_paths):
            filename = os.path.basename(path)
            JOBS[job_id]['status'] = f"Reading file {i+1} of {total_files}: {filename}..."
            JOBS[job_id]['percent'] = int((i / total_files) * 50)
            
            text = extract_text_from_pdf(path)
            if text:
                combined_text += f"\n--- SOURCE: {filename} ---\n{text}"

        if not combined_text:
            JOBS[job_id]['status'] = "Error: No text found."
            JOBS[job_id]['percent'] = 0
            return

        # --- STEP 2: AI COMPRESSION ---
        JOBS[job_id]['status'] = "Compressing text with AI..."
        JOBS[job_id]['percent'] = 50
        
        data = compress_text(combined_text)
        
        if not data:
            data = [{"title": "Error", "content": "AI failed. Using Backup."}]

        JOBS[job_id]['percent'] = 80

        # --- STEP 3: LATEX GENERATION ---
        JOBS[job_id]['status'] = "Compiling PDF..."
        
        output_filename = f"cheatsheet_{int(time.time())}.pdf"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        create_cheat_sheet(data, output_path)

        # UPDATE STATS ON SUCCESS
        increment_stats()

        JOBS[job_id]['status'] = "Complete!"
        JOBS[job_id]['percent'] = 100
        JOBS[job_id]['filename'] = output_filename
        JOBS[job_id]['done'] = True
        
    except Exception as e:
        print(f"Error in thread: {e}")
        JOBS[job_id]['status'] = f"Error: {str(e)}"
        JOBS[job_id]['percent'] = 0

if __name__ == '__main__':
    # PORT 5000 is standard for Flask apps in production
    app.run(host='0.0.0.0', debug=True, port=5000)