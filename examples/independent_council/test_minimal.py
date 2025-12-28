#!/usr/bin/env python3
"""Minimal test to verify Streamlit works"""

import streamlit as st

st.set_page_config(page_title="Test", layout="wide")

st.title("💡 Test Page")
st.write("If you see this, the basic Streamlit setup works!")

st.sidebar.header("Test Sidebar")
st.sidebar.write("Sidebar content")



