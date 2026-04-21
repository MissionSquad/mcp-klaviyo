from typing import List, Callable, Optional, Dict, Tuple, Any
from types import SimpleNamespace
from collections import defaultdict
from functools import partial
from datetime import datetime

from klaviyo_mcp_server.utils.param_types import BaseFilter
from klaviyo_mcp_server.utils.utils import (
    get_klaviyo_client,
    get_filter_string,
    clean_result,
)


FLOW_FIELDS = ["name", "status", "trigger_type"]
# KEEP SEND TIME AND AUDIENCES
CAMPAIGN_FIELDS = ["name", "status", "audiences", "send_time"]


def get_id_to_tag_name(included: dict) -> dict:
    """
    Get a relationship dict, return a dict of id to tag name
    """
    tag_names = {
        item["id"]: item["attributes"]["name"]
        for item in included
        if item["type"] == "tag" and "name" in item["attributes"]
    }

    return tag_names


class AudienceDetails:
    """
    Class to get the name of an audience from an audience ID.
    """

    def __init__(self):
        self.audience_id_to_details = defaultdict(type(None))
        self.client = get_klaviyo_client()

    def get_audience_details(self, audience_id: str) -> dict:
        """
        Returns a dict with the name and type of the audience.

        Args:
            audience_id: The ID of the audience to get the name of

        Returns:
            {id: {name: str, type: str}}
        """

        if audience_id not in self.audience_id_to_details:
            # Try to get the name of the list or segment
            self.audience_id_to_details[audience_id] = {
                "name": self._get_list_name(audience_id),
                "type": "list",
            }
            if self.audience_id_to_details[audience_id]["name"] is None:
                self.audience_id_to_details[audience_id] = {
                    "name": self._get_segment_name(audience_id),
                    "type": "segment",
                }

            # If we still don't have a name, set the output to None
            if self.audience_id_to_details[audience_id]["name"] is None:
                self.audience_id_to_details[audience_id] = None

        # None if no name found
        return self.audience_id_to_details[audience_id]

    def _get_list_name(self, list_id: str) -> str:
        try:
            response = self.client.Lists.get_list(list_id, fields_list=["name"])
            return response["data"]["attributes"]["name"]
        except Exception:
            return None

    def _get_segment_name(self, segment_id: str) -> str:
        try:
            response = self.client.Segments.get_segment(
                segment_id, fields_segment=["name"]
            )
            return response["data"]["attributes"]["name"]
        except Exception:
            return None


def batch_request(
    ids: List[str], request: Callable, extra_filters: list[SimpleNamespace] = None
):
    """
    Given a list of IDs, returns a dictionary that maps IDs to data, using the given function to request data for a batch of IDs.
    Processes in batches of 50 IDs sequentially.

    Args:
        ids: List of IDs to get details for
        request: Callable function that takes a filter parameter and returns the API response.
                Should be a partial of a Klaviyo API method with all other parameters pre-filled.
        extra_filters: List of SimpleNamespace objects that represent extra filters to apply to the request.

    Returns:
        {id: campaign or flow object}
    """
    if not extra_filters:
        extra_filters = []

    items = defaultdict(type(None))
    batch_size = 50

    # Process batches of 50 unique IDs sequentially
    unique_ids = list(set(ids))
    for i in range(0, len(unique_ids), batch_size):
        batch_ids = unique_ids[i : i + batch_size]

        # Create filter with format: any(id,['id1','id2','id3'])
        batch_id_filter = SimpleNamespace(
            field="id",
            operator="any",
            value=batch_ids,
        )
        # Make request with filter and extra filters
        batch_response = request(
            filter=get_filter_string([batch_id_filter] + extra_filters)
        )

        # Get id to tag name
        id_to_tag_name = get_id_to_tag_name(batch_response["included"])

        if batch_response.get("data", None):
            # Add results to items dict
            for item in batch_response["data"]:
                item["attributes"]["tags"] = []
                # Assign tag names to item
                for tag in item["relationships"]["tags"]["data"]:
                    item["attributes"]["tags"].append(id_to_tag_name[tag["id"]])

                # Remove relationships and links
                clean_result(item)
                items[item["id"]] = item

    # Return results in the same order as input IDs
    return items


