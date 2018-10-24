"""
This Api class allows to authenticate and make request to the surveymonkey API_BASE
"""
import logging
import requests

from django.core.cache import cache
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient

LOG = logging.getLogger(__name__)
API_BASE = "https://api.surveymonkey.com"
CACHE_TIMEOUT = 86400


class ApiSurveyMonkey(object):
    """
    Class with the necessary methods to make request to surveymonkey API_BASE
    """
    def __init__(self, client_id, client_secret):
        self.session = requests.Session()

        key = "{}-{}".format("api_survey_monkey", client_id)
        headers = cache.get(key)

        if headers is None:
            headers = self.authenticate(client_id, client_secret)
            cache.set(key, headers, CACHE_TIMEOUT)

        self.session.headers.update(headers)

    def authenticate(self, client_id, client_secret):

        client = BackendApplicationClient(client_id=client_id)
        oauth = OAuth2Session(client=client)
        authenticate_url = "{}/{}".format(API_BASE, "oauth/token")
        headers = {}

        token = oauth.fetch_token(
            token_url=authenticate_url,
            client_id=client_id,
            client_secret=client_secret
        )

        headers["Authorization"] = "{} {}".format("Bearer", token.get("access_token"))
        return headers

    def __call_api_post(self, url, data):
        response = self.session.post(url=url, json=data)
        LOG.info("Surveymonkey post response with status code = %s", response.status_code)
        return response

    def __call_api_get(self, url, payload):
        response = self.session.get(url=url, params=payload)
        LOG.info("Surveymonkey get response with status code = %s", response.status_code)
        return response

    def get_collector_responses(self, collector_id, **kwargs):
        """
        Returns a list of responses.
        """
        url = "{}/{}/{}/{}".format(
            API_BASE,
            "v3/collectors",
            collector_id,
            "responses/bulk"
        )
        response = self.__call_api_get(url, kwargs)

        if response.status_code == 200:
            return response.json()

        LOG.error("An error has ocurred trying to get collector responses = %s", response.status_code)
        return {}

    def get_surveys(self, **kwargs):
        """
        Search survey list
        """
        url = "{}/{}".format(
            API_BASE,
            "v3/surveys",
        )
        response = self.__call_api_get(url, kwargs)

        if response.status_code == 200:
            return response.json()

        LOG.error("An error has ocurred trying to get surveys = %s", response.status_code)
        return {}

    def get_collectors(self, survey_id, **kwargs):
        """
        Search survey list
        """
        url = "{}/{}/{}/{}".format(
            API_BASE,
            "v3/surveys",
            survey_id,
            "collectors"
        )
        response = self.__call_api_get(url, kwargs)

        if response.status_code == 200:
            return response.json()

        LOG.error("An error has ocurred trying to get surveys = %s", response.status_code)
        return {}
