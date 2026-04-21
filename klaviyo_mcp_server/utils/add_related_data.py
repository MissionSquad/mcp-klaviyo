from klaviyo_mcp_server.utils.utils import clean_result


def add_related_data(
    response_data: dict, related_item_type: str, relation_descriptor: str
) -> None:
    """Moves data about related items from the "included" field to the entries they are related to."""

    response_items = response_data["data"]
    if not isinstance(response_items, list):
        response_items = [response_items]

    # collect map of related item ID -> data
    related_item_id_to_data = {}
    new_included = []
    for included_entry in response_data["included"]:
        if included_entry["type"] == related_item_type:
            clean_result(included_entry)
            related_item_id_to_data[included_entry["id"]] = included_entry
        else:
            new_included.append(included_entry)

    # clear out included data from the "included" list
    response_data["included"] = new_included
    if not response_data["included"]:
        del response_data["included"]

    # fill in data for each response item
    for item in response_items:
        related_metadata = item["relationships"][relation_descriptor]["data"]
        if isinstance(related_metadata, list):
            item[relation_descriptor] = [
                related_item_id_to_data[related_item_data["id"]]
                for related_item_data in related_metadata
            ]
        else:
            item[relation_descriptor] = related_item_id_to_data[related_metadata["id"]]
