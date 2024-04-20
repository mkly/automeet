from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from .models import Meeting, User, meeting_invitations
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
    # get all users
    users = User.query.all()
    meeting = Meeting().query.filter_by(id=id).first()
    return render_template('meeting.html', meeting=meeting, users=users)

@main.route('/meeting', methods=['POST'])
@login_required
def meeting_post():
    title = request.form.get('title')
    notes = request.form.get('notes')
    id = request.form.get('id')
    if id:
        meeting = Meeting.query.filter_by(id=id).first()
        meeting.title = title
        meeting.notes = notes
        db.session.merge(meeting)
        db.session.commit()
        flash('Meeting updated successfully!')
        return redirect(url_for('main.meetings'))
    user = User.query.filter_by(email=current_user.email).first()
    user.created_meetings.append(Meeting(title=title, notes=notes))
    db.session.commit()
    flash('Meeting created successfully!')
    return redirect(url_for('main.meetings'))

@main.route('/meeting/invite', methods=['POST'])
@login_required
def invite():
    meeting = Meeting.query.filter_by(id=request.form.get('meeting_id')).first()
    for user_id in request.form.getlist('users[]'):
        user = User.query.filter_by(id=user_id).first()
        meeting.invited_users.append(user)
    db.session.merge(meeting)
    db.session.commit()
    flash('Users invited successfully!')
    return redirect(url_for('main.meeting', id=meeting.id))

@main.route('/meetings')
@login_required
def meetings():
    user = User.query.filter_by(email=current_user.email).first()
    return render_template('meetings.html', meetings=user.meetings)
