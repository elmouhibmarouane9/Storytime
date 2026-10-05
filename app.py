"""Entry shim — the console lives in streamlit_app.py.

    streamlit run app.py        # or
    streamlit run streamlit_app.py
"""

import streamlit_app  # noqa: F401  (importing runs the app — Streamlit executes top-level code)
