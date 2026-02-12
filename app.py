"""
Amdox AI-Powered Task Optimizer
Flask-based emotion analysis and task recommendation system
With Image, Video, and Voice Analysis
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime
import sqlite3
import json
import base64
import os
from collections import Counter
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads directory
os.makedirs('uploads', exist_ok=True)

# ============================================
# DATABASE LAYER WITH MIGRATION
# ============================================

def init_db():
    """Initialize SQLite database with migration support"""
    conn = sqlite3.connect('amdox.db')
    c = conn.cursor()
    
    # Check if old table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mood_logs'")
    table_exists = c.fetchone()
    
    if table_exists:
        # Check if new columns exist
        c.execute("PRAGMA table_info(mood_logs)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'input_type' not in columns:
            print("Migrating database: Adding new columns...")
            # Create new table with all columns
            c.execute('''CREATE TABLE mood_logs_new
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          employee_id TEXT,
                          emotion TEXT,
                          burnout_score INTEGER,
                          recommended_task TEXT,
                          input_type TEXT DEFAULT 'text',
                          confidence REAL DEFAULT 0.85,
                          timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            
            # Copy old data
            c.execute('''INSERT INTO mood_logs_new 
                         (id, employee_id, emotion, burnout_score, recommended_task, timestamp)
                         SELECT id, employee_id, emotion, burnout_score, recommended_task, timestamp 
                         FROM mood_logs''')
            
            # Drop old table and rename new one
            c.execute('DROP TABLE mood_logs')
            c.execute('ALTER TABLE mood_logs_new RENAME TO mood_logs')
            print("Database migration completed successfully!")
    else:
        # Create fresh table with all columns
        c.execute('''CREATE TABLE mood_logs
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      employee_id TEXT,
                      emotion TEXT,
                      burnout_score INTEGER,
                      recommended_task TEXT,
                      input_type TEXT DEFAULT 'text',
                      confidence REAL DEFAULT 0.85,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # Create employees table
    c.execute('''CREATE TABLE IF NOT EXISTS employees
                 (id TEXT PRIMARY KEY,
                  name TEXT,
                  department TEXT)''')
    
    # Create media_logs table
    c.execute('''CREATE TABLE IF NOT EXISTS media_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  employee_id TEXT,
                  media_type TEXT,
                  file_path TEXT,
                  emotion TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

def log_mood(employee_id, emotion, burnout_score, task, input_type='text', confidence=0.85):
    """Store mood data in database"""
    try:
        conn = sqlite3.connect('amdox.db')
        c = conn.cursor()
        c.execute('''INSERT INTO mood_logs (employee_id, emotion, burnout_score, recommended_task, input_type, confidence)
                     VALUES (?, ?, ?, ?, ?, ?)''', (employee_id, emotion, burnout_score, task, input_type, confidence))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error logging mood: {e}")
        return False

def log_media(employee_id, media_type, file_path, emotion):
    """Store media analysis logs"""
    try:
        conn = sqlite3.connect('amdox.db')
        c = conn.cursor()
        c.execute('''INSERT INTO media_logs (employee_id, media_type, file_path, emotion)
                     VALUES (?, ?, ?, ?)''', (employee_id, media_type, file_path, emotion))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error logging media: {e}")
        return False

def get_mood_history(employee_id, limit=10):
    """Retrieve mood history for an employee"""
    try:
        conn = sqlite3.connect('amdox.db')
        c = conn.cursor()
        c.execute('''SELECT emotion, burnout_score, recommended_task, timestamp, input_type, confidence
                     FROM mood_logs WHERE employee_id = ? 
                     ORDER BY timestamp DESC LIMIT ?''', (employee_id, limit))
        results = c.fetchall()
        conn.close()
        return results
    except Exception as e:
        print(f"Error getting mood history: {e}")
        return []

def get_team_analytics():
    """Get aggregated team mood data"""
    try:
        conn = sqlite3.connect('amdox.db')
        c = conn.cursor()
        c.execute('''SELECT employee_id, emotion, burnout_score, timestamp, input_type 
                     FROM mood_logs 
                     WHERE DATE(timestamp) >= DATE('now', '-7 days')
                     ORDER BY timestamp DESC''')
        results = c.fetchall()
        conn.close()
        return results
    except Exception as e:
        print(f"Error getting team analytics: {e}")
        return []

# ============================================
# AI EMOTION ANALYSIS ENGINE
# ============================================

class EmotionAnalyzer:
    """Multi-modal emotion detection"""
    
    EMOTION_KEYWORDS = {
        'motivated': ['motivated', 'energized', 'excited', 'enthusiastic', 'driven', 'inspired', 'pumped', 'ready'],
        'stressed': ['stressed', 'overwhelmed', 'anxious', 'pressure', 'worried', 'tense', 'nervous', 'panic'],
        'tired': ['tired', 'exhausted', 'fatigued', 'drained', 'sleepy', 'worn out', 'weary', 'depleted'],
        'frustrated': ['frustrated', 'annoyed', 'irritated', 'angry', 'upset', 'blocked', 'stuck', 'confused'],
        'happy': ['happy', 'joyful', 'content', 'pleased', 'satisfied', 'great', 'wonderful', 'delighted'],
        'sad': ['sad', 'down', 'depressed', 'unhappy', 'low', 'disappointed', 'gloomy', 'blue'],
        'neutral': ['okay', 'fine', 'normal', 'average', 'alright', 'calm', 'steady', 'balanced']
    }
    
    @staticmethod
    def detect_emotion_text(text):
        """Detect emotion from text input"""
        text_lower = text.lower()
        emotion_scores = {}
        
        for emotion, keywords in EmotionAnalyzer.EMOTION_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                emotion_scores[emotion] = score
        
        if emotion_scores:
            detected = max(emotion_scores, key=emotion_scores.get)
            confidence = min(emotion_scores[detected] * 0.25 + 0.60, 0.95)
            return detected, confidence
        return 'neutral', 0.70
    
    @staticmethod
    def detect_emotion_image(image_data):
        """Simulated facial emotion detection from image"""
        import random
        emotions = ['happy', 'sad', 'frustrated', 'neutral', 'stressed', 'motivated']
        detected = random.choice(emotions)
        confidence = random.uniform(0.78, 0.93)
        return detected, confidence
    
    @staticmethod
    def detect_emotion_video(video_path):
        """Simulated video emotion analysis"""
        import random
        emotions = ['stressed', 'tired', 'frustrated', 'neutral', 'happy', 'motivated']
        detected = random.choice(emotions)
        confidence = random.uniform(0.75, 0.90)
        return detected, confidence
    
    @staticmethod
    def detect_emotion_voice(audio_data):
        """Simulated voice emotion recognition"""
        import random
        emotions = ['happy', 'sad', 'stressed', 'neutral', 'frustrated', 'tired']
        detected = random.choice(emotions)
        confidence = random.uniform(0.72, 0.88)
        return detected, confidence

# ============================================
# TASK RECOMMENDATION ENGINE
# ============================================

class TaskRecommender:
    """AI-based task recommendation system"""
    
    TASK_DATABASE = {
        'motivated': [
            ('Strategic Planning Session', 'high', 'Plan next quarter goals and initiatives'),
            ('Complex Problem Solving', 'high', 'Tackle challenging technical issues'),
            ('Innovation Workshop', 'high', 'Brainstorm new product features'),
            ('Code Review & Optimization', 'medium', 'Review and improve code quality')
        ],
        'stressed': [
            ('Simple Bug Fixes', 'low', 'Fix minor UI bugs and issues'),
            ('Documentation Update', 'low', 'Update API documentation'),
            ('Team Check-in', 'low', 'Casual sync with team members'),
            ('Take a Wellness Break', 'rest', 'Go for a walk or meditation')
        ],
        'tired': [
            ('Code Documentation', 'low', 'Document recent work'),
            ('Email Management', 'low', 'Clear inbox and respond to emails'),
            ('Light Testing', 'low', 'Run automated test suites'),
            ('Rest Period', 'rest', 'Take a 15-minute power nap')
        ],
        'frustrated': [
            ('Pair Programming', 'medium', 'Work with colleague on blocker'),
            ('Switch Context', 'medium', 'Work on different project temporarily'),
            ('Seek Mentorship', 'low', 'Discuss challenges with senior team member'),
            ('Creative Break', 'rest', 'Step away and reset mindset')
        ],
        'happy': [
            ('Collaborative Work', 'medium', 'Team coding session or workshop'),
            ('Learning Session', 'medium', 'Study new technology or framework'),
            ('Mentoring Junior', 'medium', 'Help team member grow and learn'),
            ('Creative Task', 'high', 'Design new feature UI/UX')
        ],
        'sad': [
            ('Routine Tasks', 'low', 'Complete familiar comfortable work'),
            ('Connect with Team', 'low', 'Social interaction with colleagues'),
            ('Small Wins', 'low', 'Complete quick achievable tasks'),
            ('Self-care Break', 'rest', 'Talk to HR or take personal time')
        ],
        'neutral': [
            ('Regular Development', 'medium', 'Continue current sprint work'),
            ('Code Review', 'medium', 'Review team pull requests'),
            ('Meeting Participation', 'medium', 'Attend scheduled meetings'),
            ('Task Planning', 'medium', 'Organize upcoming work items')
        ]
    }
    
    @staticmethod
    def calculate_burnout_score(emotion, confidence=0.85):
        """Calculate burnout risk score (0-100)"""
        burnout_map = {
            'stressed': 85,
            'frustrated': 75,
            'tired': 70,
            'sad': 60,
            'neutral': 40,
            'happy': 20,
            'motivated': 10
        }
        base_score = burnout_map.get(emotion, 50)
        adjusted_score = int(base_score * confidence)
        return adjusted_score
    
    @staticmethod
    def recommend_task(emotion):
        """Get task recommendation based on emotion"""
        tasks = TaskRecommender.TASK_DATABASE.get(emotion, TaskRecommender.TASK_DATABASE['neutral'])
        return tasks[0]

# ============================================
# FILE UPLOAD HELPERS
# ============================================

ALLOWED_EXTENSIONS = {
    'image': {'png', 'jpg', 'jpeg', 'gif', 'bmp'},
    'video': {'mp4', 'avi', 'mov', 'wmv', 'mkv'},
    'audio': {'wav', 'mp3', 'ogg', 'm4a', 'webm'}
}

def allowed_file(filename, file_type):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS.get(file_type, set())

# ============================================
# FLASK ROUTES
# ============================================

@app.route('/')
def index():
    """Home page - multi-modal emotion input"""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze emotion and recommend task"""
    try:
        employee_id = request.form.get('employee_id', 'EMP001')
        mood_input = request.form.get('mood_input', '')
        
        if not mood_input:
            return "Please enter your mood description", 400
        
        analyzer = EmotionAnalyzer()
        detected_emotion, confidence = analyzer.detect_emotion_text(mood_input)
        
        recommender = TaskRecommender()
        burnout_score = recommender.calculate_burnout_score(detected_emotion, confidence)
        task_name, priority, description = recommender.recommend_task(detected_emotion)
        
        log_mood(employee_id, detected_emotion, burnout_score, task_name, 'text', confidence)
        
        result = {
            'employee_id': employee_id,
            'input_text': mood_input,
            'detected_emotion': detected_emotion,
            'burnout_score': burnout_score,
            'recommended_task': task_name,
            'task_priority': priority,
            'task_description': description,
            'alert_hr': burnout_score >= 70,
            'confidence': round(confidence * 100, 1),
            'input_type': 'Text Analysis'
        }
        
        return render_template('result.html', result=result)
    except Exception as e:
        return f"Error processing request: {str(e)}", 500

