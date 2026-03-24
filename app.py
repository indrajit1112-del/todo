import streamlit as st
import database as db
import llm
from datetime import datetime

st.set_page_config(page_title="To Do", layout="wide", page_icon="✔️")

# Inject Custom MS To Do CSS
st.markdown("""
<style>
    /* Global Colors and Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    .stApp {
        background-color: #FAF9F8;
    }
    
    /* Hide Streamlit Header & default padding */
    header {visibility: hidden;}
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        max-width: 100%;
    }
    
    /* Custom Top Bar */
    .top-bar {
        background-color: #2564CF;
        color: white;
        padding: 12px 20px;
        font-size: 16px;
        font-weight: 600;
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 999999;
        display: flex;
        align-items: center;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #F3F2F1;
        border-right: none;
    }
    
    /* MS To Do Task Row Styling applying to container */
    .task-container {
        background-color: #FFFFFF;
        border: 1px solid #EDEBE9;
        border-radius: 4px;
        padding: 5px 15px;
        margin-bottom: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: background 0.2s;
    }
    .task-container:hover {
        background-color: #F3F2F1;
    }
    
    .task-title {
        font-size: 14px;
        color: #201F1E;
        margin: 0;
        padding: 0;
        font-weight: 400;
    }
    .task-meta {
        font-size: 12px;
        color: #605E5C;
        margin-top: 2px;
    }
    
    /* Add Task Bar */
    .add-task-bar {
        background-color: #FFFFFF;
        border: 1px solid #EDEBE9;
        border-radius: 4px;
        padding: 10px 15px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }
    
    /* Customizing Streamlit Inputs to look cleaner */
    .stTextInput>div>div>input {
        background: transparent;
        border: none;
        color: #201F1E;
        box-shadow: none;
    }
    .stTextInput>div>div>input:focus {
        border-bottom: 1px solid #2564CF;
        box-shadow: none;
    }
    
    /* Sidebar buttons */
    .stButton>button {
        width: 100%;
        text-align: left;
        border: none;
        background: transparent;
        color: #201F1E;
        padding: 8px 12px;
        border-radius: 4px;
        justify-content: flex-start;
    }
    .stButton>button:hover {
        background-color: #EDEBE9;
        color: #201F1E;
    }
    .stButton>button:focus {
        color: #2564CF;
        background-color: white;
        box-shadow: none;
    }
</style>
<div class="top-bar">✅ To Do</div>
""", unsafe_allow_html=True)

# --- State Management ---
if 'db_inited' not in st.session_state:
    db.init_db()
    st.session_state.db_inited = True
if 'current_project' not in st.session_state:
    st.session_state.current_project = "My Day" # Using string for smart lists, int for db projects
if 'clarification_pending' not in st.session_state:
    st.session_state.clarification_pending = None

# --- Sidebar ---
with st.sidebar:
    st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
    
    # Smart Lists
    if st.button("☀️ My Day"): st.session_state.current_project = "My Day"
    if st.button("⭐ Important"): st.session_state.current_project = "Important"
    if st.button("📅 Planned"): st.session_state.current_project = "Planned"
    if st.button("♾️ All"): st.session_state.current_project = "All"
    if st.button("✔️ Completed"): st.session_state.current_project = "Completed"
    if st.button("🏠 Tasks"): st.session_state.current_project = "Tasks"
    
    st.divider()
    
    # Custom Projects
    st.markdown("<p style='font-size:12px; font-weight:600; color:#605E5C; margin-bottom:5px;'>PROJECTS</p>", unsafe_allow_html=True)
    projects = db.get_projects()
    
    for p in projects:
        icon = "📥" if p['name'] == 'inbox' else "📋"
        if st.button(f"{icon} {p['name'].capitalize()}", key=f"proj_{p['id']}"):
            st.session_state.current_project = p['id']
            st.rerun()
            
    st.divider()
    new_proj = st.text_input("New Project Name", placeholder="➕ New list", label_visibility="collapsed")
    if new_proj:
        new_id = db.add_project(new_proj)
        st.session_state.current_project = new_id
        st.rerun()

