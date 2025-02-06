from datetime import datetime
from app import db

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat()
        }
