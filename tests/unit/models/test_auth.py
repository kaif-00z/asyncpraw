"""Test asyncpraw.models.auth."""
import pytest

from asyncpraw import Reddit
from asyncpraw.exceptions import ClientException

from .. import UnitTest


class TestAuth(UnitTest):
    @pytest.fixture
    async def installed_app(self):
        async with Reddit(
            client_id="dummy client",
            client_secret=None,
            redirect_uri="https://dummy.tld/",
            user_agent="dummy",
        ) as reddit:
            yield reddit

    @pytest.fixture
    async def script_app(self):
        async with Reddit(
            client_id="dummy client",
            client_secret="dummy secret",
            redirect_uri="https://dummy.tld/",
            user_agent="dummy",
        ) as reddit:
            yield reddit

    @pytest.fixture
    async def script_app_with_password(self):
        async with Reddit(
            client_id="dummy client",
            client_secret="dummy secret",
            password="dummy password",
            user_agent="dummy",
            username="dummy username",
        ) as reddit:
            yield reddit

    @pytest.fixture
    async def web_app(self):
        async with Reddit(
            client_id="dummy client",
            client_secret="dummy secret",
            redirect_uri="https://dummy.tld/",
            user_agent="dummy",
        ) as reddit:
            yield reddit

    def test_implicit__from_script_app(self, script_app_with_password, script_app):
        with pytest.raises(ClientException):
            script_app.auth.implicit("dummy token", 10, "")
        with pytest.raises(ClientException):
            script_app_with_password.auth.implicit("dummy token", 10, "")

    def test_implicit__from_web_app(self, web_app):
        with pytest.raises(ClientException):
            web_app.auth.implicit("dummy token", 10, "")

    def test_limits(self, web_app, script_app_with_password, script_app, installed_app):
        expected = {"remaining": None, "reset_timestamp": None, "used": None}
        for app in [
            installed_app,
            script_app,
            script_app_with_password,
            web_app,
        ]:
            assert expected == app.auth.limits

    async def test_url__installed_app(self, installed_app):
        url = installed_app.auth.url(["dummy scope"], "dummy state")
        assert "client_id=dummy+client" in url
        assert "duration=permanent" in url
        assert "redirect_uri=https://dummy.tld/" in url
        assert "response_type=code" in url
        assert "scope=dummy+scope" in url
        assert "state=dummy+state" in url

    async def test_url__installed_app__implicit(self, installed_app):
        url = installed_app.auth.url(["dummy scope"], "dummy state", implicit=True)
        assert "client_id=dummy+client" in url
        assert "duration=temporary" in url
        assert "redirect_uri=https://dummy.tld/" in url
        assert "response_type=token" in url
        assert "scope=dummy+scope" in url
        assert "state=dummy+state" in url

    def test_url__web_app(self, web_app):
        url = web_app.auth.url(["dummy scope"], "dummy state")
        assert "client_id=dummy+client" in url
        assert "secret" not in url
        assert "redirect_uri=https://dummy.tld/" in url
        assert "response_type=code" in url
        assert "scope=dummy+scope" in url
        assert "state=dummy+state" in url

    def test_url__web_app__implicit(self, web_app):
        with pytest.raises(ClientException):
            web_app.auth.url(["dummy scope"], "dummy state", implicit=True)

    async def test_url__web_app_without_redirect_uri(self):
        async with Reddit(
            client_id="dummy client",
            client_secret="dummy secret",
            user_agent="dummy",
        ) as reddit:
            with pytest.raises(ClientException):
                reddit.auth.url(["dummy scope"], "dummy state")
