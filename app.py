import os
import logging
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from utils.openai_helper import process_message, process_document
from datetime import datetime
from utils.text_processor import TextProcessor

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask and SQLAlchemy
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default_secret_key")

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Configure upload settings
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'txt', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize TextProcessor
text_processor = TextProcessor()

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat()
        }


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

            # Process based on file type
            if filename.lower().endswith('.pdf'):
                content = text_processor.extract_text_from_pdf(filepath)
            else:  # .txt files
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

            logger.debug(f"File content read, length: {len(content)} characters")

            # Process the document content
            num_chunks = process_document(content)
            logger.debug(f"Document processed into {num_chunks} chunks")

            # Clean up the file after reading
            os.remove(filepath)
            logger.debug("Temporary file removed")

            return jsonify({'message': 'File processed successfully'})

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

        # Create and save user message
        user_message = ChatMessage(role='user', content=message)
        db.session.add(user_message)
        db.session.commit()

        try:
            # Get recent chat history from database
            chat_history = [msg.to_dict() for msg in 
                          ChatMessage.query.order_by(ChatMessage.timestamp.desc()).limit(10).all()]
            chat_history.reverse()  # Most recent last

            response = process_message(message, chat_history)

            # Save assistant's response
            assistant_message = ChatMessage(role='assistant', content=response)
            db.session.add(assistant_message)
            db.session.commit()

            return jsonify({
                'response': response,
                'history': [msg.to_dict() for msg in 
                           ChatMessage.query.order_by(ChatMessage.timestamp).all()]
            })

        except Exception as e:
            logger.error(f"OpenAI processing error: {str(e)}")
            db.session.rollback()  # Rollback the user message on error
            return jsonify({'error': str(e)}), 500

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/history', methods=['GET'])
def get_history():
    messages = ChatMessage.query.order_by(ChatMessage.timestamp).all()
    return jsonify({'history': [msg.to_dict() for msg in messages]})

@app.route('/reset', methods=['POST'])
def reset_chat():
    try:
        # Clear all chat messages
        db.session.query(ChatMessage).delete()
        db.session.commit()
        logger.debug("Chat history cleared successfully")

        # Return success response with empty history
        return jsonify({
            'message': 'Chat reset successful',
            'history': []
        }), 200
    except Exception as e:
        logger.error(f"Error resetting chat: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Create database tables
with app.app_context():
    db.create_all()