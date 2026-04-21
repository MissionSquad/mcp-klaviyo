from typing import Annotated

from fastmcp.prompts.prompt import PromptMessage, TextContent
from klaviyo_mcp_server.server import mcp
from pydantic import Field


TIMEFRAME_FORMAT = """
## Available Timeframes:
    - Use these preset timeframe keys: last_90_days, last_30_days, last_7_days, last_365_days, last_12_months, last_3_months, last_month, last_week, last_year, this_month, this_week, this_year, today, yesterday.
    - CUSTOM TIMEFRAMES: If the user specifies a custom timeframe, use the format: {{"value": {{"start": "start_date", "end": "end_date"}}}}
"""

GENERAL_EMOJI_USAGE = """
- Use emojis in headers to make the output more engaging.
    - For positive metrics or insights, use emojis like 📈 or 🚀.
    - For negative metrics or insights, use emojis like 📉 or ⚠️.
    - Use emojis like 💡 for recommendations and insights.
    - Ensure emojis are contextually relevant and enhance readability.
"""


@mcp.prompt
def analyze_campaign_or_flow_anomalies(
    report_type: Annotated[
        str,
        Field(description="Report types include: [campaign, flow]"),
    ],
    timeframe: Annotated[str, Field(description="The timeframe to analyze")],
    refine_prompt: Annotated[
        str,
        Field(
            description="Ask for specific channels, tags, or other details for analysis"
        ),
    ] = "",
) -> PromptMessage:
    """Prompt for analyzing spikes, dips, and other anomalies in campaign or flow performance data."""

    return PromptMessage(
        role="user",
        content=TextContent(
            type="text",
            text=f"""You are a marketing analytics expert analyzing Klaviyo {report_type} performance data.

Analyze {report_type} data over the timeframe: {timeframe}.

{refine_prompt}

When analyzing {report_type} reports, follow this structured approach. If any prior information is unclear, ask the user for clarification.

IMPORTANT EXTRA DETAILS:

--------------------------------

# Important Details
- **ALWAYS** use {report_type} names in final output; IDs only for internal tool calls. This is crucial for understanding.
- Prioritize actionable insights over descriptive statistics
- Include the timeframe in the request always, prioritize using preset timeframes over custom timeframes if possible.
    - {TIMEFRAME_FORMAT}
- If possible, visualize the data in a chart or graph.
- Use emojis in headers to make the output more engaging

# Tool calls
- Start with get_metrics to identify available metrics for the timeframe
    - Apply channel filters (email/SMS) only when user specifies channel preference
- Use get_campaign_report_by_id to get the name for a specific campaign
- Use get_flow_report_by_id to get the name for a specific flow
- **Map {report_type} IDs to names**: After retrieving data, ensure that all {report_type} IDs are mapped to their corresponding names before presenting the analysis.

# Analysis Structure
## Header: {report_type} Performance Analysis for {timeframe}

## 1. Performance Overview
- Start with key metrics: delivery rate, open rate, click rate, conversion rate
- Look for rates or metrics from the {report_type}s which differ from the rest of the data substantially.
- Identify top 3 performers and bottom 3 performers with specific percentage differences

## 2. Event Analysis
- Identify spikes and dips in the data
- Provide a detailed analysis of the events that caused the spikes or drops, list the specific {report_type} names that experienced the spike or drop, and which metric was experiencing the spike or drop.
- Provide recommendations for optimizing the {report_type}s to address the drop or build on the spike
- Put it into larger context of the timeframe it is in

## 3. Conclusion
- Summarize the findings
- Provide recommendations for optimizing the data
""",
        ),
    )


