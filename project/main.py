from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from .models import Meeting, User, MeetingPriority
from autogen import ConversableAgent, UserProxyAgent, GroupChat, GroupChatManager, AssistantAgent
from . import db

import os
from openai import OpenAI

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url="https://llm.mdb.ai",
)

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
    if meeting:
        meeting_priority = MeetingPriority.query.filter_by(meeting_id=meeting.id, user_id=current_user.id).first()
    meeting_priorities = MeetingPriority.query.filter_by(meeting_id=meeting.id).all()
    return render_template('meeting.html', meeting=meeting, users=users, meeting_priority=meeting_priority, meeting_priorities=meeting_priorities)

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

@main.route('/meeting/priority', methods=['POST'])
@login_required
def priority():
    meeting = Meeting.query.filter_by(id=request.form.get('meeting_id')).first()
    notes = request.form.get('notes')
    user = User.query.filter_by(email=current_user.email).first()
    meeting_priority = MeetingPriority.query.filter_by(meeting_id=meeting.id, user_id=user.id).first()
    if meeting_priority:
        meeting_priority.notes = notes
        db.session.merge(meeting_priority)
        db.session.commit()
        flash('Priority updated successfully!')
        return redirect(url_for('main.meeting', id=meeting.id))
    priority = MeetingPriority(meeting_id=meeting.id, user_id=user.id, notes=notes)
    db.session.add(priority)
    db.session.commit()
    flash('Priority added successfully!')
    return redirect(url_for('main.meeting', id=meeting.id))

@main.route('/meeting/complete', methods=['POST'])
@login_required
def complete():
    meeting = Meeting.query.filter_by(id=request.form.get('meeting_id')).first()
    meeting_priorities = MeetingPriority.query.filter_by(meeting_id=meeting.id).all()
    notes = "\n".join([f"{priority.notes}\n\n" for priority in meeting_priorities])
    """
    chat_completion = client.chat.completions.create(
        model="llama-3-70b",
        messages=[
            {"role": "user", "content": notes},
        ],
        stream=False,
    )
    chat_completion = chat_completion.choices[0].message.content
    """
    MODEL = "llama-3-70b"
    llm_config={"config_list": [{"base_url": "https://llm.mdb.ai", "model": MODEL, "api_key": os.environ.get("OPENAI_API_KEY"), "stream": False}]}
    agents = []
    facilitator_obj = User.query.filter_by(email=meeting.creator.email).first()
    assistant_agent = AssistantAgent(
        facilitator_obj.email,
        system_message=meeting.notes,
        llm_config=llm_config,
        code_execution_config=False,  # Turn off code execution, by default it is off.
        function_map=None,  # No registered functions, by default it is None.
        human_input_mode="NEVER",  # Never ask for human input.
    )
    agents.append(assistant_agent)
    for priority in meeting_priorities:
        agents.append(AssistantAgent(
            priority.user.email,
            system_message=priority.notes,
            llm_config=llm_config,
            code_execution_config=False,  # Turn off code execution, by default it is off.
            function_map=None,  # No registered functions, by default it is None.
            human_input_mode="NEVER",  # Never ask for human input.
        ))

    groupchat = GroupChat(agents=agents, messages=[], max_round=10, speaker_selection_method="round_robin")
    manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)
    chat_result = assistant_agent.initiate_chat(manager, message=meeting.notes)

    # reply = facilitator.initiate_chat(agents, message=meeting.notes, max_turns=2)

    # reply = agent.generate_reply(messages=[{"content": notes, "role": "user"}])
    return render_template('meeting_result.html', meeting=meeting, chat_completion="<br><br><br><br>".join(result["content"] for result in chat_result.chat_history))

@main.route('/meetings')
@login_required
def meetings():
    user = User.query.filter_by(email=current_user.email).first()
    return render_template('meetings.html', meetings=user.meetings)
