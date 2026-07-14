class RedcapMcpError(Exception):
    """Safe error intended for presentation to an MCP client."""


class PrivacyError(RedcapMcpError):
    pass


class ConfigurationError(RedcapMcpError):
    pass


class ApiError(RedcapMcpError):
    pass
