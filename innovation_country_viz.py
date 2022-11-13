"""
Streamlit app for visualizing OpenAlex data on a treemap.

Author: Shreyas Gadgin Matha
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from google.oauth2 import service_account
from google.cloud import storage
import gcsfs

# Set app to be wide
st.set_page_config(page_title="Country Innovation Profiles", layout="wide")


def create_gcp_client():
    # Create GCP client
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    client = storage.Client(credentials=credentials)
    return client


def prepare_gcsfs():
    # Get GCP client
    client = create_gcp_client()
    # Create GCSFS
    fs = gcsfs.GCSFileSystem(project=client.project, token=client._credentials)
    return fs


def gcsfs_to_pandas(fs, BUCKET_NAME, file_name):
    with fs.open(f"{BUCKET_NAME}/{file_name}") as f:
        if file_name.endswith(".parquet"):
            df = pd.read_parquet(f)
        elif file_name.endswith(".csv"):
            df = pd.read_csv(f)
        else:
            raise ValueError("File format not supported")
    return df


@st.experimental_memo(ttl=600)
def read_data():
    # Get GCSFS
    fs = prepare_gcsfs()
    # Set GCS bucket name
    BUCKET_NAME = "country-innovation"
    # Read OpenAlex data
    works_all = gcsfs_to_pandas(fs, BUCKET_NAME, "country_concept.parquet")
    # Read patents data
    patents = gcsfs_to_pandas(fs, BUCKET_NAME, "country_patents.parquet")
    # Read country codes
    country_codes = gcsfs_to_pandas(fs, BUCKET_NAME, "country_codes.parquet")
    return works_all, patents, country_codes


def write_intro():
    # Set up app
    st.title("Country Innovation Profiles")
    st.markdown(
        """
        What do countries innovate in? This app visualizes data on patents and scientific publications from [WIPO WIPR (Miguelez et al 2019)](https://tind.wipo.int/record/40558/files/wipo_pub_econstat_wp_58.pdf) and [OpenAlex](https://openalex.org/) respectively. The data is aggregated to the country-technology class / country-scientific concept levels.
        """
    )

# -------------------------#
# Write intro
write_intro()

# -------------------------#
# Read data
fs = prepare_gcsfs()
# Set GCS bucket name
BUCKET_NAME = "country-innovation"
works_all, patents, country_codes = read_data()

# -------------------------#
# Set up sidebar - generic
# -------------------------#

# st.sidebar.title("Treemap parameters")
# Country
selected_country_name = st.sidebar.selectbox(
    "Country", country_codes.country_name.unique()
)
selected_country = country_codes[
    country_codes.country_name == selected_country_name
].country_code.values[0]

# -------------------------#
# Set up sidebar - OpenAlex
# -------------------------#

st.sidebar.markdown("# Publications")

# Citation count constraint
selected_oa_citation_constraint = st.sidebar.radio(
    "Citation count constraint", ["none", "at least 5"]
)
# Metric - articles or citations
selected_oa_metric = st.sidebar.radio("Metric", ["works", "citations"])
# Type of apportioning
selected_oa_apportion_type = st.sidebar.radio(
    "Apportioning concepts with multiple parents", ["dominant", "equal"]
)
# Transformations
selected_oa_transformations = st.sidebar.radio(
    "Transformations", ["none", "rca"], key="Transformations - OpenAlex"
)

# -------------------------#
# Set up sidebar - Patents
# -------------------------#

st.sidebar.markdown("# Patents")

# Transformations
selected_pat_transformations = st.sidebar.radio(
    "Transformations", ["none", "rca"], key="Transformations - Patents"
)

# -------------------------#
# Process parameters

# Filter to selected country
country_works_count = works_all[works_all.country_code == selected_country]
country_patents_count = patents[patents.country_code == selected_country]


# -------------------------#
# Plot OpenAlex data
# -------------------------#

st.markdown("### Publications - 2010-2021")

# Prepare plotting column - OpenAlex

# Column to plot - citation constraint
if selected_oa_citation_constraint == "none":
    plot_col_oa = f"{selected_oa_metric}_{selected_oa_apportion_type}"
elif selected_oa_citation_constraint == "at least 5":
    plot_col_oa = f"{selected_oa_metric}_{selected_oa_apportion_type}_cited"
else:
    raise "Invalid citation constraint"  # type: ignore
# Column to plot - rca or not
if selected_oa_transformations == "none":
    plot_col_oa = plot_col_oa
elif selected_oa_transformations == "rca":
    plot_col_oa = plot_col_oa + "_rca"
else:
    raise "Invalid transformation"  # type: ignore

# -------------------------#
# Plot treemap
fig_oa = px.treemap(
    country_works_count,
    path=[px.Constant(selected_country), "broad_concept_name", "concept_name"],
    values=plot_col_oa,
)
# fig_oa.update_traces(root_color="lightgrey")
fig_oa.update_layout(margin=dict(t=50, l=25, r=25, b=25))

st.plotly_chart(fig_oa, use_container_width=True)
# # Add caption with note
# st.caption(
#     "Note: the treemap corresponds to journal articles published in the period 2010-2021."
# )


# -------------------------#
# Plot patents data
# -------------------------#

st.markdown("### Patents - 2010-2019")

# Prepare plotting column - patents

# Column to plot - rca or not
plot_col_pat = "patent_count"
if selected_pat_transformations == "none":
    plot_col_pat = plot_col_pat
elif selected_pat_transformations == "rca":
    plot_col_pat = plot_col_pat + "_rca"
else:
    raise "Invalid transformation"  # type: ignore

# -------------------------#
# Plot treemap
fig_pat = px.treemap(
    country_patents_count,
    path=[px.Constant(selected_country), "section_code", "subclass_code"],
    hover_name="subclass_name",
    hover_data=[
        "section_name",
    ],
    values=plot_col_pat,
)
fig_pat.update_layout(margin=dict(t=50, l=25, r=25, b=25))
st.plotly_chart(fig_pat, use_container_width=True)
# # Add caption with note
# st.caption(
#     "Note: the treemap corresponds to patents published in the period 2010-2018."
# )

# -------------------------#
# Write footer
st.markdown(
    """
    ## Contact us

    We would love to hear your feedback:

    - Publications data or visualization app: shreyas_gadgin_matha[at]hks[dot]harvard[dot]edu
    - Patents data: christian_chacua[at]hks[dot]harvard[dot]edu
    """
)
