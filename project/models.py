from flask_login import UserMixin
from . import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    created_meetings = db.relationship('Meeting', backref='creator', lazy=True)
    meetings = db.relationship('Meeting', secondary='meeting_invitations')

class Meeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.Text)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    invited_users = db.relationship('User', secondary='meeting_invitations')

meeting_invitations = db.Table('meeting_invitations',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('meeting_id', db.Integer, db.ForeignKey('meeting.id'), primary_key=True)
)

class MeetingPriority(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey('meeting.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='meeting_priorities')
    notes = db.Column(db.Text)
    priority = db.Column(db.String(100), nullable=True)
    embeddings_index = db.Column(db.Text, nullable=True)
    file_name_list = db.Column(db.Text, nullable=True)
