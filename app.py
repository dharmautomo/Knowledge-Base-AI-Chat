import os
import logging
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from utils.openai_helper import process_message

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default_secret_key")

# Configure upload settings
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'txt'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# In-memory storage for chat history
chat_history = []

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    logger.debug("File upload request received")

    try:
        if 'file' not in request.files:
            logger.error("No file part in request")
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        if file.filename == '':
            logger.error("No selected file")
            return jsonify({'error': 'No selected file'}), 400

        if not file or not allowed_file(file.filename):
            logger.error(f"Invalid file type: {file.filename if file else 'None'}")
            return jsonify({'error': 'Invalid file type'}), 400

        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            logger.debug(f"Saving file to: {filepath}")

            file.save(filepath)
            logger.debug("File saved successfully")

            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.debug(f"File content read, length: {len(content)} characters")

            # Clean up the file after reading
            os.remove(filepath)
            logger.debug("Temporary file removed")

            return jsonify({'content': content})

        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500

    except Exception as e:
        logger.error(f"Unexpected error in upload: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message')

        if not message:
            logger.error("No message provided")
            return jsonify({'error': 'No message provided'}), 400

        # Add user message to history
        chat_history.append({'role': 'user', 'content': message})

        try:
            response = process_message(message, chat_history)
            chat_history.append({'role': 'assistant', 'content': response})

            return jsonify({
                'response': response,
                'history': chat_history
            })
        except Exception as e:
            logger.error(f"OpenAI processing error: {str(e)}")
            chat_history.pop()  # Remove the user message from history if processing failed
            return jsonify({'error': str(e)}), 500

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/history', methods=['GET'])
def get_history():
    return jsonify({'history': chat_history})