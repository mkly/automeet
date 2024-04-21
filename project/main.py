from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from .models import Meeting, User, MeetingPriority
from autogen import ConversableAgent, UserProxyAgent, GroupChat, GroupChatManager, AssistantAgent, Agent
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage

from llama_index.core.retrievers import VectorIndexRetriever
from typing import Optional, Dict, List, Any, Union
import json
from . import db

import os
from openai import OpenAI
import agentops
import html2text

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("MDB_OPENAI_API_KEY"),
    base_url="https://llm.mdb.ai",
)

agentops.init(os.environ.get("AGENTOPS_API_KEY"))

main = Blueprint('main', __name__)

DANGER_COLOR = "pico-background-red-500"
SUCCESS_COLOR = "pico-background-green-500"

NO_PRIORITY_PROMPT = "I have no opinion on this"
PRIORITY_PROMPT = {
    "LOW": "I do not feel strongly about this",
    "MEDIUM": "I feel somewhat strongly about this",
    "HIGH": "I feel very strongly about this",
}

class RagAssistantAgent(ConversableAgent):
    def generate_reply(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        sender: Optional["Agent"] = None,
        **kwargs: Any,
    ) -> Union[str, Dict, None]:
        if messages is None:
            messages = self._oai_messages[sender]

        meeting = Meeting.query.filter_by(id=request.form.get('meeting_id')).first()
        if not meeting:
            return super().generate_reply(messages, sender, **kwargs)
        user = User.query.filter_by(email=self.name).first()
        if not user:
            return super().generate_reply(messages, sender, **kwargs)
        meeting_priority = MeetingPriority.query.filter_by(meeting_id=meeting.id, user_id=user.id).first()
        if not meeting_priority:
            return super().generate_reply(messages, sender, **kwargs)
        if not messages:
            return super().generate_reply(messages, sender, **kwargs)
        search_val = "\n\n".join([m["content"] for m in messages[-3:]])
        index = None
        storage_context = None
        if meeting_priority.embeddings_index:
            storage_context = StorageContext.from_dict(json.loads(meeting_priority.embeddings_index))
        if storage_context:
            index = load_index_from_storage(storage_context)
        else:
            return super().generate_reply(messages, sender, **kwargs)
        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=10,
        )
        results = retriever.retrieve(search_val)
        rag = []
        results = sorted(results, key=lambda x: x.score, reverse=True)
        for result in results:
            if result.score and result.score > 0.75:
                rag.append(result.get_text()[:500])
        messages[-1]["content"] = " ".join((messages[-1]["content"] + "\n\n### Additional context that you already know:\n\n" + "\n".join(rag)).split(" "))
        # Truncate all messages to 3000 tokens
        for message in messages:
            message["content"] = " ".join(message["content"].split(" ")[:1000])
        # Remove older messages from the list until the sum of all the 'content' properties total less than 4096 tokens
        while sum([len(m["content"].split(" ")) for m in messages]) > 3000:
            print(sum([len(m["content"].split(" ")) for m in messages]))
            messages.pop(0)
            print("Popping message")

        return super().generate_reply(messages, sender, **kwargs)


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
    flash('Your name has been updated!', SUCCESS_COLOR)
    return redirect(url_for('main.profile'))

@main.route('/meeting/<id>', methods=['GET'])
@main.route('/meeting', methods=['GET'])
@login_required
def meeting(id=None):
    users = User.query.all()
    meeting = Meeting().query.filter_by(id=id).first()
    file_names = []
    if meeting:
        meeting_priority = MeetingPriority.query.filter_by(meeting_id=meeting.id, user_id=current_user.id).first()
        file_names = json.loads(meeting_priority.file_name_list) if meeting_priority and meeting_priority.file_name_list else []
        meeting_priorities = MeetingPriority.query.filter_by(meeting_id=meeting.id).all()
        for i, mp in enumerate(meeting_priorities):
            meeting_priorities[i].file_names = json.loads(mp.file_name_list) if mp.file_name_list else []
    else:
        meeting_priority = MeetingPriority()
        meeting_priorities = []
    invited_user_ids = []
    if meeting:
        invited_user_ids = [user.id for user in meeting.invited_users]
        invited_user_ids.append(meeting.creator_id)
    return render_template('meeting.html', meeting=meeting, users=users, meeting_priority=meeting_priority, meeting_priorities=meeting_priorities, file_names=file_names, invited_user_ids=invited_user_ids)

