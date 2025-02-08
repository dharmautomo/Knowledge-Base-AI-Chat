# Checkpoint - February 07, 2025

## Database Schema

### User Table
- id (SERIAL PRIMARY KEY)
- username (VARCHAR(64), UNIQUE, NOT NULL)
- email (VARCHAR(120), UNIQUE, NOT NULL)
- created_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)

### ChatMessage Table
- id (SERIAL PRIMARY KEY)
- role (VARCHAR(20) NOT NULL)
- content (TEXT NOT NULL)
- timestamp (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- user_id (INTEGER REFERENCES user(id))

### File Table
- id (SERIAL PRIMARY KEY)
- filename (VARCHAR(255) NOT NULL)
- original_filename (VARCHAR(255) NOT NULL)
- uploaded_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- user_id (INTEGER REFERENCES user(id) NOT NULL)

## Working Features
1. Google OAuth Authentication
2. File Upload System
   - Supports PDF and TXT files
   - File processing with LangChain
3. Chat Interface
   - Message history per user
   - AI responses based on uploaded documents
4. Database Integration
   - User management
   - Chat history tracking
   - File management

## Environment Requirements
- Python packages installed and working
- PostgreSQL database configured
- Google OAuth credentials set up

This checkpoint represents a stable version with working:
- User authentication
- File uploads
- Chat functionality
- Database relations
