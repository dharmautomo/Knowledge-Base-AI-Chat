import os
import logging
import uuid
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_login import LoginManager, login_required, current_user
from werkzeug.utils import secure_filename
from utils.openai_helper import process_message, process_document
from datetime import datetime, timedelta
from utils.text_processor import TextProcessor
from extensions import db

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default_secret_key")
app.permanent_session_lifetime = timedelta(days=5)

# Database configuration with proper SSL and connection pooling
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,  # Enable connection health checks
    'pool_recycle': 300,    # Recycle connections every 5 minutes
    'pool_timeout': 30,     # Connection timeout of 30 seconds
    'pool_size': 10,        # Maximum pool size
    'max_overflow': 5,      # Maximum number of connections above pool_size
    'connect_args': {
        'sslmode': 'require',  # Force SSL mode
        'connect_timeout': 10   # Connection attempt timeout
    }
}

db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configure upload settings
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'txt', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize TextProcessor
text_processor = TextProcessor()

# Import models after db initialization
from models import User, ChatMessage, File
from google_auth import google_auth

# Register Google Auth blueprint
app.register_blueprint(google_auth)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Custom unauthorized handler
@login_manager.unauthorized_handler
def unauthorized():
    logger.debug("Unauthorized access attempt")
    return redirect(url_for('login'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/login')
def login():
    if current_user.is_authenticated:
        logger.debug(f"Already authenticated user {current_user.id} accessing login page")
        return redirect(url_for('index'))
    logger.debug("Rendering login page for unauthenticated user")
    return render_template('login.html')

@app.route('/')
@login_required
def index():
    logger.debug(f"User {current_user.id} accessing index page")
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    logger.debug("File upload request received")
    filepath = None

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
            # Generate unique filename
            original_filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{original_filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            logger.debug(f"Saving file to: {filepath}")

            file.save(filepath)
            logger.debug("File saved successfully")

            # Create file record in database
            file_record = File(
                filename=unique_filename,
                original_filename=original_filename,
                user_id=current_user.id
            )
            db.session.add(file_record)
            db.session.commit()

            # Process based on file type
            if original_filename.lower().endswith('.pdf'):
                content = text_processor.extract_text_from_pdf(filepath)
            else:  # .txt files
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

            logger.debug(f"File content read, length: {len(content)} characters")

            # Process the document content
            num_chunks = process_document(content)
            logger.debug(f"Document processed into {num_chunks} chunks")

            return jsonify({
                'message': 'File processed successfully',
                'file': file_record.to_dict()
            })

        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            db.session.rollback()
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500

    except Exception as e:
        logger.error(f"Unexpected error in upload: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/files', methods=['GET'])
@login_required
def get_files():
    try:
        files = File.query.filter_by(user_id=current_user.id).order_by(File.uploaded_at.desc()).all()
        return jsonify({'files': [file.to_dict() for file in files]})
    except Exception as e:
        logger.error(f"Error retrieving files: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/files/<int:file_id>', methods=['DELETE'])
@login_required
def delete_file(file_id):
    try:
        file = File.query.filter_by(id=file_id, user_id=current_user.id).first()

        if not file:
            return jsonify({'error': 'File not found or unauthorized'}), 404

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        if os.path.exists(filepath):
            os.remove(filepath)

        db.session.delete(file)
        db.session.commit()

        return jsonify({'message': 'File deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    try:
        data = request.json
        message = data.get('message')

        if not message:
            logger.error("No message provided")
            return jsonify({'error': 'No message provided'}), 400

        # Create and save user message with user_id
        user_message = ChatMessage(role='user', content=message, user_id=current_user.id)
        db.session.add(user_message)
        db.session.commit()

        try:
            # Get recent chat history from database for current user
            chat_history = [msg.to_dict() for msg in 
                          ChatMessage.query.filter_by(user_id=current_user.id)
                          .order_by(ChatMessage.timestamp.desc()).limit(10).all()]
            chat_history.reverse()  # Most recent last

            response = process_message(message, chat_history)

            # Save assistant's response with user_id
            assistant_message = ChatMessage(role='assistant', content=response, user_id=current_user.id)
            db.session.add(assistant_message)
            db.session.commit()

            return jsonify({
                'response': response,
                'history': [msg.to_dict() for msg in 
                           ChatMessage.query.filter_by(user_id=current_user.id)
                           .order_by(ChatMessage.timestamp).all()]
            })

        except Exception as e:
            logger.error(f"OpenAI processing error: {str(e)}")
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/history', methods=['GET'])
@login_required
def get_history():
    messages = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.timestamp).all()
    return jsonify({'history': [msg.to_dict() for msg in messages]})

@app.route('/reset', methods=['POST'])
@login_required
def reset_chat():
    try:
        # Clear chat messages for current user only
        ChatMessage.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        logger.debug("Chat history cleared successfully")

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