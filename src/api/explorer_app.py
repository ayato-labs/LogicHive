import streamlit as st
import asyncio
import pandas as pd
import sys
from pathlib import Path

# Add backend to path before importing local modules
sys.path.append(str(Path(__file__).parent.parent))

from storage.sqlite_api import sqlite_storage  # noqa: E402

# --- MINIMALIST DESIGN ---
st.set_page_config(
    page_title="LogicHive | Personal Logic Vault", layout="wide", page_icon="🛡️"
)

st.markdown(
    """
    <style>
    .main { background-color: #0e1117; color: #e6edf3; }
    h1 { color: #4facfe; }
    </style>
    """,
    unsafe_allow_html=True,
)


async def load_data():
    # Direct local access to all functions
    return await sqlite_storage.get_all_functions()


def main():
    st.title("🛡️ Personal Logic Vault")
    st.markdown("Direct local access enabled (No authentication required).")

    tab1, tab2 = st.tabs(["📊 Assets", "⚙️ DB Stats"])

    with tab1:
        with st.spinner("Loading logic assets..."):
            funcs = asyncio.run(load_data())

        if funcs:
            df = pd.DataFrame(funcs)
            c1, c2, c3 = st.columns(3)
            c1.metric("Assets", len(df))
            c2.metric("Executions", df["call_count"].sum() if "call_count" in df else 0)
            c3.metric(
                "Avg Reliability",
                f"{df['reliability_score'].mean():.2f}"
                if "reliability_score" in df
                else "1.0",
            )

            st.subheader("Asset Audit")
            cols = ["name", "description", "language", "created_at"]
            display_cols = [c for c in cols if c in df.columns]
            st.dataframe(
                df[display_cols],
                use_container_width=True,
                hide_index=True,
            )

            selected_func = st.selectbox("View Source", df["name"].tolist())
            f_data = df[df["name"] == selected_func].iloc[0]
            st.code(f_data["code"], language=f_data.get("language", "python"))
        else:
            st.info("The vault is empty. Save functions via MCP to see them here.")

    with tab2:
        st.write("### Database Status")
        st.write(f"SQLite DB Path: `{sqlite_storage._db_path or 'logichive.db'}`")
        if st.button("Refresh Cache"):
            st.rerun()


if __name__ == "__main__":
    main()