@mcp.prompt
def compare_flow_performance(
    flow_id_or_name_1: Annotated[
        str, Field(description="The first flow ID or name to compare")
    ],
    flow_id_or_name_2: Annotated[
        str, Field(description="The second flow ID or name to compare")
    ],
    timeframe_1: Annotated[
        str,
        Field(
            description="The time period over which to compare the first flow (e.g., 'last_30_days', 'this_month', or a custom date range)"
        ),
    ],
    timeframe_2: Annotated[
        str,
        Field(
            description="The time period over which to compare the second flow (e.g., 'last_30_days', 'this_month', or a custom date range)"
        ),
    ],
    refine_prompt: Annotated[
        str,
        Field(
            description="Any user refinements or additional instructions for the analysis"
        ),
    ] = "",
) -> PromptMessage:
    """Prompt for comparing flow performance between two time periods."""

    return PromptMessage(
        role="user",
        content=TextContent(
            type="text",
            text=f"""
**Role:** You are a marketing analytics expert.
**Task:** Compare two Klaviyo flows, {flow_id_or_name_1} and {flow_id_or_name_2}, over these time periods: {timeframe_1} and {timeframe_2} respectively.
**Goal:** Identify the higher-performing flow, identify key metrics that differed and what about the flow may have caused these differences (e.g. trigger_type, messages, channels, etc.) and provide actionable recommendations based on the data.

1. **Analysis Steps:**
- If the user has entered a flow name, you will have to just call all flows that match this flow's type in the given timeframe, and then just use the first flow that matches the name.
- Call the get_flow_report tool for {flow_id_or_name_1} using the specified timeframe  {timeframe_1}.
- Call the get_flow_report tool for {flow_id_or_name_2} using the specified timeframe  {timeframe_2}.
- For key metrics (Open Rate, Click Rate, Placed Order Rate, Revenue Per Recipient), calculate the percentage difference between them. Use {flow_id_or_name_2} as the baseline for comparison: ((Flow 1 Value - Flow 2 Value) / Flow 2 Value) * 100.
- If {flow_id_or_name_2}'s value is 0, show "N/A" for the difference.

2. **Output Format:**
- Header: Create a main header like ## 🚀 Flow Comparison: {flow_id_or_name_1} vs. {flow_id_or_name_2}.
- Comparison Table: Present the data in a markdown table with these columns:
    - Metric
    - {flow_id_or_name_1}
    - {flow_id_or_name_2}
    - Difference (This column must show the % difference, indicating which flow performed better with an emoji like 📈 or 📉).
    - Key Insight: After the table, briefly state which flow was the overall top performer and in which key area.
- Summary: After the table, briefly state which flow was the overall top performer and in which key area.
- {GENERAL_EMOJI_USAGE}

3. **Recommendations:**
- Provide 1-2 concise recommendations based on the results:
- If 1 flow clearly outperforms the other: Recommend analyzing the winning flow's content, timing, and offers to apply its successful elements to the underperforming one.
- If performance is mixed (e.g., one has a better open rate, the other a better click rate): Highlight the specific strengths of each and suggest A/B testing to combine the best elements from both.
- If performance is very similar: Note that both are effective and suggest A/B testing minor variables (like subject lines) to seek further optimization.

**User Refinements:**
{refine_prompt}

""",
        ),
    )


