#!/usr/bin/env python3
"""
Streamlit application for Independent Council Idea Generation Bot
"""

import streamlit as st

# Page config MUST be first
st.set_page_config(
    page_title="Independent Council Idea Generator",
    page_icon="💡",
    layout="wide"
)

import asyncio
import sys
import os
import threading
import time
from datetime import datetime
from typing import Dict, List

# Add the src directory to the path
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.join(_script_dir, '..', '..')
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _src_dir)
# Also add the current directory for local imports
sys.path.insert(0, _script_dir)

import_error_msg = None
try:
    from llm_manager import LLMManager
    from independent_bot import IndependentCouncilBot, LLMState, DEFAULT_MODELS, DEFAULT_JUDGE_MODEL, DEFAULT_NOVELTY_THRESHOLD, DEFAULT_COHERENCE_THRESHOLD
except ImportError as e:
    # Store error for display
    import_error_msg = str(e)
    LLMManager = None
    IndependentCouncilBot = None
    DEFAULT_MODELS = []
    DEFAULT_JUDGE_MODEL = "bedrock/claude-sonnet-3.7"
    DEFAULT_NOVELTY_THRESHOLD = 0.15
    DEFAULT_COHERENCE_THRESHOLD = 15

# Initialize session state (wrap in try-except to prevent silent failures)
try:
    if 'llm_manager' not in st.session_state:
        st.session_state.llm_manager = None
        if LLMManager is not None:
            try:
                st.session_state.llm_manager = LLMManager()
            except Exception as e:
                st.session_state.llm_manager_error = str(e)
        else:
            st.session_state.llm_manager_error = f"Import error: {import_error_msg if import_error_msg else 'Could not import LLMManager'}"

    if 'bot' not in st.session_state:
        st.session_state.bot = None

    if 'updates' not in st.session_state:
        st.session_state.updates = {}  # model -> list of updates

    if 'running' not in st.session_state:
        st.session_state.running = False

    if 'results' not in st.session_state:
        st.session_state.results = None
except Exception as e:
    # If session state initialization fails, store error
    if 'init_error' not in st.session_state:
        st.session_state.init_error = str(e)


def update_callback(data: Dict):
    """Callback function to receive updates from the bot"""
    model = data['model']
    if model not in st.session_state.updates:
        st.session_state.updates[model] = []
    st.session_state.updates[model].append(data)


async def run_generation(llm_manager, question: str, models: List[str], max_iterations: int,
                        novelty_threshold: float, coherence_threshold: int, 
                        updates_dict: dict, results_dict: dict, running_flag: dict):
    """Run the idea generation process"""
    # Initialize bot
    bot = IndependentCouncilBot(
        llm_manager,
        judge_model=DEFAULT_JUDGE_MODEL,
        novelty_threshold=novelty_threshold,
        coherence_threshold=coherence_threshold
    )
    
    # Create a callback that updates the shared dict instead of session state
    def thread_safe_callback(data: Dict):
        model = data['model']
        if model not in updates_dict:
            updates_dict[model] = []
        updates_dict[model].append(data)
    
    bot.set_update_callback(thread_safe_callback)
    
    # Clear previous updates
    updates_dict.clear()
    
    # Run generation
    results = await bot.generate_ideas(question, models, max_iterations)
    results_dict['results'] = results
    running_flag['running'] = False