def get_flow_details(flow_ids: List[str]):
    """
    Use the get_flows endpoint to get flow details from a list of flow_ids.
    Processes batches of 50 IDs sequentially.

    Args:
        flow_ids: List of flow IDs to get details for

    Returns:
        {id: flow object}
    """
    client = get_klaviyo_client()

    flow_request = partial(
        client.Flows.get_flows,
        include=["tags"],
        fields_flow=FLOW_FIELDS,
        fields_tag=["name"],
    )

    return batch_request(flow_ids, flow_request)


def get_campaign_details(channel_to_campaign_ids: dict[str, List[str]]):
    """
    Use the get_campaigns endpoint to get campaign details from a list of campaign_ids.
    Processes batches of 50 IDs sequentially.

    Args:
        channel_to_campaign_ids: dict of channel to list of campaign IDs to get details for

    Returns:
        {id: campaign object}
    """
    client = get_klaviyo_client()

    results = defaultdict(type(None))
    audience_id_to_details = AudienceDetails()
    for channel, ids in channel_to_campaign_ids.items():
        channel_filter = SimpleNamespace(
            field="messages.channel", operator="equals", value=channel
        )

        campaign_request = partial(
            client.Campaigns.get_campaigns,
            include=["tags"],
            fields_campaign=CAMPAIGN_FIELDS,
            fields_tag=["name"],
        )

        batch_results = batch_request(
            ids, campaign_request, extra_filters=[channel_filter]
        )

        # Add audience details and send time formatting to returned campaigns
        for campaign in batch_results.values():
            # Change send_time to year, month, day, hour, minute
            if campaign["attributes"].get("send_time", None):
                send_time = datetime.fromisoformat(campaign["attributes"]["send_time"])
                campaign["attributes"]["send_time"] = send_time.strftime(
                    "%Y %d %B %H:%M"
                )

            # Add audience details to item if it exists
            if campaign.get("attributes", {}).get("audiences", {}):
                # Add audience details to included audiences
                campaign["attributes"]["audiences"]["included"] = [
                    audience_id_to_details.get_audience_details(audience_id)
                    for audience_id in campaign["attributes"]["audiences"]["included"]
                ]

                # Add audience details to excluded audiences
                campaign["attributes"]["audiences"]["excluded"] = [
                    audience_id_to_details.get_audience_details(audience_id)
                    for audience_id in campaign["attributes"]["audiences"]["excluded"]
                ]

        results.update(batch_results)

    return results


def matches_detail_filters(item: dict, detail_filters: list[BaseFilter]) -> bool:
    """
    Check if campaign or flow matches the detail filters.

    Args:
        item: Campaign or flow dictionary with attributes containing filterable fields
        detail_filters: List of filter objects with field, operator, and value attributes

    Returns:
        bool: True if item matches all filters, False otherwise

    Operators:
        - equals: Compares single value against single item (exact match)
        - contains-any: Checks if any filter value matches any item value (substring matching)

    All string comparisons are case-insensitive.
    """

    if not detail_filters:
        return True

    for filter_item in detail_filters:
        field = filter_item.field
        operator = filter_item.operator
        values = filter_item.value

        # If there is just one value it's a string, if multiple it's a list
        if isinstance(values, str):
            values = [values]

        item_attributes = item.get("attributes", {})
        keys = field.split(".")
        actual_values = get_value_recursive(item_attributes, keys)

        if not _check_filter_match(actual_values, operator, values):
            return False

    return True


def _check_filter_match(items: list, operator: str, values: list) -> bool:
    """
    Check if items match the filter condition (case-insensitive for strings).

    Args:
        items: List of strings from the campaign/flow data to check against
        operator: Filter operator ('equals' or 'contains-any')
        value: List of strings from the filter to match

    Returns:
        bool: True if filter condition is met, False otherwise

    Operator behavior:
        - equals: Compares single filter value against single item value (exact match)
                 Both items and value lists should contain exactly one element
        - contains-any: Checks if any filter value appears in any item value
                       Supports multiple values in both items and value lists

    All string comparisons are case-insensitive.
    """

    if not items:
        return False

    # Convert all strings to lowercase for case-insensitive comparison
    items = set([item.lower() if isinstance(item, str) else item for item in items])
    values = set(
        [value.lower() if isinstance(value, str) else value for value in values]
    )

    if operator == "equals":
        # exact match, no substring matching
        return items == values
    elif operator == "contains-any":
        # contains-any: Any filter value matches any item value (substring matching)
        # Supports multiple values in both items and value lists
        return any(any(val in item for val in values) for item in items)

    return False


