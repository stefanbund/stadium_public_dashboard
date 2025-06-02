import streamlit as st
import altair as alt
import pandas as pd

# Set page configuration
st.set_page_config(layout="wide")

st.title("Prediction Analysis Dashboard")

# Load the data
try:
    df = pd.read_csv('https://stadiumglobalchart.s3.us-east-2.amazonaws.com/global_chart.csv')
    # st.write("Data loaded successfully. First 5 rows:")
    # # st.write(df.head())
    # st.write(f"Shape of the DataFrame: {df.shape}")
    # st.write("Data types:")
    # st.write(df.dtypes)
except FileNotFoundError:
    st.error("Error: 'global_chart.csv' not found. Please make sure the file is in the same directory as the app.")
    df = None
except Exception as e:
    st.error(f"An error occurred while loading data: {e}")
    df = None

if df is not None:
    st.header("Data Preparation")
    st.subheader("Sort Data by Timestamp")

    # Convert 'prediction_timestamp_utc' to datetime objects if it's not already
    if not pd.api.types.is_datetime64_any_dtype(df['prediction_timestamp_utc']):
        try:
            df['prediction_timestamp_utc'] = pd.to_datetime(df['prediction_timestamp_utc'])
            # st.write("Converted 'prediction_timestamp_utc' to datetime.")
        except ValueError as e:
            st.error(f"Error converting 'prediction_timestamp_utc' to datetime: {e}")
            st.warning("Continuing without sorting.")
        except Exception as e:
            st.error(f"An unexpected error occurred during datetime conversion: {e}")
            st.warning("Continuing without sorting.")
    # else:
        # st.write("'prediction_timestamp_utc' is already in datetime format.")

    # Proceed with sorting if datetime conversion was successful or not needed
    if pd.api.types.is_datetime64_any_dtype(df['prediction_timestamp_utc']):
        try:
            df.sort_values(by='prediction_timestamp_utc', inplace=True, ascending=True)
            # st.write("DataFrame sorted by 'prediction_timestamp_utc'.")
            # st.write("First 5 rows after sorting:")
            # st.write(df.head())
            # st.write("Last 5 rows after sorting:")
            # st.write(df.tail())
        except KeyError:
            st.error("Error: 'prediction_timestamp_utc' column not found after conversion attempt.")
        except Exception as e:
            st.error(f"An unexpected error occurred during sorting: {e}")

    st.header("Charts")

    # --- Chart 1: Chronology of Predictions ---
    st.subheader("A Chronology of Predictions")

    # Create the chart with the requested tooltip additions
    global_chart = alt.Chart(df).mark_circle().encode(
        x=alt.X('prediction_timestamp_utc:T', title="Prediction Timestamp"),
        y=alt.Y('hours_to_target_or_default:Q', title="Hours to Target or Default"),
        color='symbol:N',
        tooltip=[
            alt.Tooltip('symbol:N', title="Symbol"), # Add symbol to tooltip
            alt.Tooltip('hours_to_target_or_default:Q', title="Hours to Target or Default"),
            alt.Tooltip('prediction_timestamp_utc:T', title="Prediction Timestamp"),
            alt.Tooltip('mp_at_prediction:Q', title="MP at Prediction")
        ]
    ).properties(
        title=alt.Title(
            text='A Chronology of Predictions',
            subtitle='120 Days of autonomous trading across Coinbase. Each dot signifies one trade, and the time to complete each trade, in hours. The red line represents a six hour boundary.'
        ),
        width="container",
        height=400
    )

    # Add a horizontal rule at y=6
    g_rule = alt.Chart(pd.DataFrame({'y': [6]})).mark_rule(color='red').encode(y='y')

    # Create the text label for the rule
    g_text = alt.Chart(pd.DataFrame({'y': [6], 'text': ['The six hour line']})).mark_text(
        align='left',
        baseline='middle',
        dx=5 # Adjust horizontal position of the text
    ).encode(
        y='y:Q',
        text='text:N',
        color=alt.value('red') # Match color with the rule
    )

    # Combine the bubble chart, rule, and text
    final_chart = global_chart + g_rule + g_text

    st.altair_chart(final_chart, use_container_width=True)

    # --- Chart 2: Distributions ---
    st.subheader("Distribution of Trade Durations")

    # Create the base chart for the distribution of hours_to_target_or_default
    hours_distribution_base = alt.Chart(df).mark_bar().encode(
        x=alt.X('hours_to_target_or_default:Q', bin=True, title='Hours to Target or Default'),
        y=alt.Y('count()', title='Frequency'),
        color='symbol:N',  # Encode color by symbol in the base chart
        tooltip=[
            alt.Tooltip('symbol:N', title='Symbol'),  # Add symbol to tooltip
            alt.Tooltip('hours_to_target_or_default:Q', bin=True, title='Hours to Exit (Trade Duration, in  Hours)'),
            'count()'
        ]
    ).properties(
        title='120 Day Distribution of Time Durations, Entry to Trade Exit, in Hours by Symbol',
        width="container",
        height=400
    )

    # Create the detailed chart for the selected data
    detailed_distribution = alt.Chart(df).mark_bar().encode(
        x=alt.X('hours_to_target_or_default:Q', bin=alt.Bin(maxbins=100), title='Hours to Target or Default'), # More bins for granularity
        y=alt.Y('count()', title='Frequency'),
        color='symbol:N', # Encode color by symbol in the detailed chart
        tooltip=[
            alt.Tooltip('symbol:N', title='Symbol'), # Add symbol to tooltip
            alt.Tooltip('hours_to_target_or_default:Q', bin=True, title='Hour detail'),
            'count()'
        ]
    ).properties(
        title='Detailed Distribution for each durational bin by Symbol',
        width="container",
        height=400
    )

    # Combine the two charts vertically
    distributions_interactive_chart = alt.vconcat(
        hours_distribution_base,
        detailed_distribution
    ).resolve_axis(
        x='independent' # Allow independent x-axes for the two charts
    ).resolve_scale(
        color='independent' # Allow independent color scales if needed
    )
    st.altair_chart(distributions_interactive_chart, use_container_width=True)

    # --- Chart 3: Interactive Dashboard ---
    st.subheader("Interactive Dashboard: Symbol Prevalence and Time Series")

    # Calculate frequency of each symbol
    symbol_counts = df['symbol'].value_counts().reset_index()
    symbol_counts.columns = ['symbol', 'count']

    # Create a selection for interactivity (filtering by symbol)
    selection = alt.selection_point(fields=['symbol'], empty='all')

    top_chart = alt.Chart(symbol_counts).mark_bar().encode(
        # Y-axis is the symbol, ordered alphabetically ascending (lowest letters on top)
        y=alt.Y('symbol:N', sort='ascending', title="Symbol"),
        # X-axis is the count of entries for each symbol
        x=alt.X('count:Q', title="How Many Trades Done, 120 Day Period"),
        # Color bars by symbol
        color='symbol:N',
        # Add tooltips for symbol and count
        tooltip=[
            alt.Tooltip('symbol:N', title="Ticker Symbol, of Cryptocurrency"),
            alt.Tooltip('count:Q', title="Number of Entries / Prevalence")
        ],
        # Add interactivity - opacity based on selection
        opacity=alt.condition(selection, alt.value(1), alt.value(0.6))
    ).properties(
        title='Ticker Symbols Traded in Period, En Masse, Last 120 Days',
        width="container",  # This already sets the width to the container width
        height=800  # Adjust height as needed for the bars
    ).add_params(
        selection
    )

    # Base chart for the bottom side
    bottom_base = alt.Chart(df).mark_point().encode(
        x=alt.X('prediction_timestamp_utc:T', title="Prediction Timestamp"),
        y=alt.Y('hours_to_target_or_default:Q', title="Hours to Target or Default"),
        # Encode color by symbol in the bottom chart as well
        color='symbol:N',
        tooltip=[
            alt.Tooltip('symbol:N', title="Symbol"), # Add symbol to the tooltip
            alt.Tooltip('prediction_timestamp_utc:T', title="Prediction Timestamp"),
            alt.Tooltip('hours_to_target_or_default:Q', title="Hours to Target or Default")
        ]
    ).properties(
        # Update the title to include the selected symbol
        title=alt.Title(
            text='Time Series for Selected Symbol',
            anchor='start',
            subtitle=['Click on a symbol in the top chart to filter the time series.']
        ),
        width="container", # This also sets the width to the container width
        height=800  # Keep or adjust height as needed
    )

    # Conditional chart: Time series if a symbol is selected
    bottom_chart = bottom_base.transform_filter(
        selection
    )

    # Combine the charts vertically
    dashboard = alt.vconcat(top_chart, bottom_chart).resolve_legend(
        color="independent",
        size="independent" # size resolution is still needed due to the previous bubble chart code
    )

    st.altair_chart(dashboard, use_container_width=True)