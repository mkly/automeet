from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
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
