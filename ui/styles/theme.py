from __future__ import annotations

import streamlit as st


THEME = """
<style>
:root {
    --xhs-bg: #08090a;
    --xhs-panel: #0f1011;
    --xhs-surface: #191a1b;
    --xhs-text: #f7f8f8;
    --xhs-muted: #8a8f98;
    --xhs-border: rgba(255,255,255,.08);
    --xhs-accent: #5e6ad2;
}
.stApp {
    background: var(--xhs-bg);
    color: var(--xhs-text);
}
[data-testid="stAppViewContainer"] > .main .block-container {
    max-width: 1080px;
    padding-top: 56px;
    padding-bottom: 80px;
}
[data-testid="stHeader"] {
    background: transparent;
}
h1, h2, h3, p, label, [data-testid="stMarkdownContainer"] {
    font-feature-settings: "cv01", "ss03";
}
h1 {
    font-size: 30px !important;
    font-weight: 510 !important;
    letter-spacing: -.66px !important;
    margin-bottom: 36px !important;
}
h2, h3 {
    font-weight: 510 !important;
    letter-spacing: -.3px !important;
}
[data-testid="stFileUploaderDropzone"],
[data-testid="stForm"],
[data-testid="stDataFrame"] {
    background: rgba(255,255,255,.02);
    border: 1px solid var(--xhs-border);
    border-radius: 8px;
}
[data-testid="stFileUploaderDropzone"] {
    min-height: 132px;
}
.stButton > button, [data-testid="stFormSubmitButton"] > button {
    min-height: 42px;
    border-radius: 6px;
    border: 1px solid var(--xhs-border);
    font-weight: 510;
}
.stButton > button[kind="primary"],
[data-testid="stFormSubmitButton"] > button[kind="primary"] {
    background: var(--xhs-accent);
    border-color: var(--xhs-accent);
}
.stButton > button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
    background: #7170ff;
    border-color: #7170ff;
}
[data-testid="stCaptionContainer"], .stCaption {
    color: var(--xhs-muted) !important;
}
[data-testid="stAlert"] {
    border: 1px solid var(--xhs-border);
    border-radius: 8px;
}
hr {
    border-color: var(--xhs-border) !important;
}
@media (max-width: 640px) {
    [data-testid="stAppViewContainer"] > .main .block-container {
        padding: 32px 20px 56px;
    }
    h1 {
        font-size: 26px !important;
        margin-bottom: 28px !important;
    }
}
</style>
"""


def apply_theme() -> None:
    st.markdown(THEME, unsafe_allow_html=True)
