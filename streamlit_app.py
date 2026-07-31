# streamlit_app.py
# Streamlit Cloud often defaults to this filename as the Main file.
# Delegate to app.py so Cosmic Cards and the full Lunatick build load.

from pathlib import Path
import runpy

_APP = Path(__file__).resolve().parent / "app.py"
runpy.run_path(str(_APP), run_name="__main__")
