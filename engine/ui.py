"""
公共 UI 样式模块
"""

import streamlit as st

COMPACT_CSS = """
<style>
/* 减少块容器间距 */
.block-container {
    padding-top: 0.5rem !important;
    padding-bottom: 0.5rem !important;
}

/* 减少所有元素垂直间距 */
div[data-testid="stVerticalBlock"] > div {
    gap: 0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    gap: 0 !important;
}

/* 减少 markdown/text 间距 */
.stMarkdown {
    margin-bottom: 0 !important;
}
.stMarkdown p {
    margin-bottom: 0.1rem !important;
    line-height: 1.3 !important;
}
.stMarkdown ul, .stMarkdown ol {
    margin-top: 0 !important;
    margin-bottom: 0.1rem !important;
    padding-left: 1.2rem !important;
}
.stMarkdown li {
    margin-bottom: 0 !important;
    line-height: 1.4 !important;
}

/* 减少 dataframe 间距 */
.stDataFrame {
    margin-bottom: 0 !important;
}

/* 减少 metric 间距 */
div[data-testid="stMetric"] {
    padding: 0 !important;
}
div[data-testid="stMetricValue"] {
    font-size: 1.1rem !important;
}
div[data-testid="stMetricLabel"] {
    font-size: 0.75rem !important;
}

/* 减少 selectbox 间距 */
.stSelectbox {
    margin-bottom: 0 !important;
}
.stSelectbox > div {
    margin-bottom: 0 !important;
}

/* 减少 expander 间距 */
div[data-testid="stExpander"] {
    margin-bottom: 0 !important;
}
div[data-testid="stExpander"] details {
    padding: 0 !important;
}
div[data-testid="stExpander"] details summary {
    padding: 0.3rem 0.5rem !important;
}
div[data-testid="stExpander"] details > div {
    padding: 0.2rem 0.5rem !important;
}
.streamlit-expanderContent {
    padding: 0 !important;
}
.streamlit-expanderContent > div {
    gap: 0 !important;
}

/* 减少标题间距 */
h1 {
    margin-top: 0 !important;
    margin-bottom: 0.3rem !important;
    font-size: 1.6rem !important;
    padding-top: 0 !important;
}
h2 {
    margin-top: 0 !important;
    margin-bottom: 0.2rem !important;
    font-size: 1.2rem !important;
}
h3 {
    margin-top: 0 !important;
    margin-bottom: 0.1rem !important;
    font-size: 1rem !important;
}

/* 减少 divider 间距 */
hr {
    margin-top: 0.2rem !important;
    margin-bottom: 0.2rem !important;
}

/* 减少 columns 间距 */
div[data-testid="column"] {
    padding: 0 0.2rem !important;
}
div[data-testid="stHorizontalBlock"] {
    gap: 0.3rem !important;
}

/* 减少 caption 间距 */
.stCaption {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}

/* 减少 code block 间距 */
.stCode {
    margin-bottom: 0 !important;
}

/* 减少 info/warning/error 间距 */
.stAlert {
    margin-bottom: 0 !important;
    padding: 0.3rem 0.5rem !important;
}

/* 减少 element container 间距 */
div[data-testid="stElementContainer"] {
    margin-bottom: 0 !important;
}

/* 减少 sidebar 间距 */
section[data-testid="stSidebar"] .block-container {
    padding-top: 0.5rem !important;
}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div {
    gap: 0.2rem !important;
}
</style>
"""


def apply_compact_style():
    """应用紧凑样式，减少整体间距"""
    st.markdown(COMPACT_CSS, unsafe_allow_html=True)