@mcp.prompt
def analyze_metric_by_campaign_audience(
    timeframe: Annotated[str, Field(description="The timeframe to analyze")],
    metric_name: Annotated[str, Field(description="The metric to analyze")],
    audience_name: Annotated[
        str, Field(description="The audience to analyze, default all audiences")
    ] = "all audiences",
    refine_prompt: Annotated[
        str,
        Field(
            description="Ask for specific channels, tags, or other details for analysis"
        ),
    ] = "",
) -> PromptMessage:
    """Prompt for analyzing a metric by audience."""

    return PromptMessage(
        role="user",
        content=TextContent(
            type="text",
            text=f"""
**Role:** You are a marketing analytics expert.
Your mission is to analyze Klaviyo campaign performance by calculating a specific metric and grouping the results by the target audience, aggregated across all campaigns sent in the provided timeframe.

** Tasks:**
- ALWAYS use the deterministic server-side aggregation so you do NOT do math yourself.
- For campaigns sent within the {timeframe}, compute the {metric_name} and group results by audience using only the tool output.
- The analysis will focus on analyzing: {audience_name}.

**Required Tool Calls:**
1. Identify a conversion metric id using get_metrics:
    - For `{metric_name}`, try exact case-insensitive name match.
    - if there are multiple matches, Always generate the report for all of the matches.
    - If no exact match exists, select the newest available metric (do not prefer any specific metric).
    - If `{metric_name}` is not a conversion metric, still pass a valid conversion metric id (newest available is fine; required by the API).
2. Fetch data with server-side audience grouping using get_campaign_report for {timeframe}:
    - statistics: Include `recipients`, `delivered`, `opens_unique`, `clicks_unique`, `unsubscribes`, `spam_complaints`; include `conversions` when available.
    - value_statistics: If `{metric_name}` is a conversion metric, attempt `conversion_value`. If unsupported, retry without `value_statistics`.
    - filters: Do not filter by `send_channel` unless specified. Do not filter by `status` (not supported by this endpoint); the timeframe automatically scopes data and includes both "Sent" and "Sending" rows.
    - detail_filters: If the user specifies tags or audience filters, pass them (e.g., `audiences.included.name`, `tags`).
    - group_by_audience: true
    - metric_name: {metric_name}
3. Do NOT perform any math yourself. Use only `data.attributes.audience_aggregation.results` and the provided `rate_value`/`rate_name`.

**Validation / QA Checklist (MANDATORY):**
    - Confirm the table rows come from `audience_aggregation.results` and that every campaign contributes to exactly one combined audience label.
    - Verify recipients sums include all included campaigns for that audience label, including zero-conversion and "Sending" rows.
    - Show both `recipients` and `delivered` in the table.
    - Assert there is no row literally labeled `null`; null/empty names are rolled into "No Audience Specified" by the tool.
    - Do not recompute rates; use the tool's `rate_value` (already rounded to 2 decimals) and `rate_name`.

**Response Output Format:**
Generate a report with this format using the following structure:
    - Header: ## 📉 {metric_name} by Campaign Audience: {timeframe} - Generated: `add date and time generated`
    - Header: Results Table
        - Create a markdown table using ONLY `audience_aggregation.results`.
        - Name the conversion columns {metric_name} rate, {metric_name} count, and {metric_name} value.
        - Include: Audience, Send Channel, Recipients, Delivered, Opens Unique, Clicks Unique, Conversions, Unsubscribes, Spam Complaints, Open Rate (%), Click Rate (%), Conversion Rate (%), Unsubscribe Rate (%), Spam Rate (%).
        - Display counts as integers; rates are already rounded by the tool.
        - Keep both `recipients` and `delivered` columns.
        - Sort the results table by Audience (case-insensitive), descending.
        - If `{metric_name}` is a conversion metric, include the `conversion_value` column.
    - Header: Key Insight
        - Identify audiences with the highest and lowest `rate_value` from the tool output.
    - Header: Recommendations
        - Provide 1-2 concise recommendations based on outlier audiences:
        - High Negative Metric (e.g., Unsubscribe Rate): Suggest reviewing content/frequency for that audience and consider using send time optimization, A/B testing content, or creating suppression segments to exclude less engaged customers.
        - Low Positive Metric (e.g., Click Rate): Suggest running a re-engagement campaign for that disengaged audience or A/B testing subject lines/campaign content.
        - High Positive Metric (e.g., Click Rate): Suggest analyzing what makes this high-performing audience so successful and replicating those strategies or creating lookalike segments. Look for common themes in the campaigns where this audience showed high performance, to suggest strategies that may already be working best.
    - Header: Methodology
        - Briefly state the timeframe used, the metric used, and the audience used. If the audience is "all audiences", state that.
        - State that grouping and calculation were performed server-side via get_campaign_report with `group_by_audience=true`.
        - Briefly state any data that was excluded from the analysis.
        - Confirm the denominator used (recipients), confirm zero-conversion sends were included, and cite the conversion metric id used to query conversions for {metric_name}.
    - {GENERAL_EMOJI_USAGE}
**User Refinements:**
- {refine_prompt}
""",
        ),
    )