# Determine current view title
if isinstance(st.session_state.current_project, str):
    view_title = st.session_state.current_project
    # Fetch tasks based on smart list
    all_tasks = db.get_tasks(include_completed=True)
    if view_title == "My Day":
        tasks = [t for t in all_tasks if not t['completed']]
    elif view_title == "Important":
        tasks = [t for t in all_tasks if "Important" in t['tags'] and not t['completed']]
    elif view_title == "Planned":
        tasks = [t for t in all_tasks if t['due_date'] and not t['completed']]
    elif view_title == "Completed":
        tasks = [t for t in all_tasks if t['completed']]
    elif view_title == "All":
        tasks = all_tasks
    else: # Tasks
        tasks = [t for t in all_tasks if not t['completed']]
else:
    proj_name = next((p['name'] for p in projects if p['id'] == st.session_state.current_project), "Unknown")
    view_title = proj_name.capitalize()
    tasks = db.get_tasks(project_id=st.session_state.current_project, include_completed=False)

# Main Title Area
st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
st.markdown(f"<h2 style='color: #2564CF; font-weight: 600; font-size: 24px; margin-bottom: 20px;'>{view_title}</h2>", unsafe_allow_html=True)

# Add Task Input Bar
with st.container():
    if st.session_state.clarification_pending:
        st.warning("Clarification Needed!")
        st.info(st.session_state.clarification_pending['question'])
        rule = st.text_input("Teach me what this means for next time:")
        if st.button("Save & Continue"):
            db.add_memory_rule(rule)
            st.session_state.clarification_pending = None
            st.rerun()
    else:
        st.markdown("<div class='add-task-bar'>", unsafe_allow_html=True)
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            task_input = st.text_input("Add a task", placeholder="Add a task", label_visibility="collapsed", key="task_input")
        with col2:
            st.write("") # spacing
            submit = st.button("Add", type="secondary")
            
        if (submit and task_input) or task_input:
            with st.spinner("Thinking..."):
                parsed = llm.parse_task(task_input)
                if parsed.get('needs_clarification'):
                    st.session_state.clarification_pending = {
                        "question": parsed.get('clarification_question', "Can you clarify?")
                    }
                    st.rerun()
                else:
                    proj_id = st.session_state.current_project if isinstance(st.session_state.current_project, int) else 1 # default inbox
                    t_id = db.add_task(
                        title=parsed.get('title', task_input),
                        project_id=proj_id,
                        description=parsed.get('description', ''),
                        due_date=parsed.get('due_date', None),
                        task_type=parsed.get('task_type', '')
                    )
                    for tg in parsed.get('tags', []):
                        db.add_tag_to_task(t_id, tg)
                    if view_title == "Important":
                        db.add_tag_to_task(t_id, "Important")
                    st.session_state.submit = True
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# List Tasks
main_tasks = [t for t in tasks if not t.get('parent_id')]

for t in main_tasks:
    st.markdown("<div class='task-container'>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([0.05, 0.9, 0.05])
    
    with col1:
        st.write("") # spacing for alignment
        is_done = st.checkbox("done", value=bool(t['completed']), key=f"done_{t['id']}", label_visibility="collapsed")
        if is_done != bool(t['completed']):
            db.update_task(t['id'], completed=is_done)
            st.rerun()
            
    with col2:
        title_style = "text-decoration: line-through; color: #605E5C;" if t['completed'] else "color: #201F1E;"
        st.markdown(f"<p class='task-title' style='{title_style}'>{t['title']}</p>", unsafe_allow_html=True)
        
        meta = []
        if t['task_type']: meta.append(f"<span style='color: #2564CF; font-weight:600;'>{t['task_type']}</span>")
        if t['due_date']: meta.append(f"📅 {t['due_date']}")
        meta_html = " • ".join(meta)
        if meta_html:
            st.markdown(f"<p class='task-meta'>{meta_html}</p>", unsafe_allow_html=True)
            
        with st.expander("Details"):
            new_title = st.text_input("Title", t['title'], key=f"t_{t['id']}")
            new_desc = st.text_area("Notes", t['description'] or "", key=f"d_{t['id']}")
            if st.button("Save", key=f"s_{t['id']}"):
                db.update_task(t['id'], title=new_title, description=new_desc)
                st.rerun()
            if st.button("Delete", key=f"del_{t['id']}"):
                db.delete_task(t['id'])
                st.rerun()
                
    with col3:
        st.write("")
        is_imp = "Important" in t['tags']
        if st.button("⭐" if is_imp else "☆", key=f"star_{t['id']}"):
            if is_imp:
                db.clear_task_tags(t['id']) 
                for tag in t['tags']: 
                    if tag != "Important": db.add_tag_to_task(t['id'], tag)
            else:
                db.add_tag_to_task(t['id'], "Important")
            st.rerun()
            
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)