def main():
    # Always show title first
    st.title("💡 Independent Council Idea Generator")
    st.markdown("""
    Each LLM in the council generates ideas independently, maintaining its own conversation history.
    Each response is evaluated by a judge, and LLMs stop when their responses score below thresholds.
    """)
    
    # Sidebar for configuration - ALWAYS show this first
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Question input
        question = st.text_area(
            "Question",
            placeholder="Enter your question here...",
            height=100
        )
        
        # Model selection
        st.subheader("Council Models")
        try:
            available_models = DEFAULT_MODELS
        except NameError:
            # Fallback if DEFAULT_MODELS not imported
            available_models = [
                "azure/o3",
                "azure/o1",
                "bedrock/claude-sonnet-3.7",
                "bedrock/claude-sonnet-4",
            ]
        selected_models = st.multiselect(
            "Select models for the council",
            available_models,
            default=available_models[:min(4, len(available_models))] if available_models else []
        )
        
        # Iterations
        max_iterations = st.number_input(
            "Max Iterations per LLM",
            min_value=1,
            max_value=50,
            value=10,
            help="Maximum number of ideas each LLM will generate"
        )
        
        # Thresholds
        st.subheader("Quality Thresholds")
        novelty_threshold = st.slider(
            "Novelty Threshold",
            min_value=0.0,
            max_value=1.0,
            value=DEFAULT_NOVELTY_THRESHOLD,
            step=0.05,
            help="Minimum novelty score required to continue"
        )
        coherence_threshold = st.slider(
            "Coherence Threshold",
            min_value=0,
            max_value=100,
            value=DEFAULT_COHERENCE_THRESHOLD,
            step=5,
            help="Minimum coherence score required to continue"
        )
        
        # Run button
        run_button = st.button("🚀 Generate Ideas", type="primary", use_container_width=True)
    
    # Check for initialization errors AFTER sidebar is shown
    if hasattr(st.session_state, 'init_error'):
        st.error(f"❌ Initialization error: {st.session_state.init_error}")
        return
    
    # Check if LLM Manager initialized successfully
    if st.session_state.llm_manager is None:
        error_msg = getattr(st.session_state, 'llm_manager_error', 'Unknown error')
        st.error(f"❌ Failed to initialize LLM Manager: {error_msg}")
        st.info("""
        **Troubleshooting:**
        - Make sure all required dependencies are installed (e.g., `pip install openai`)
        - Check that your LLM configuration file is set up correctly
        - Verify that the necessary API keys/credentials are configured
        """)
        return
    
    # Main content area
    if not question:
        st.info("👈 Enter a question in the sidebar to get started")
        return
    
    if not selected_models:
        st.warning("⚠️ Please select at least one model")
        return
    
    # Handle run button
    if run_button and not st.session_state.running:
        st.session_state.running = True
        st.session_state.updates = {}
        st.session_state.results = None
        
        # Capture llm_manager in main thread before starting thread
        llm_manager = st.session_state.llm_manager
        
        # Create thread-safe shared dictionaries
        shared_updates = {}
        shared_results = {'results': None}
        shared_running = {'running': True}
        
        # Run async function in a thread
        def run_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run_generation(
                    llm_manager,  # Use captured value, not from session state
                    question, selected_models, max_iterations,
                    novelty_threshold, coherence_threshold,
                    shared_updates, shared_results, shared_running
                ))
            finally:
                loop.close()
        
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        
        # Store references to shared dicts in session state
        st.session_state.shared_updates = shared_updates
        st.session_state.shared_results = shared_results
        st.session_state.shared_running = shared_running
    
    # Sync shared dictionaries to session state (thread-safe updates)
    if hasattr(st.session_state, 'shared_updates'):
        # Copy updates from shared dict to session state
        for model, updates in st.session_state.shared_updates.items():
            if model not in st.session_state.updates:
                st.session_state.updates[model] = []
            # Only add new updates
            existing_count = len(st.session_state.updates[model])
            if len(updates) > existing_count:
                st.session_state.updates[model] = updates.copy()
        
        # Sync results
        if st.session_state.shared_results['results'] is not None:
            st.session_state.results = st.session_state.shared_results['results']
        
        # Sync running status
        if not st.session_state.shared_running['running']:
            st.session_state.running = False
    
    # Show status and allow manual refresh
    if st.session_state.running:
        status_col1, status_col2 = st.columns([3, 1])
        with status_col1:
            st.info("🔄 Generating ideas... This may take a while. Click 'Refresh' to see updates.")
        with status_col2:
            if st.button("🔄 Refresh", use_container_width=True, key="refresh_btn"):
                st.rerun()
    
    # Display results
    if st.session_state.running or st.session_state.results or st.session_state.updates:
        # Show status and allow manual refresh
        if st.session_state.running:
            status_col1, status_col2 = st.columns([3, 1])
            with status_col1:
                st.info("🔄 Generating ideas... This may take a while. Click 'Refresh' to see updates.")
            with status_col2:
                if st.button("🔄 Refresh", use_container_width=True):
                    st.rerun()
        
        # Create columns for each model
        num_models = len(selected_models)
        if num_models > 0:
            cols = st.columns(num_models)
            
            for idx, model in enumerate(selected_models):
                with cols[idx]:
                    st.subheader(f"🤖 {model}")
                    
                    # Show updates for this model (from callback)
                    if model in st.session_state.updates:
                        updates = st.session_state.updates[model]
                        for update in updates:
                            iteration = update['iteration']
                            idea = update['idea']
                            novelty = update['novelty']
                            coherence = update['coherence']
                            reasoning = update['reasoning']
                            is_active = update['is_active']
                            
                            # Status badge
                            if is_active:
                                st.success(f"✅ Iteration {iteration}")
                            else:
                                st.error(f"⛔ Iteration {iteration} - Stopped")
                            
                            # Scores
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Novelty", f"{novelty:.3f}")
                            with col2:
                                st.metric("Coherence", f"{coherence}")
                            
                            # Idea
                            with st.expander(f"View Idea {iteration}", expanded=True):
                                st.write(idea)
                            
                            # Reasoning
                            with st.expander("Judge Reasoning"):
                                st.write(reasoning)
                            
                            st.divider()
                    
                    # Show final results if available
                    if st.session_state.results and model in st.session_state.results:
                        llm_state = st.session_state.results[model]
                        if llm_state.responses:
                            st.markdown("### 📊 Summary")
                            st.write(f"**Total Ideas:** {len(llm_state.responses)}")
                            st.write(f"**Status:** {'Active' if llm_state.is_active else 'Stopped'}")
                    elif model not in st.session_state.updates:
                        st.info("⏳ Waiting for response...")
        
        # Final summary section
        if st.session_state.results:
            st.divider()
            st.header("📋 Final Summary")
            
            summary_cols = st.columns(3)
            total_ideas = sum(len(state.responses) for state in st.session_state.results.values())
            active_count = sum(1 for state in st.session_state.results.values() if state.is_active)
            stopped_count = len(st.session_state.results) - active_count
            
            with summary_cols[0]:
                st.metric("Total Ideas Generated", total_ideas)
            with summary_cols[1]:
                st.metric("Active LLMs", active_count)
            with summary_cols[2]:
                st.metric("Stopped LLMs", stopped_count)
            
            # Detailed results table
            st.subheader("All Ideas by Model")
            for model, llm_state in st.session_state.results.items():
                with st.expander(f"🤖 {model} - {len(llm_state.responses)} ideas"):
                    for i, resp in enumerate(llm_state.responses, 1):
                        st.markdown(f"### Idea {i} (Iteration {resp['iteration']})")
                        st.write(f"**Novelty:** {resp['novelty']:.3f} | **Coherence:** {resp['coherence']}")
                        st.write(resp['idea'])
                        with st.expander("Judge Reasoning"):
                            st.write(resp['reasoning'])
                        st.divider()


# Always call main - wrap everything to ensure page renders
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # If main fails, at least show something
        st.title("💡 Independent Council Idea Generator")
        st.error(f"❌ An error occurred while loading the application: {e}")
        st.exception(e)
        st.info("""
        **Please check:**
        - All dependencies are installed
        - Python version is compatible
        - File paths are correct
        """)

