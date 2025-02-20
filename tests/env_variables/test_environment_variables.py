import os
import pytest
import requests

HUGGING_FACE_API_URL = "https://huggingface.co/api/whoami"
GITHUB_API_URL = "https://api.github.com/user"

do_not_run_in_debug = lambda: os.getenv("FLASK_DEBUG") == "1"


class TestEnvironmentVariables:
    """Tests for expiring environment variables."""

    @pytest.mark.xfail(
        condition=do_not_run_in_debug,
        reason="Skipping in debug mode",
        run=False,
    )
    def test_hugging_face_token(self):
        """Test if HUGGING_FACE_TOKEN is valid by querying Hugging Face API."""

        token = os.getenv("HUGGING_FACE_TOKEN")
        assert token is not None, "HUGGING_FACE_TOKEN is not set"

        token_validation_response = requests.get(
            HUGGING_FACE_API_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )

        assert (
            token_validation_response.status_code == 200
        ), f"Invalid HUGGING_FACE_TOKEN: {token_validation_response.text}"

    @pytest.mark.xfail(
        condition=do_not_run_in_debug,
        reason="Skipping in debug mode",
        run=False,
    )
    def test_github_microdata_auth_token(self):
        """Test if POLICYENGINE_GITHUB_MICRODATA_AUTH_TOKEN is valid by querying GitHub user API."""

        token = os.getenv("POLICYENGINE_GITHUB_MICRODATA_AUTH_TOKEN")
        assert (
            token is not None
        ), "POLICYENGINE_GITHUB_MICRODATA_AUTH_TOKEN is not set"

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        token_validation_response = requests.get(
            GITHUB_API_URL,
            eaders=headers,
            timeout=5,
        )

        assert (
            token_validation_response.status_code == 200
        ), f"Invalid POLICYENGINE_GITHUB_MICRODATA_AUTH_TOKEN: {token_validation_response.text}"

        token_user_details = token_validation_response.json()
        assert (
            "login" in token_user_details
        ), "Token is valid but did not return expected user details"
