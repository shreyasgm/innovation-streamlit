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


@st.cache_data(ttl=600)
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
    # Read country totals
    country_totals = gcsfs_to_pandas(fs, BUCKET_NAME, "country_totals.parquet")
    return works_all, patents, country_codes, country_totals


def write_intro():
    # Set up app
    st.title("Country Innovation Profiles")
    st.markdown(
        """
        What do countries innovate in? This app visualizes data on patents from [PATSTAT](https://www.epo.org/en/searching-for-patents/business/patstat) using the methodology from [WIPO WIPR (Miguelez et al 2019)](https://tind.wipo.int/record/40558/files/wipo_pub_econstat_wp_58.pdf), and on scientific publications from [OpenAlex](https://openalex.org/). The data is aggregated to the country-technology class / country-scientific concept levels.

        Publications and patents data cover the 10-year period 2013-2022.
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
works_all, patents, country_codes, country_totals = read_data()

# -------------------------#
# Set up sidebar - generic
# -------------------------#

# st.sidebar.title("Treemap parameters")
# Country
selected_country_name = st.sidebar.selectbox(
    label="Country",
    options=country_codes.country_name.unique(),
)
selected_country = country_codes[
    country_codes.country_name == selected_country_name
].country_code.values[0]

# -------------------------#
# Set up sidebar - OpenAlex
# -------------------------#

st.sidebar.markdown("# Publications")

# Metric - articles or citations
selected_oa_metric = st.sidebar.radio(
    "Metric", ["works", "citations"], help="Metric used to draw visualizations"
)

# Citation count constraint
selected_oa_citation_constraint = st.sidebar.radio(
    "Citation count constraint",
    ["none", "at least 5"],
    help="Minimum number of citations for a publication to be included",
)

# Scatterplot transformation
selected_oa_agg_input = st.sidebar.radio(
    "Aggregation method for scatterplot",
    ["per capita", "total", "sophistication (expy)"],
    help="Aggregation method for scatterplot",
    key="Aggregation - OpenAlex",
)

# Transformations
selected_oa_transformations = st.sidebar.radio(
    "Transformations for treemap",
    [
        "none",
        "rca",
    ],
    key="Transformations - OpenAlex",
    help="Transformations to apply to the data",
)

# Coloring
selected_oa_color_parameter = st.sidebar.radio(
    "Color for treemap",
    ["broad concept", "concept sophistication (prody)"],
    key="Color - OpenAlex",
    help="Method to use for coloring the treemap",
)

# -------------------------#
# Set up sidebar - Patents
# -------------------------#

st.sidebar.markdown("# Patents Families")

# Scatterplot transformation
selected_pat_agg_input = st.sidebar.radio(
    "Aggregation method for scatterplot",
    ["per capita", "total", "sophistication (expy)"],
    help="Aggregation method for scatterplot",
    key="Aggregation - Patents",
)

# Transformations
selected_pat_transformations = st.sidebar.radio(
    "Transformations for treemap",
    ["none", "rca"],
    key="Transformations - Patents",
    help="Transformations to apply to the data",
)

# Coloring
selected_pat_color_parameter = st.sidebar.radio(
    "Color for treemap",
    ["patent class", "subclass sophistication (prody)"],
    key="Color - Patents",
    help="Method to use for coloring the treemap",
)

# -------------------------#
# Set pre-defined color ranges for prody
patents_prody_color_range = {"patent_count_prody_count": (20412.18, 46355.5)}

publications_prody_color_range = {
    "works_prody_count": (18020.53, 35572.04),
    "citations_prody_count": (20481.44, 38344.45),
    "works_cited_prody_count": (18803.98, 35492.67),
    "citations_cited_prody_count": (20002.89, 38103.41),
}
# -------------------------#

# Process parameters

# Filter to selected country
country_works_count = works_all[works_all.country_code == selected_country]
country_patents_count = patents[patents.country_code == selected_country]

# -------------------------#
# Plot scatters
# -------------------------#

# Scatterplot parameters - publications - citation constraint
if selected_oa_citation_constraint == "none":
    scatter_col_oa = selected_oa_metric
elif selected_oa_citation_constraint == "at least 5":
    scatter_col_oa = f"{selected_oa_metric}_cited"
else:
    raise "Invalid citation constraint"

# Scatterplot parameters - publications - aggregation
log_oa = True
if selected_oa_agg_input == "total":
    scatter_col_oa = scatter_col_oa
elif selected_oa_agg_input == "per capita":
    scatter_col_oa = f"{scatter_col_oa}_pc"
elif selected_oa_agg_input == "sophistication (expy)":
    scatter_col_oa = f"{scatter_col_oa}_expy_count"
    log_oa = False
else:
    raise "Invalid aggregation method"

# Scatterplot parameters - patents - aggregation
scatter_col_pat = "patent_count"
log_pat = True
if selected_pat_agg_input == "total":
    scatter_col_pat = scatter_col_pat
elif selected_pat_agg_input == "per capita":
    scatter_col_pat = f"{scatter_col_pat}_pc"
elif selected_pat_agg_input == "sophistication (expy)":
    scatter_col_pat = f"{scatter_col_pat}_expy_count"
    log_pat = False
else:
    raise "Invalid aggregation method"


# Add annotation
country_totals["selected_country"] = ""
country_totals.loc[
    country_totals.country_code == selected_country, "selected_country"
] = selected_country

# Scatterplot - publications
scatter_oa = px.scatter(
    country_totals,
    x="gdppc",
    y=scatter_col_oa,
    color="region",
    size="pop",
    log_x=True,
    log_y=log_oa,
    hover_name="country_name",
    hover_data=[
        "gdppc",
        scatter_col_oa,
    ],
    text="selected_country",
    labels={
        "gdppc": "GDP per capita",
        scatter_col_oa: f"Publications {selected_oa_agg_input}",
    },
    template="simple_white",
)
scatter_oa.update_layout(margin=dict(t=50, l=25, r=25, b=25), showlegend=False)


# Scatterplot - patents
scatter_pat = px.scatter(
    country_totals,
    x="gdppc",
    y=scatter_col_pat,
    color="region",
    size="pop",
    log_x=True,
    log_y=log_pat,
    hover_name="country_name",
    hover_data=[
        "gdppc",
        scatter_col_pat,
    ],
    text="selected_country",
    labels={
        "gdppc": "GDP per capita",
        scatter_col_pat: f"Patents {selected_pat_agg_input}",
    },
    template="simple_white",
)
scatter_pat.update_layout(margin=dict(t=50, l=25, r=25, b=25), showlegend=False)


# Plot side by side
col1, col2 = st.columns(2)
with col1:
    st.markdown(
        "<h3 style='text-align: center;'>Publications</h3>", unsafe_allow_html=True
    )
    st.plotly_chart(scatter_oa, use_container_width=True)

with col2:
    st.markdown("<h3 style='text-align: center;'>Patents</h3>", unsafe_allow_html=True)
    st.plotly_chart(scatter_pat, use_container_width=True)

# -------------------------#
# Treemaps
# -------------------------#

# Get country total for publications
country_total_patents_count = country_totals.loc[
    country_totals.country_code == selected_country, "patent_count"
].iloc[0]
country_total_works_count = country_totals.loc[
    country_totals.country_code == selected_country, "works"
].iloc[0]
country_total_citations_count = country_totals.loc[
    country_totals.country_code == selected_country, "citations"
].iloc[0]

# -------------------------#
# Plot OpenAlex treemap
# -------------------------#

st.markdown("### Publications in Scientific Fields")

st.markdown(f"Total publications: {country_total_works_count:,.0f}")
st.markdown(f"Total citations: {country_total_citations_count:,.0f}")

# Prepare plotting column - OpenAlex

# Column to plot - citation constraint
if selected_oa_citation_constraint == "none":
    plot_col_oa_constraint = f"{selected_oa_metric}"
elif selected_oa_citation_constraint == "at least 5":
    plot_col_oa_constraint = f"{selected_oa_metric}_cited"
else:
    raise ValueError("Invalid citation constraint")


# Column to plot - rca or not
if selected_oa_transformations == "none":
    plot_col_oa = plot_col_oa_constraint
elif selected_oa_transformations == "rca":
    plot_col_oa = plot_col_oa_constraint + "_rca"
else:
    raise ValueError("Invalid transformation")

# Column to plot - color
if selected_oa_color_parameter == "concept sophistication (prody)":
    color_col_oa = f"{plot_col_oa_constraint}_prody_count"
elif selected_oa_color_parameter == "broad concept":
    color_col_oa = None
else:
    raise ValueError("Invalid color parameter")

# -------------------------#
# Plot treemap
# if (
#     selected_oa_transformations == "none"
#     and selected_oa_color_parameter == "broad concept"
# ):
#     fig_oa_path = ["broad_concept_name", "concept_name"]
# else:
#     fig_oa_path = ["concept_name"]
fig_oa_path = ["broad_concept_name", "concept_name"]

if selected_oa_color_parameter == "concept sophistication (prody)":
    fig_oa_color = color_col_oa
    fig_oa_color_continous_scale = px.colors.sequential.Inferno
    fig_oa_range_color = publications_prody_color_range[color_col_oa]
    fig_oa_labels_dict = {color_col_oa: "PRODY"}
else:
    fig_oa_color = None
    fig_oa_color_continous_scale = None
    fig_oa_range_color = None
    fig_oa_labels_dict = None

fig_oa = px.treemap(
    country_works_count[country_works_count[plot_col_oa] > 0],
    path=fig_oa_path,
    values=plot_col_oa,
    hover_name="concept_name",
    color=fig_oa_color,
    color_continuous_scale=fig_oa_color_continous_scale,
    range_color=fig_oa_range_color,
    labels=fig_oa_labels_dict,
)
fig_oa.update_layout(margin=dict(t=50, l=25, r=25, b=25))

st.plotly_chart(fig_oa, use_container_width=True)

# -------------------------#
# Plot patents treemap
# -------------------------#

st.markdown("### Patent Families in Technologies (IPC4 Subclasses)")

st.markdown(f"Total patent families: {country_total_patents_count:,.0f}")

# Prepare plotting column - patents

# Column to plot - rca or not
plot_col_pat_raw = "patent_count"
if selected_pat_transformations == "none":
    plot_col_pat = plot_col_pat_raw
elif selected_pat_transformations == "rca":
    plot_col_pat = plot_col_pat_raw + "_rca"
else:
    raise ValueError("Invalid transformation")

# Column to plot - color
if selected_pat_color_parameter == "subclass sophistication (prody)":
    color_col_pat = f"{plot_col_pat_raw}_prody_count"
elif selected_pat_color_parameter == "patent class":
    color_col_pat = None
else:
    raise ValueError("Invalid color parameter")


# -------------------------#
# Plot treemap
# if (
#     selected_pat_transformations == "none"
#     and selected_pat_color_parameter == "patent class"
# ):
#     fig_pat_path = ["section_name", "subclass_name"]
# else:
#     fig_pat_path = ["subclass_name"]
fig_pat_path = ["section_name", "subclass_name"]

if selected_pat_color_parameter == "subclass sophistication (prody)":
    fig_pat_color = color_col_pat
    fig_pat_color_continous_scale = px.colors.sequential.Inferno
    fig_pat_range_color = patents_prody_color_range[color_col_pat]
    fig_pat_labels_dict = {color_col_pat: "PRODY"}
else:
    fig_pat_color = None
    fig_pat_color_continous_scale = None
    fig_pat_range_color = None
    fig_pat_labels_dict = None

fig_pat = px.treemap(
    country_patents_count[country_patents_count[plot_col_pat] > 0],
    path=fig_pat_path,
    values=plot_col_pat,
    hover_name="subclass_name",
    hover_data=[
        "subclass_code",
        "section_name",
    ],
    color=fig_pat_color,
    color_continuous_scale=fig_pat_color_continous_scale,
    range_color=fig_pat_range_color,
    labels=fig_pat_labels_dict,
)

fig_pat.update_layout(margin=dict(t=50, l=25, r=25, b=25))
st.plotly_chart(fig_pat, use_container_width=True)

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
