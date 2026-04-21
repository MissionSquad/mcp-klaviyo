from klaviyo_mcp_server.utils.generate_model_from_oas import model_generator

TrackingOptions = model_generator.generate_from_schema_name(
    "CampaignCreateQueryResourceObject",
    "properties",
    "attributes",
    "properties",
    "tracking_options",
)
SendStrategy = model_generator.generate_from_schema_name(
    "CampaignCreateQueryResourceObject",
    "properties",
    "attributes",
    "properties",
    "send_strategy",
)
CampaignMessage = model_generator.generate_from_schema_name(
    "CampaignMessageCreateQueryResourceObject",
    "properties",
    "attributes",
    "properties",
    "definition",
)
