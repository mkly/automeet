from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from .models import Meeting, User
from . import db

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@main.route('/profile', methods=['POST'])
@login_required
def profile_post():
    current_user.name = request.form.get('name')
    db.session.merge(current_user)
    db.session.commit()
    flash('Your name has been updated!')
    return redirect(url_for('main.profile'))

@main.route('/meeting/<id>', methods=['GET'])
@main.route('/meeting', methods=['GET'])
@login_required
def meeting(id=None):
    meeting = Meeting().query.filter_by(id=id).first()
    return render_template('meeting.html', meeting=meeting)

@main.route('/meeting', methods=['POST'])
@login_required
def meeting_post():
    title = request.form.get('title')
    notes = request.form.get('notes')
    user = User.query.filter_by(email=current_user.email).first()
    user.created_meetings.append(Meeting(title=title, notes=notes))
    db.session.commit()
    flash('Meeting created successfully!')
    return redirect(url_for('main.meetings'))

@main.route('/meetings')
@login_required
def meetings():
    user = User.query.filter_by(email=current_user.email).first()
    return render_template('meetings.html', meetings=user.meetings)