def get_value_recursive(data: dict | list, dict_key_path: list) -> list:
    """Get nested values from a dict or list, based on the given path."""
    if isinstance(data, list):
        return [
            result
            for child in data
            for result in get_value_recursive(child, dict_key_path)
        ]
    if not dict_key_path:
        return [data]
    [key, *remaining_keys] = dict_key_path
    if key not in data:
        return []
    return get_value_recursive(data.get(key), remaining_keys)


def normalize_audience_value(val) -> Optional[str]:
    """Normalize audience value to a string, filtering out None, empty, and null values."""
    if not (val or "").strip():
        return None
    return val


def audience_label_from_included(included: list) -> str:
    """Build the audience label from included audiences preserving order and duplicates."""
    names = []
    for item in included or []:
        name = item.get("name") if isinstance(item, dict) else None
        normalized_name = normalize_audience_value(name)
        if normalized_name is None:
            continue
        names.append(normalized_name)

    if not names:
        # If we don't find any audiences, we will return "No Audience Specified". This includes null audiences.
        return "No Audience Specified"
    sorted_names = sorted(names)
    return " + ".join(sorted_names)


def round_rate(val: Optional[float]) -> Optional[float]:
    """Round rate to 2 decimal places, handling None values."""
    if val is None:
        return None
    return round(val, 2)


def aggregate_results_by_audience(
    campaigns: List[dict],
    include_values: bool,
) -> List[Dict[str, Any]]:
    """Aggregate campaign/flow results by audience and send channel."""
    grouped: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(
        lambda: defaultdict(lambda: 0)  # initialize the bucket with 0 for each key
    )

    # Iterate through the results and add the stats to the grouped bucket.
    for campaign in campaigns:
        stats = campaign.get("statistics", {}) or {}
        send_channel = campaign.get("groupings", {}).get("send_channel", "unknown")

        campaign_details = campaign.get("campaign_details") or {}
        attributes = campaign_details.get("attributes", {}) or {}
        audiences = (attributes.get("audiences", {}) or {}).get("included", []) or []
        label = audience_label_from_included(audiences)

        # Get the bucket for the current label and send channel
        key = (label, send_channel)
        bucket = grouped[key]

        # Add the stats to the bucket
        bucket["recipients"] += stats.get("recipients", 0)
        bucket["delivered"] += stats.get("delivered", 0)
        bucket["opens_unique"] += stats.get("opens_unique", 0)
        bucket["clicks_unique"] += stats.get("clicks_unique", 0)
        bucket["unsubscribes"] += stats.get("unsubscribes", 0)
        bucket["spam_complaints"] += stats.get("spam_complaints", 0)
        bucket["conversions"] += stats.get("conversions", 0)

        if include_values:
            bucket["conversion_value"] += float(stats.get("conversion_value", 0.0))

    rows = []
    # Iterate through the grouped bucket and compute the rates.
    for (label, send_channel), sums in grouped.items():
        recipients = sums["recipients"]

        # Compute standard rates directly from totals.
        def _compute_rate(key: str) -> Optional[float]:
            if not recipients or recipients <= 0:
                return None
            return round_rate((sums.get(key, 0) / recipients) * 100.0)

        row = {
            "audience": label,
            "send_channel": send_channel,
            "recipients": recipients,
            "delivered": sums["delivered"],
            "opens_unique": sums["opens_unique"],
            "clicks_unique": sums["clicks_unique"],
            "unsubscribes": sums["unsubscribes"],
            "spam_complaints": sums["spam_complaints"],
            "conversions": sums["conversions"],
            "open_rate": _compute_rate("opens_unique"),
            "click_rate": _compute_rate("clicks_unique"),
            "unsubscribe_rate": _compute_rate("unsubscribes"),
            "spam_complaint_rate": _compute_rate("spam_complaints"),
            "conversion_rate": _compute_rate("conversions"),
            "delivery_rate": _compute_rate("delivered"),
        }
        if include_values:
            row["conversion_value"] = round(sums["conversion_value"], 2)
        rows.append(row)

    rows.sort(key=lambda r: r["audience"].lower(), reverse=True)
    return rows
