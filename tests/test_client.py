import pytest

from redcap_mcp.client import RedcapClient
from redcap_mcp.errors import ApiError
from redcap_mcp.models import Profile


class Response:
    def __init__(self, status_code, text="", location=None):
        self.status_code = status_code
        self.text = text
        self.headers = {} if location is None else {"location": location}


class RedirectingClient:
    def __init__(self, destination):
        self.destination = destination
        self.urls = []

    async def post(self, url, **kwargs):
        self.urls.append(url)
        if len(self.urls) == 1:
            return Response(301, location=self.destination)
        return Response(200, "field_name,field_label\nage,Age\n")


@pytest.mark.asyncio
async def test_same_origin_redirect_is_followed_with_post_body():
    client = RedirectingClient("/redcap/api/")
    api = RedcapClient(Profile("safe", "https://redcap.example.edu/redcap/api"), "secret", client)
    rows = await api.export("metadata")
    assert rows == [{"field_name": "age", "field_label": "Age"}]
    assert client.urls == [
        "https://redcap.example.edu/redcap/api",
        "https://redcap.example.edu/redcap/api/",
    ]


@pytest.mark.asyncio
async def test_cross_origin_redirect_is_rejected_before_second_request():
    client = RedirectingClient("https://other.example/api/")
    api = RedcapClient(Profile("safe", "https://redcap.example.edu/redcap/api/"), "secret", client)
    with pytest.raises(ApiError, match="different origin"):
        await api.export("metadata")
    assert len(client.urls) == 1