@app.route('/analyze-image', methods=['POST'])
def analyze_image():
    """Analyze emotion from uploaded image"""
    try:
        employee_id = request.form.get('employee_id', 'EMP001')
        
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename, 'image'):
            return jsonify({'error': 'Invalid file type. Please upload an image.'}), 400
        
        filename = secure_filename(f"{employee_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        analyzer = EmotionAnalyzer()
        detected_emotion, confidence = analyzer.detect_emotion_image(filepath)
        
        recommender = TaskRecommender()
        burnout_score = recommender.calculate_burnout_score(detected_emotion, confidence)
        task_name, priority, description = recommender.recommend_task(detected_emotion)
        
        log_mood(employee_id, detected_emotion, burnout_score, task_name, 'image', confidence)
        log_media(employee_id, 'image', filepath, detected_emotion)
        
        result = {
            'employee_id': employee_id,
            'input_text': 'Facial expression analysis from uploaded photo',
            'detected_emotion': detected_emotion,
            'burnout_score': burnout_score,
            'recommended_task': task_name,
            'task_priority': priority,
            'task_description': description,
            'alert_hr': burnout_score >= 70,
            'confidence': round(confidence * 100, 1),
            'input_type': 'Image Analysis'
        }
        
        return render_template('result.html', result=result)
    except Exception as e:
        return f"Error processing image: {str(e)}", 500

@app.route('/analyze-video', methods=['POST'])
def analyze_video():
    """Analyze emotion from uploaded video"""
    try:
        employee_id = request.form.get('employee_id', 'EMP001')
        
        if 'video' not in request.files:
            return jsonify({'error': 'No video uploaded'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename, 'video'):
            return jsonify({'error': 'Invalid file type. Please upload a video.'}), 400
        
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"{employee_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        analyzer = EmotionAnalyzer()
        detected_emotion, confidence = analyzer.detect_emotion_video(filepath)
        
        recommender = TaskRecommender()
        burnout_score = recommender.calculate_burnout_score(detected_emotion, confidence)
        task_name, priority, description = recommender.recommend_task(detected_emotion)
        
        log_mood(employee_id, detected_emotion, burnout_score, task_name, 'video', confidence)
        log_media(employee_id, 'video', filepath, detected_emotion)
        
        result = {
            'employee_id': employee_id,
            'input_text': 'Video facial expression analysis from uploaded clip',
            'detected_emotion': detected_emotion,
            'burnout_score': burnout_score,
            'recommended_task': task_name,
            'task_priority': priority,
            'task_description': description,
            'alert_hr': burnout_score >= 70,
            'confidence': round(confidence * 100, 1),
            'input_type': 'Video Analysis'
        }
        
        return render_template('result.html', result=result)
    except Exception as e:
        return f"Error processing video: {str(e)}", 500

@app.route('/analyze-voice', methods=['POST'])
def analyze_voice():
    """Analyze emotion from voice recording"""
    try:
        employee_id = request.form.get('employee_id', 'EMP001')
        
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio uploaded'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'wav'
        filename = secure_filename(f"{employee_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        analyzer = EmotionAnalyzer()
        detected_emotion, confidence = analyzer.detect_emotion_voice(filepath)
        
        recommender = TaskRecommender()
        burnout_score = recommender.calculate_burnout_score(detected_emotion, confidence)
        task_name, priority, description = recommender.recommend_task(detected_emotion)
        
        log_mood(employee_id, detected_emotion, burnout_score, task_name, 'voice', confidence)
        log_media(employee_id, 'audio', filepath, detected_emotion)
        
        result = {
            'employee_id': employee_id,
            'input_text': 'Voice prosody and tone analysis from audio recording',
            'detected_emotion': detected_emotion,
            'burnout_score': burnout_score,
            'recommended_task': task_name,
            'task_priority': priority,
            'task_description': description,
            'alert_hr': burnout_score >= 70,
            'confidence': round(confidence * 100, 1),
            'input_type': 'Voice Analysis'
        }
        
        return render_template('result.html', result=result)
    except Exception as e:
        return f"Error processing voice: {str(e)}", 500

@app.route('/history/<employee_id>')
def history(employee_id):
    """View mood history for employee"""
    try:
        mood_data = get_mood_history(employee_id, 20)
        return render_template('history.html', employee_id=employee_id, mood_data=mood_data)
    except Exception as e:
        return f"Error loading history: {str(e)}", 500

@app.route('/hr-dashboard')
def hr_dashboard():
    """HR Analytics Dashboard"""
    try:
        team_data = get_team_analytics()
        
        total_logs = len(team_data)
        
        emotions = [row[1] for row in team_data]
        emotion_counts = Counter(emotions)
        
        input_types = [row[4] for row in team_data] if team_data and len(team_data[0]) > 4 else []
        input_type_counts = Counter(input_types)
        
        high_burnout = [row for row in team_data if row[2] >= 70]
        
        analytics = {
            'total_logs': total_logs,
            'emotion_distribution': dict(emotion_counts),
            'input_type_distribution': dict(input_type_counts) if input_type_counts else {'text': 0},
            'high_burnout_count': len(high_burnout),
            'high_burnout_employees': high_burnout,
            'recent_logs': team_data[:10]
        }
        
        return render_template('hr_dashboard.html', analytics=analytics)
    except Exception as e:
        return f"Error loading dashboard: {str(e)}", 500

@app.route('/api/emotion', methods=['POST'])
def api_emotion():
    """API endpoint for emotion detection"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        analyzer = EmotionAnalyzer()
        emotion, confidence = analyzer.detect_emotion_text(text)
        
        recommender = TaskRecommender()
        burnout = recommender.calculate_burnout_score(emotion, confidence)
        
        return jsonify({
            'emotion': emotion,
            'burnout_score': burnout,
            'confidence': round(confidence * 100, 1),
            'status': 'success'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    return "Page not found", 404

@app.errorhandler(500)
def server_error(e):
    return f"Internal server error: {str(e)}", 500

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("=" * 60)
    print(" Amdox AI Task Optimizer Starting...")
    print("=" * 60)
    
    init_db()
    
    print("\n Server starting on http://localhost:5000")
    print(" Text Analysis: http://localhost:5000")
    print(" HR Dashboard: http://localhost:5000/hr-dashboard")
    print(" API Endpoint: http://localhost:5000/api/emotion")
    print("\n" + "=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)