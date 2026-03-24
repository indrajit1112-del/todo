import streamlit as st
import database as db
import llm
from datetime import datetime
from streamlit_calendar import calendar

st.set_page_config(page_title="Inbox - AI Task Manager", layout="wide", page_icon="✅")

# Inject Custom Premium CSS
st.markdown("""
<style>
    /* Premium Look Elements */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .task-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 12px;
        transition: transform 0.2s, background 0.2s;
    }
    .task-card:hover {
        transform: translateY(-2px);
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .task-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 4px;
        color: #FFFFFF;
    }
    .task-meta {
        font-size: 0.85rem;
        color: #A0AEC0;
        margin-bottom: 8px;
    }
    .task-tag {
        display: inline-block;
        background: #3182CE;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 6px;
    }
    .subtask {
        margin-left: 20px;
        border-left: 2px solid #4A5568;
        padding-left: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- State Management ---
if 'db_inited' not in st.session_state:
    db.init_db()
    st.session_state.db_inited = True
if 'current_project' not in st.session_state:
    st.session_state.current_project = 1 # inbox
if 'clarification_pending' not in st.session_state:
    st.session_state.clarification_pending = None

# --- Sidebar ---
with st.sidebar:
    st.title("🎯 Projects")
    projects = db.get_projects()
    
    for p in projects:
        if st.button(f"📁 {p['name'].capitalize()}", key=f"proj_{p['id']}", use_container_width=True):
            st.session_state.current_project = p['id']
            st.rerun()
            
    st.divider()
    new_proj = st.text_input("New Project Name")
    if st.button("Create Project", use_container_width=True) and new_proj:
        db.add_project(new_proj)
        st.session_state.current_project = db.get_projects()[-1]['id']
        st.rerun()

current_proj_name = next((p['name'] for p in projects if p['id'] == st.session_state.current_project), "Unknown")
st.title(f"📂 {current_proj_name.capitalize()}")

# --- Add Task Area ---
with st.container():
    if st.session_state.clarification_pending:
        pending = st.session_state.clarification_pending
        st.warning(f"🤔 The AI is unsure about: '{pending['original_input']}'")
        st.info(f"Question: {pending['question']}")
        
        rule_input = st.text_input("Help me understand! (Provide a rule or context for next time):")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Save Rule & Retry", type="primary"):
                if rule_input:
                    db.add_memory_rule(rule_input)
                st.session_state.clarification_pending = None
                st.rerun()
        with col2:
            if st.button("Cancel"):
                st.session_state.clarification_pending = None
                st.rerun()
    else:
        st.markdown("### ✨ New Task")
        with st.form("new_task_form", clear_on_submit=True):
            task_input = st.text_input("What needs to be done?", placeholder="e.g. Buy groceries tomorrow")
            submit_task = st.form_submit_button("Add Task")
            
            if submit_task and task_input:
                with st.spinner("AI is analyzing your task..."):
                    try:
                        parsed = llm.parse_task(task_input)
                        
                        if parsed.get('needs_clarification'):
                            st.session_state.clarification_pending = {
                                "original_input": task_input,
                                "question": parsed.get('clarification_question', "What do you mean?")
                            }
                            st.rerun()
                        else:
                            # Standard insertion
                            title = parsed.get('title', task_input)
                            desc = parsed.get('description', '')
                            task_type = parsed.get('task_type', '')
                            due_date = parsed.get('due_date', None)
                            tags = parsed.get('tags', [])
                            
                            t_id = db.add_task(
                                title=title,
                                project_id=st.session_state.current_project,
                                description=desc,
                                due_date=due_date,
                                task_type=task_type
                            )
                            for t in tags:
                                db.add_tag_to_task(t_id, t)
                            st.success(f"Added task: {title}")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error parsing task: {e}")

st.divider()

# --- Main Views ---
tab1, tab2 = st.tabs(["📝 List View", "📅 Calendar View"])

# Fetch Tasks for current project
tasks = db.get_tasks(project_id=st.session_state.current_project)
main_tasks = [t for t in tasks if not t['parent_id']]
subtasks = {t['parent_id']: [] for t in tasks if t['parent_id']}
for t in tasks:
    if t['parent_id']:
        subtasks[t['parent_id']].append(t)

with tab1:
    if not main_tasks:
        st.info("No tasks here yet. Add some above!")
    
    for t in main_tasks:
        st.markdown(f"<div class='task-card'>", unsafe_allow_html=True)
        col1, col2 = st.columns([0.05, 0.95])
        with col1:
            if st.checkbox("DONE", key=f"done_{t['id']}", label_visibility="hidden"):
                db.update_task(t['id'], completed=True)
                st.rerun()
        with col2:
            st.markdown(f"<div class='task-title'>{t['title']}</div>", unsafe_allow_html=True)
            meta = []
            if t['due_date']: meta.append(f"📅 {t['due_date']}")
            if t['task_type']: meta.append(f"🏷️ {t['task_type']}")
            st.markdown(f"<div class='task-meta'>{' | '.join(meta)}</div>", unsafe_allow_html=True)
            
            tags_html = "".join([f"<span class='task-tag'>{tag}</span>" for tag in t['tags']])
            if tags_html: st.markdown(tags_html, unsafe_allow_html=True)
            
            if t['description']:
                st.markdown(f"<p style='font-size:0.9rem; color:#CBD5E0; margin-top:8px;'>{t['description']}</p>", unsafe_allow_html=True)
                
            # Expandable Editor & Subtasks
            with st.expander("Edit / Subtasks"):
                edit_col1, edit_col2 = st.columns(2)
                with edit_col1:
                    new_title = st.text_input("Title", value=t['title'], key=f"title_{t['id']}")
                    new_desc = st.text_area("Notes/Description", value=t['notes'] or t['description'] or "", key=f"desc_{t['id']}")
                with edit_col2:
                    new_date = st.text_input("Due Date (YYYY-MM-DD)", value=t['due_date'] or "", key=f"date_{t['id']}")
                    new_project = st.selectbox("Project", [p['name'] for p in projects], index=[p['id'] for p in projects].index(t['project_id']), key=f"proj_sel_{t['id']}")
                
                if st.button("Save Changes", key=f"save_{t['id']}"):
                    new_proj_id = next(p['id'] for p in projects if p['name'] == new_project)
                    db.update_task(t['id'], title=new_title, description=new_desc, due_date=new_date, project_id=new_proj_id)
                    st.rerun()
                
                st.markdown("**Subtasks**")
                for sub in subtasks.get(t['id'], []):
                    scol1, scol2, scol3 = st.columns([0.1, 0.7, 0.2])
                    with scol1:
                        if st.checkbox("done", key=f"sdone_{sub['id']}", label_visibility="hidden"):
                            db.update_task(sub['id'], completed=True)
                            st.rerun()
                    with scol2:
                        st.write(sub['title'])
                    with scol3:
                        if st.button("Make Main", key=f"main_{sub['id']}", help="Convert to main task"):
                            db.update_task(sub['id'], parent_id=None)
                            st.rerun()
                            
                new_sub = st.text_input("Add Subtask", key=f"new_sub_{t['id']}")
                if st.button("Add Subtask", key=f"add_sub_{t['id']}") and new_sub:
                    db.add_task(title=new_sub, project_id=t['project_id'], parent_id=t['id'])
                    st.rerun()
                    
                if st.button("Delete Task", key=f"del_{t['id']}", type="primary"):
                    db.delete_task(t['id'])
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    calendar_events = []
    
    for t in tasks:
        if t['due_date']:
            # Assign color based on task type or project
            bg_color = "#3182CE" if not t['parent_id'] else "#4A5568"
            calendar_events.append({
                "title": t['title'],
                "start": t['due_date'],
                "backgroundColor": bg_color,
                "borderColor": bg_color,
            })
            
    calendar_options = {
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek"
        },
        "initialView": "dayGridMonth",
    }
    
    if len(calendar_events) > 0:
        calendar(events=calendar_events, options=calendar_options)
    else:
        st.info("No tasks with due dates to show on the calendar.")
