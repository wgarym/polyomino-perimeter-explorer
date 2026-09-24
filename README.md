# Polyomino Perimeter Explorer

Streamlit prototype migrated from `display072926b.ipynb`. It reads the existing
JSON datasets from `https://wgarym.github.io/perimeter/` and does not modify or
replace the Mercury application.

## Run locally

```bash
python3 -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Search format

Use `#`, `X`, `x`, or `1` for filled blocks. Use any other character for an
empty cell, and separate rows with commas or line breaks. Press Command+Enter
on macOS (or Control+Enter on other systems) to run the search, or use the
Search button. For example:

```text
#.,
##
```

The Display controls adjust the pixel size of each rendered block and the
number of character cells used to pack each page. Screen width follows the
measured browser content width by default; turn off `Fit width to browser` to
set it manually.

## Deploy

Push this directory to a GitHub repository, open Streamlit Community Cloud,
and select `streamlit_app.py` as the entrypoint.
