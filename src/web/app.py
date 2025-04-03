from flask import Flask, render_template, jsonify, send_from_directory
import os
from src.core.file_tracker import file_tracker

app = Flask(__name__,
            static_url_path='/static',
            static_folder='static',
            template_folder='templates')

# Register an additional static folder for media files
# This is a cleaner approach than creating a custom route handler
app.config['MEDIA_FOLDER'] = os.path.abspath('')

print(file_tracker.get_latest_files())

@app.route('/')
def index():
    """Render the main visualization page."""
    return render_template('index.html')

@app.route('/fCase')
def index_fCase():
    """Render the main visualization page."""
    return render_template('index_fCase.html')

@app.route('/fBox')
def index_fBox():
    """Render the main visualization page."""
    return render_template('index_fBox.html')

@app.route('/fCover')
def index_fCover():
    """Render the main visualization page."""
    return render_template('index_fCover.html')

@app.route('/fFinal')
def inde_fFinal():
    """Render the main visualization page."""
    return render_template('index_fFinal.html')

@app.route('/api/last_files')
def get_last_files():
    """Get the most recent files for all task types."""
    return jsonify(file_tracker.get_latest_files())

@app.route('/api/all_files')
def get_all_files():
    """Get all tracked files for all task types."""
    return jsonify(file_tracker.get_files())

@app.route('/api/files/<task_type>')
def get_task_files(task_type):
    """Get tracked files for a specific task type."""
    return jsonify(file_tracker.get_files(task_type))

# Simplified media serving using send_from_directory
@app.route('/media/<path:file_path>')
def serve_media(file_path):
    """Serve media files (images and videos) from the media folder."""
    return send_from_directory(app.config['MEDIA_FOLDER'], file_path)

# # Uncomment to run the app
# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=8080, debug=True)