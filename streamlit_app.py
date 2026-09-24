"""Streamlit prototype for browsing polyominoes by area and perimeter."""

import streamlit as st

from perimeter_app.config import MIN_AREA, MAX_AREA, normalize_perimeter, valid_perimeters
from perimeter_app.content_width import get_content_width
from perimeter_app.data import DatasetError, load_dataset
from perimeter_app.display import pack_page, recommended_screen_width, render_page
from perimeter_app.figures import area as figure_area
from perimeter_app.figures import find_figure, is_connected, parse_figure
from perimeter_app.figures import perimeter as figure_perimeter

st.set_page_config(
    page_title="Polyomino Perimeter Explorer",
    page_icon=None,
    layout="wide",
)

grid_column_css = "\n".join(
    f".poly-grid.cols-{column_count} "
    f"{{ grid-template-columns: repeat({column_count}, var(--cell-size)); }}"
    for column_count in range(1, MAX_AREA + 1)
)

st.markdown(
    """
    <style>
    .stApp { color: #202421; }
    [data-testid="stSidebar"] { border-right: 1px solid #d8ddd5; }
    [data-testid="stSidebar"] h2 { font-size: 1.05rem; }
    .block-container { max-width: 1240px; padding-top: 2rem; }
    h1 { font-size: 1.65rem !important; letter-spacing: 0 !important; }
    .app-subtitle { color: #59615b; margin: -0.5rem 0 1.3rem; }
    .result-summary {
        display: flex;
        gap: 1.5rem;
        align-items: baseline;
        flex-wrap: wrap;
        padding: 0.65rem 0;
        border-top: 1px solid #d8ddd5;
        border-bottom: 1px solid #d8ddd5;
        margin-bottom: 1rem;
    }
    .result-summary strong { font-size: 1.1rem; }
    .result-summary span { color: #59615b; }
    .poly-results { overflow-x: auto; padding: 0.25rem 0 1.5rem; }
    .poly-row {
        display: flex;
        align-items: flex-start;
        gap: 26px;
        min-width: max-content;
        padding: 14px 4px 20px;
        border-bottom: 1px solid #e2e6df;
    }
    .poly-figure { margin: 0; }
    .poly-grid {
        display: grid;
    }
    __GRID_COLUMN_CSS__
    .poly-cell { width: var(--cell-size); height: var(--cell-size); }
    .poly-cell.filled {
        background: #202421;
        border: 1px solid #f7f8f5;
        box-sizing: border-box;
    }
    .poly-cell.empty { background: transparent; }
    .poly-figure figcaption {
        color: #707871;
        font-size: 0.72rem;
        margin-top: 6px;
        text-align: center;
    }
    [data-testid="stNumberInput"] [data-testid="InputInstructions"] {
        display: none !important;
    }
    div.stButton > button { border-radius: 4px; }
    @media (max-width: 700px) {
        .block-container { padding-top: 1rem; }
        .poly-row { gap: 18px; }
    }
    </style>
    """.replace("__GRID_COLUMN_CSS__", grid_column_css),
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_dataset(area: int, perimeter: int):
    return load_dataset(area, perimeter)


def initialize_state() -> None:
    defaults = {
        "area": 4,
        "selected_perimeter": 8,
        "current_position": 0,
        "page_history": [],
        "active_signature": None,
        "active_layout": None,
        "search_status": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_navigation() -> None:
    st.session_state.current_position = 0
    st.session_state.page_history = []


def go_next(next_position: int) -> None:
    st.session_state.page_history.append(st.session_state.current_position)
    st.session_state.current_position = next_position


def go_previous() -> None:
    if st.session_state.page_history:
        st.session_state.current_position = st.session_state.page_history.pop()
    else:
        st.session_state.current_position = 0


def jump_to_position(position_key: str, result_count: int) -> None:
    requested_position = int(st.session_state[position_key])
    st.session_state.current_position = max(
        0,
        min(requested_position - 1, result_count - 1),
    )
    st.session_state.page_history = []


def run_search() -> None:
    value = st.session_state.search_input.strip()
    if not value:
        st.session_state.search_status = ("warning", "Enter a figure to search for.")
        return

    figure = parse_figure(value)
    if not figure:
        st.session_state.search_status = ("error", "The search does not contain any filled blocks.")
        return
    if not is_connected(figure):
        st.session_state.search_status = ("error", "The entered figure is disconnected.")
        return

    target_area = figure_area(figure)
    target_perimeter = figure_perimeter(figure)
    if not MIN_AREA <= target_area <= MAX_AREA:
        st.session_state.search_status = (
            "error",
            f"The figure has area {target_area}; supported areas run from "
            f"{MIN_AREA} to {MAX_AREA}.",
        )
        return

    try:
        figures = cached_dataset(target_area, target_perimeter)
    except (DatasetError, ValueError) as exc:
        st.session_state.search_status = ("error", str(exc))
        return

    position = find_figure(figure, figures)
    if position < 0:
        st.session_state.search_status = ("warning", "The figure was not found.")
        return

    st.session_state.area = target_area
    st.session_state.selected_perimeter = target_perimeter
    st.session_state[f"perimeter_area_{target_area}"] = target_perimeter
    st.session_state.active_signature = (target_area, target_perimeter)
    st.session_state.current_position = position
    st.session_state.page_history = []
    st.session_state.search_status = (
        "success",
        f"Found at position {position + 1:,}.",
    )


initialize_state()
content_width = get_content_width()

with st.sidebar:
    st.header("Dataset")
    selected_area = st.slider(
        "Area (number of blocks)",
        min_value=MIN_AREA,
        max_value=MAX_AREA,
        key="area",
    )

    perimeter_options = valid_perimeters(selected_area)
    perimeter_key = f"perimeter_area_{selected_area}"
    if perimeter_key not in st.session_state:
        st.session_state[perimeter_key] = normalize_perimeter(
            st.session_state.selected_perimeter,
            selected_area,
        )
    selected_perimeter = st.select_slider(
        "Perimeter (exposed edges)",
        options=perimeter_options,
        key=perimeter_key,
    )
    st.session_state.selected_perimeter = selected_perimeter
    st.caption(
        f"Valid range: {perimeter_options[0]} to {perimeter_options[-1]} "
        "in steps of 2"
    )

    st.header("Search")
    st.text_area(
        "Figure",
        key="search_input",
        placeholder=(
            "Use # or X for blocks; use another character for an empty space. "
            "Separate rows with commas or line breaks."
        ),
        height=100,
        on_change=run_search,
    )
    st.button("Search", on_click=run_search, use_container_width=True)

    st.header("Display")
    block_size = st.slider("Block size", 8, 24, 14, 1)
    automatic_width = st.checkbox("Fit width to browser", value=True)
    measured_screen_width = recommended_screen_width(content_width, block_size)
    if automatic_width:
        screen_width = st.slider(
            "Screen width",
            20,
            100,
            measured_screen_width,
            1,
            key=f"automatic_screen_width_{measured_screen_width}",
            disabled=True,
        )
    else:
        screen_width = st.slider(
            "Screen width",
            20,
            100,
            45,
            1,
            key="manual_screen_width",
        )
    screen_height = st.slider("Screen height", 20, 200, 40, 5)

st.markdown(
    f"<style>:root {{ --cell-size: {block_size}px; }}</style>",
    unsafe_allow_html=True,
)

signature = selected_area, selected_perimeter
if signature != st.session_state.active_signature:
    st.session_state.active_signature = signature
    reset_navigation()
    st.session_state.search_status = None

layout_signature = screen_width, screen_height
if layout_signature != st.session_state.active_layout:
    st.session_state.active_layout = layout_signature
    st.session_state.page_history = []

st.title("Polyomino Perimeter Explorer")
st.markdown(
    '<p class="app-subtitle">Browse fixed polyominoes by area and perimeter.</p>',
    unsafe_allow_html=True,
)

if st.session_state.search_status:
    status_type, status_message = st.session_state.search_status
    getattr(st, status_type)(status_message)

try:
    with st.spinner("Loading figures..."):
        figures = cached_dataset(selected_area, selected_perimeter)
except (DatasetError, ValueError) as exc:
    st.error(str(exc))
    st.stop()

if not figures:
    st.info("No solutions are available for this area and perimeter.")
    st.stop()

st.session_state.current_position = max(
    0,
    min(st.session_state.current_position, len(figures) - 1),
)
page = pack_page(
    figures,
    st.session_state.current_position,
    screen_width,
    screen_height,
)

st.markdown(
    '<div class="result-summary">'
    f'<strong>Area {selected_area}</strong>'
    f'<strong>Perimeter {selected_perimeter}</strong>'
    f'<span>{len(figures):,} solutions</span>'
    f'<span>Showing {page.start + 1:,} to {page.end:,}</span>'
    "</div>",
    unsafe_allow_html=True,
)

previous_column, position_column, next_column = st.columns([1, 2, 1])
with previous_column:
    st.button(
        "Previous Page",
        on_click=go_previous,
        disabled=page.start == 0,
        use_container_width=True,
    )
with position_column:
    position_key = f"start_position_{signature}_{page.start}"
    input_column, go_column = st.columns([3, 1])
    with input_column:
        st.number_input(
            "Starting position",
            min_value=1,
            max_value=len(figures),
            value=page.start + 1,
            step=1,
            label_visibility="collapsed",
            key=position_key,
            on_change=jump_to_position,
            args=(position_key, len(figures)),
        )
    with go_column:
        st.button(
            "Go",
            on_click=jump_to_position,
            args=(position_key, len(figures)),
            use_container_width=True,
        )
with next_column:
    st.button(
        "Next Page",
        on_click=go_next,
        args=(page.end,),
        disabled=page.end >= len(figures),
        use_container_width=True,
    )

st.markdown(render_page(page), unsafe_allow_html=True)
