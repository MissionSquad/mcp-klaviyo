from klaviyo_mcp_server.utils.generate_model_from_oas import model_generator

ProfilePatchProperties = model_generator.generate_from_schema_name(
    "ProfileMetaPatchProperties"
)
Profile = model_generator.generate_from_schema_name(
    "ProfileCreateQueryResourceObject", "properties", "attributes"
)


class ProfileUpdate(Profile):
    anonymous_id: str | None = None