@main.route('/meeting', methods=['POST'])
@login_required
def meeting_post():
    title = request.form.get('title')
    notes = request.form.get('notes')
    id = request.form.get('id')
    if not title or not notes:
        flash('Please enter title and notes!', DANGER_COLOR)
        global meeting
        return meeting(None)
    if id:
        meeting = Meeting.query.filter_by(id=id).first()
        meeting.title = title
        meeting.notes = notes
        db.session.merge(meeting)
        db.session.commit()
        flash('Meeting updated successfully!', SUCCESS_COLOR)
        return redirect(url_for('main.meetings'))
    user = User.query.filter_by(email=current_user.email).first()
    user.created_meetings.append(Meeting(title=title, notes=notes))
    db.session.commit()
    flash('Meeting created successfully!', SUCCESS_COLOR)
    return redirect(url_for('main.meetings'))

@main.route('/meeting/invite', methods=['POST'])
@login_required
def invite():
    meeting = Meeting.query.filter_by(id=request.form.get('meeting_id')).first()
    for user_id in request.form.getlist('users[]'):
        user = User.query.filter_by(id=user_id).first()
        if not user:
            continue
        if user.id in [u.id for u in meeting.invited_users]:
            continue
        meeting.invited_users.append(user)
    db.session.merge(meeting)
    db.session.commit()
    flash('Users invited successfully!', SUCCESS_COLOR)
    return redirect(url_for('main.meeting', id=meeting.id))

@main.route('/meeting/priority', methods=['POST'])
@login_required
def priority():
    meeting = Meeting.query.filter_by(id=request.form.get('meeting_id')).first()
    notes = request.form.get('notes')
    priority = request.form.get('priority')
    user = User.query.filter_by(email=current_user.email).first()
    meeting_priority = MeetingPriority.query.filter_by(meeting_id=meeting.id, user_id=user.id).first()
    if meeting_priority:
        meeting_priority.notes = notes
        meeting_priority.priority = priority
        db.session.merge(meeting_priority)
        db.session.commit()
        flash('Priority updated successfully!', SUCCESS_COLOR)
        return redirect(url_for('main.meeting', id=meeting.id))
    priority = MeetingPriority(meeting_id=meeting.id, user_id=user.id, notes=notes, priority=priority)
    db.session.add(priority)
    db.session.commit()
    flash('Priority added successfully!', SUCCESS_COLOR)
    return redirect(url_for('main.meeting', id=meeting.id))

@main.route('/meeting/priority/fileupload', methods=['POST'])
@login_required
def priority_fileupload():
    meeting = Meeting.query.filter_by(id=request.form.get('meeting_id')).first()
    meeting_priority = MeetingPriority.query.filter_by(meeting_id=meeting.id, user_id=current_user.id).first()
    file = request.files['file']
    if not file:
        flash('Please select a file to upload!', DANGER_COLOR)
        return redirect(url_for('main.meeting', id=meeting.id))

    tmp_dir = f"tmp/{meeting_priority.meeting_id}_{meeting_priority.user_id}"
    # create temporary directory
    os.makedirs(tmp_dir, exist_ok=True)
    file.save(f"{tmp_dir}/{file.filename}")
    #if html file, convert to get_text
    if file.filename.endswith('.html'):
        with open(f"{tmp_dir}/{file.filename}", 'r') as f:
            html = f.read()
        text = html2text.html2text(html)
        with open(f"{tmp_dir}/{file.filename}", 'w') as f:
            f.write(text)
    index = None
    storage_context = None
    if meeting_priority.embeddings_index:
        storage_context = StorageContext.from_dict(json.loads(meeting_priority.embeddings_index))

    documents = SimpleDirectoryReader(tmp_dir).load_data()
    os.unlink(f"{tmp_dir}/{file.filename}")
    if storage_context:
        index = load_index_from_storage(storage_context)
        index.insert(document=documents[0])
    else:
        index = VectorStoreIndex.from_documents(documents)
    result = json.dumps(index.storage_context.to_dict())
    meeting_priority.embeddings_index = result
    try:
        file_list = [] if not meeting_priority.file_name_list else json.loads(meeting_priority.file_name_list)
    except:
        file_list = []
    file_list.append(file.filename)
    meeting_priority.file_name_list = json.dumps(file_list)
    db.session.merge(meeting_priority)
    db.session.commit()
    flash('File uploaded and indexed successfully!', SUCCESS_COLOR)
    return redirect(url_for('main.meeting', id=meeting.id))
    


