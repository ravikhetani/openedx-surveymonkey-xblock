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
SURVEY_MONKEY_API_TAG = "api_survey_monkey"


class ApiSurveyMonkey(object):
    """
    Class with the necessary methods to make request to surveymonkey API_BASE
    """
    def __init__(self, client_id, client_secret, cache_duration):
        self.session = requests.Session()
        self.client_id = client_id
        self.surveymonkey_api_cache_duration = cache_duration

        key = "{}-{}-{}".format(SURVEY_MONKEY_API_TAG, client_id, client_secret)
        headers = cache.get(key)

        if not headers:
            headers = self.authenticate(client_id, client_secret)
            cache.set(key, headers, cache_duration)

        self.session.headers.update(headers)

    def authenticate(self, client_id, client_secret):
        """
        This method return a dict with the authorization token
        """
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
        """
        This uses the session to make a POST request and returns the response
        """
        response = self.session.post(url=url, json=data)
        LOG.info("Surveymonkey post response with status code = %s %s", response.status_code, url)
        return response

    def __call_api_get(self, url, payload):
        """
        This uses the session to make a GET request and return the response
        """
        response = self.session.get(url=url, params=payload)
        LOG.info("Surveymonkey get response with status code = %s %s", response.status_code, url)
        return response

    def __call_api_patch(self, url, payload):
        """
        This uses the session to make a PATCH request and return the response.
        """
        response = self.session.patch(url=url, json=payload)

        LOG.info("Surveymonkey PATCH response with status code = %s %s", response.status_code, url)

        return response

    def get_collector_responses(self, collector_id, **kwargs):
        """
        Retrieves a list of full expanded responses, including answers to all questions.
        """
        url = "{}/{}/{}/{}".format(
            API_BASE,
            "v3/collectors",
            collector_id,
            "responses/bulk"
        )
        response = self.__call_api_get(url, kwargs)

        # TODO add support for next pages.
        if response.status_code == 200:
            return response.json()

        LOG.error("An error has ocurred trying to get collector responses = %s", response.status_code)
        return {}

    def get_surveys(self, **kwargs):
        """
        Returns a list of surveys owned or shared with the authenticated user.
        """
        cache_key = "{}-{}-{}".format(SURVEY_MONKEY_API_TAG, "all_surveys", self.client_id)
        all_surveys_data = cache.get(cache_key)

        if not self.surveymonkey_api_cache_duration:
            cache.delete(cache_key)
        elif all_surveys_data:
            return all_surveys_data

        url = "{}/{}".format(
            API_BASE,
            "v3/surveys",
        )
        response = self.__call_api_get(url, kwargs)

        # TODO add support for next pages.
        if response.status_code == 200:
            cache.set(cache_key, response.json(), self.surveymonkey_api_cache_duration)
            return response.json()

        LOG.error("An error has ocurred trying to get surveys = %s", response.status_code)
        return {}

    def get_collectors(self, survey_id, block_location_id, **kwargs):
        """
        Returns a list of collectors for a given survey.
        """
        cache_key = "{}-{}-{}-{}".format(SURVEY_MONKEY_API_TAG, "all_collectors", self.client_id, block_location_id)
        all_collectors_data = cache.get(cache_key)

        if not self.surveymonkey_api_cache_duration:
            cache.delete(cache_key)
        elif all_collectors_data:
            return all_collectors_data

        url = "{}/{}/{}/{}".format(
            API_BASE,
            "v3/surveys",
            survey_id,
            "collectors"
        )
        response = self.__call_api_get(url, kwargs)

        if response.status_code == 200:
            cache.set(cache_key, response.json(), self.surveymonkey_api_cache_duration)
            return response.json()

        LOG.error("An error has ocurred trying to get surveys = %s", response.status_code)
        return {}

    def get_survey_details(self, survey_id, block_location_id):
        """
        Returns the survey details for the given survey_id.

        Args:
            survey_id: SurveyMonkey survey id.
        Returns:
            response: requests.models.Response.json instance.
        """
        cache_key = "{}-{}-{}-{}".format(SURVEY_MONKEY_API_TAG, "survey_details", self.client_id, block_location_id)
        survey_details = cache.get(cache_key)

        if not self.surveymonkey_api_cache_duration:
            cache.delete(cache_key)
        elif survey_details:
            return survey_details

        url = "{}/v3/surveys/{}/details".format(
            API_BASE,
            survey_id,
        )
        response = self.__call_api_get(url, {})

        if response.status_code == 200:
            cache.set(cache_key, response.json(), self.surveymonkey_api_cache_duration)
            return response.json()

    def get_survey_responses(self, survey_id, **kwargs):
        """
        Returns the bulk survey responses for the given survey_id.

        Args:
            survey_id: SurveyMonkey survey id.
            kwargs: Request data.
        Returns:
            response: requests.models.Response.json instance.
        """
        url = "{}/v3/surveys/{}/responses/bulk".format(
            API_BASE,
            survey_id,
        )
        response = self.__call_api_get(url, kwargs)

        if response.status_code == 200:
            return response.json()

        LOG.error("An error has ocurred trying to GET the survey responses: %s", response.status_code)
        return {}

    def patch_question_data(self, survey_id, page_id, question_id, **kwargs):
        """
        Makes a PATCH request to update the question data.

        Args:
            survey_id: SurveyMonkey survey id.
            page_id: Page id of the survey.
            question_id: Id of the question to update.
            kwargs: Request data.
        Returns:
            response: requests.models.Response.json instance.
        """
        patch_url = "{}/v3/surveys/{}/pages/{}/questions/{}".format(
            API_BASE,
            survey_id,
            page_id,
            question_id,
        )

        response = self.__call_api_patch(patch_url, kwargs)

        if response.status_code == 200:
            return response.json()

        LOG.error("An error has ocurred trying to PATCH the question survey: %s", response.status_code)
        return {}
