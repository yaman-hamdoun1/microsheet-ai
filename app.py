import os
import tempfile
import glob
import time
import threading
import uuid
import json
import requests
from flask import Flask, render_template, request, send_file, after_this_request, jsonify
from werkzeug.utils import secure_filename

from extractor import extract_text_from_pdf
from compressor import compress_text
from generator_latex import create_cheat_sheet

app = Flask(__name__)

# Config
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 128 * 1024 * 1024

JOBS = {}

# --- KEYS ---
JSONBIN_ID = "694ec6edd0ea881f4041c405"
JSONBIN_KEY = "$2a$10$prBYnFrP8THHG6qkHcgE/.HBbXmtHW8l804eGpy.sbg2mvbzsZNiW"

print(f"--- APP STARTING ---")

def get_stats():
    """
    Fetches both Automations and Likes.
    Auto-migrates old DB format to new format if needed.
    """
    # START LIKES AT 10
    default_stats = {'automations': 150, 'likes': 10} 
    
    try:
        url = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}/latest"
        headers = {"X-Master-Key": JSONBIN_KEY}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json().get('record', {})
            
            # MIGRATION LOGIC: If old 'count' exists, map it to 'automations'
            if 'count' in data and 'automations' not in data:
                stats = {
                    'automations': data['count'],
                    'likes': 10  # Set initial migration value to 10
                }
                # Update DB immediately to new format
                threading.Thread(target=save_stats, args=(stats,)).start()
                return stats
            
            # Return current values or defaults
            return {
                'automations': data.get('automations', 150),
                'likes': data.get('likes', 10)
            }
            
    except Exception as e:
        print(f"DEBUG: Stats Read Error: {e}")
    
    return default_stats

def save_stats(new_data):
    """Helper to write to DB"""
    try:
        url = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"
        headers = {
            "Content-Type": "application/json",
            "X-Master-Key": JSONBIN_KEY
        }
        requests.put(url, json=new_data, headers=headers)
    except Exception as e:
        print(f"DEBUG: DB Write Error: {e}")

def increment_stat(stat_type):
    """Updates the count for 'automations' or 'likes'"""
    def _update():
        try:
            current = get_stats()
            # Increment the specific field
            if stat_type in current:
                current[stat_type] += 1
                save_stats(current)
                print(f"DEBUG: Incremented {stat_type} to {current[stat_type]}")
        except Exception as e:
            print(f"DEBUG: Increment Error: {e}")

    threading.Thread(target=_update).start()

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

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {'status': 'Initializing...', 'percent': 0, 'done': False}

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

    thread = threading.Thread(target=process_pipeline, args=(job_id, saved_paths))
    thread.start()

    return jsonify({'job_id': job_id})

@app.route('/status/<job_id>')
def get_status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)

@app.route('/api/stats')
def stats():
    return jsonify(get_stats())

# NEW ENDPOINT FOR LIKES
@app.route('/api/like', methods=['POST'])
def like_action():
    increment_stat('likes')
    return jsonify({'success': True})

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

        JOBS[job_id]['status'] = "Compressing text with AI..."
        JOBS[job_id]['percent'] = 50
        
        data = compress_text(combined_text)
        
        if not data:
            data = [{"title": "Error", "content": "AI failed. Using Backup."}]

        JOBS[job_id]['percent'] = 80

        JOBS[job_id]['status'] = "Compiling PDF..."
        
        output_filename = f"cheatsheet_{int(time.time())}.pdf"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        create_cheat_sheet(data, output_path)

        # Increment Automation Stat
        increment_stat('automations')

        JOBS[job_id]['status'] = "Complete!"
        JOBS[job_id]['percent'] = 100
        JOBS[job_id]['filename'] = output_filename
        JOBS[job_id]['done'] = True
        
    except Exception as e:
        print(f"Error in thread: {e}")
        JOBS[job_id]['status'] = f"Error: {str(e)}"
        JOBS[job_id]['percent'] = 0

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)