@main.route('/meeting/complete', methods=['POST'])
@login_required
def complete():
    meeting = Meeting.query.filter_by(id=request.form.get('meeting_id')).first()
    meeting_priorities = MeetingPriority.query.filter_by(meeting_id=meeting.id).all()
    MODEL = "llama-3-8b"
    MODEL = "llama-3-70b"
    llm_config={"config_list": [{"base_url": "https://llm.mdb.ai", "model": MODEL, "api_key": os.environ.get("MDB_OPENAI_API_KEY"), "stream": False}]}
    agents = []
    facilitator_obj = User.query.filter_by(email=meeting.creator.email).first()
    assistant_agent = AssistantAgent(
        facilitator_obj.email,
        system_message=f"You are facilitating a meeting with your coworkers.\n\nYou should provide a response and a brief outline to keep everyone on track.\n\nDO NOT CREATE FAKE NAMES\n\n### TITLE:{meeting.title}\n\n{meeting.notes}",
        llm_config=llm_config,
        code_execution_config=False,  # Turn off code execution, by default it is off.
        function_map=None,  # No registered functions, by default it is None.
        human_input_mode="NEVER",  # Never ask for human input.
    )
    agents.append(assistant_agent)
    for priority in meeting_priorities:
        meeting_agent = RagAssistantAgent(
            name=priority.user.email,
            system_message=f"You are in a meeting with team members from you organization. You deeply want to stay on task and push for your priorities. {PRIORITY_PROMPT[priority.priority] if priority.priority else NO_PRIORITY_PROMPT}:\n\nYOUR PRIORITIES: {priority.notes}",
            llm_config=llm_config,
            code_execution_config=False,  # Turn off code execution, by default it is off.
            function_map=None,  # No registered functions, by default it is None.
            human_input_mode="NEVER",  # Never ask for human input.
        )
        agents.append(meeting_agent)

    groupchat = GroupChat(agents=agents, messages=[], max_round=len(agents) * 3, speaker_selection_method="random")
    manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)
    chat_result = assistant_agent.initiate_chat(manager, message=meeting.notes)
    conversation = "\n".join([f"### {message['role']}:\n\n{message['content']}\n\n" for message in chat_result.chat_history])
    summary = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a summarization tool. You are not a person or assistant. Briefly summarize the meeting. YOU MUST PROVIDE A SUMMARY AND ONLY A SUMMARY"},
            {"role": "user", "content": conversation},
        ],
        stream=False,
    )
    print('************')
    print(summary.choices[0].message.content)
    action_items = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "Create a list of one or two sentence actions items from the meeting. ONLY PROVIDE THE LIST"},
            {"role": "user", "content": conversation},
        ],
        stream=False,
    )
    print('000000000000')
    print(action_items.choices[0].message.content)
    print('************')

    return render_template('meeting_result.html', meeting=meeting, chat_results=chat_result.chat_history, summary=summary.choices[0].message.content, action_items=action_items.choices[0].message.content)

@main.route('/meetings')
@login_required
def meetings():
    user = User.query.filter_by(email=current_user.email).first()
    invite_meetings = Meeting.query.filter(Meeting.invited_users.any(id=user.id)).all()
    return render_template('meetings.html', meetings=user.created_meetings, invite_meetings=invite_meetings)
