# Polyomino Perimeter Explorer

Streamlit prototype migrated from `display072926b.ipynb`. The main app reads
the canonical collection from
`https://wgarym.github.io/polyomino-canonical-data/`. It loads the collection
and dataset manifests first, then downloads only the data segment needed for
the current page or search. It does not modify or replace the Mercury
application.

The previously deployed Streamlit implementation is preserved in
`streamlit_legacy.py`; it continues to use the earlier
`https://wgarym.github.io/perimeter/` collection.

## Run locally

```bash
python3 -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Search format

Use `#`, `X`, `x`, or `1` for filled blocks. Use any other character for an
empty cell, and separate rows with commas or line breaks. Use the Search
button to run the search. For example:

```text
#.,
##
```

The Display controls adjust the pixel size of each rendered block and the
number of character cells used to pack each page. Screen width follows the
measured browser content width by default; turn off `Fit width to browser` to
set it manually.

## Build canonical datasets

The offline builder streams an unsegmented source array, validates every
figure, chooses a deterministic orientation, externally sorts the cases, and
writes size-bounded `row-masks-v1` JSON parts with manifests:

```bash
python -m tools.build_datasets \
  /path/to/data-15-26.json \
  /path/to/output \
  --targets-mib 4 8 16
```

Generated manifests record case counts, cumulative offsets, key ranges,
checksums, ordering version, and encoding version. Dataset generation does not
modify the files used by the deployed application.

To build a resumable collection with parallel workers and then validate every
generated record:

```bash
python -m tools.build_collection OUTPUT_ROOT SOURCE_ROOT [SOURCE_ROOT ...]
python -m tools.validate_collection OUTPUT_ROOT/8MiB
```

## Deploy

Push this directory to a GitHub repository, open Streamlit Community Cloud,
and select `streamlit_app.py` as the entrypoint. To run the preserved version
locally, use `streamlit run streamlit_legacy.py`.
