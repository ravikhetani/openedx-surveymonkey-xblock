"""
This Xblock allows to embed a survey link in a unit course.
If the mode track-able is selected, the user anonymous id will be sent as a query parameter
"""

import pkg_resources

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from oauthlib.oauth2 import InvalidClientError
from webob.response import Response
from web_fragments.fragment import Fragment

from xblock.core import XBlock
from xblock.fields import Scope, String, Boolean, Float
from xblockutils.resources import ResourceLoader
from xblockutils.studio_editable import StudioEditableXBlockMixin
from xblock.validation import ValidationMessage

from courseware.courses import get_course_by_id
from branding import api as branding_api
from microsite_configuration import microsite

from api_surveymonkey import ApiSurveyMonkey

LOADER = ResourceLoader(__name__)


class SurveyMonkeyXBlock(XBlock, StudioEditableXBlockMixin):
    """
    This XBlock allows to redirect to an external survey with the anonymous user id as query parameters
    """

    display_name = String(
        display_name=_("Display Name"),
        help=_("Enter the name that students see for this component."),
        scope=Scope.settings,
        default=_("SurveyMonkey")
    )

    survey_link = String(
        scope=Scope.settings,
    )

    text_link = String(
        display_name=_("Text Link"),
        help=_("Enter the text that will be shown instead of the url."),
        default=_("Complete the Survey"),
        scope=Scope.settings,
    )

    introductory_text = String(
        display_name=_("Introductory Text"),
        scope=Scope.settings,
        help=_("This contains an introductory text which is displayed to the student above the survey link."),
        default="",
        multiline_editor="html",
        resettable_editor=False
    )

    trackable = Boolean(
        display_name=_("User Tracking"),
        help=_("Make true if you want to track the survey using the user_id."),
        scope=Scope.settings,
        default=False
    )

    client_id = String(
        display_name=_("Client ID"),
        help=_("Your public identifier for your surveymonkey app"),
        default=None,
        scope=Scope.settings,
    )

    client_secret = String(
        display_name=_("Client Secret"),
        help=_("It is a secret known only to the application and the authorization server."),
        default=None,
        scope=Scope.settings,
    )

    survey_name = String(
        display_name=_("SurveyMonkey Name"),
        help=_("Enter the survey name."),
        scope=Scope.settings,
    )

    weight = Float(
        display_name=_("Score"),
        help=_("Defines the number of points each problem is worth. "),
        values={"min": 0, "step": .1},
        default=1,
        scope=Scope.settings
    )

    collector_id = String(
        scope=Scope.settings,
    )

    completed_survey = Boolean(
        scope=Scope.user_state,
        default=False,
    )

    has_score = True
    api_survey_monkey = None

    # Possible editable fields
    editable_fields = (
        "display_name",
        "survey_name",
        "text_link",
        "trackable",
        "introductory_text",
        "weight",
        "client_id",
        "client_secret",
    )

    def validate_field_data(self, validation, data):
        try:
            api_survey_monkey = ApiSurveyMonkey(data.client_id, data.client_secret)
        except InvalidClientError:
            validation.add(ValidationMessage(ValidationMessage.ERROR, u"Invalid client id or client secret"))
            return

        self._validate_survey_name(validation, data, api_survey_monkey)

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    # TO-DO: change this view to display your data your own way.
    def student_view(self, context=None):
        """
        The primary view of the SurveyMonkeyXBlock, shown to students
        when viewing courses.
        """
        frag = Fragment(LOADER.render_template("static/html/surveymonkey.html", self.context))
        frag.add_css(self.resource_string("static/css/surveymonkey.css"))
        frag.add_javascript(self.resource_string("static/js/src/surveymonkey.js"))
        frag.initialize_js('SurveyMonkeyXBlock')
        return frag

    def studio_view(self, context=None):
        """  Returns edit studio view fragment """
        context = {
            "completion_page": self.completion_page,
        }
        frag = super(SurveyMonkeyXBlock, self).studio_view(context)
        frag.add_content(LOADER.render_template("static/html/surveymonkeystudio.html", context))
        frag.add_javascript(self.resource_string("static/js/src/studio_view.js"))
        frag.initialize_js('StudioViewEdit')
        return frag

    @property
    def completion_page(self):
        base = microsite.get_value_for_org(
            self.course_id.org,
            "SITE_NAME",
            settings.LMS_ROOT_URL,
        )
        return "{}/{}/{}#{}".format(base, "xblock", self.location, "completion")

    @property
    def context(self):

        link = self.survey_link

        if self.trackable:
            link = "{}?uid={}".format(link, self.runtime.anonymous_student_id)

        context = {
            "title": self.display_name,
            "introductory_text": self.introductory_text,
            "text_link": self.text_link,
            "survey_link": link,
            "completed_survey": self.verify_completion(),
        }

        if hasattr(self.xmodule_runtime, 'is_author_mode'):
            return context

        context.update({
            "logo": branding_api.get_logo_url(False),
            "course": get_course_by_id(self.course_id),
            "footer": branding_api.get_footer(False),
            "completion_page": self.completion_page,
        })

        return context

    def _validate_survey_name(self, validation, data, api_surveymonkey):
        """
        This method searches survey list by survey title and sets a message if the survey is not unique
        """
        kwargs = {"title": data.survey_name}
        response = api_surveymonkey.get_surveys(**kwargs)
        data_response = response.get("data", [])

        filtered_data = [survey for survey in data_response if survey["title"] == data.survey_name]
        count = len(filtered_data)

        if not count:
            validation.add(ValidationMessage(ValidationMessage.ERROR, u"Invalid survey name, the survey doesn't exist"))
            return
        elif count > 1:
            validation.add(ValidationMessage(
                ValidationMessage.ERROR, u"Invalid survey name, there are two or more surveys with the same name"
            ))
            return

        collectors = api_surveymonkey.get_collectors(filtered_data[0].get("id"), **{"include": "url,type"})
        data_collectors = collectors.get("data")

        if not len(data_collectors):
            validation.add(ValidationMessage(
                ValidationMessage.ERROR, u"The survey must have at least one defined collector"
            ))
            return
        for data_collector in data_collectors:
            if data_collector.get("type") == "weblink":
                self.survey_link = data_collector.get("url")
                self.collector_id = data_collector.get("id")
                return

        validation.add(ValidationMessage(
            ValidationMessage.ERROR, u"The survey must have at least one weblink defined collector"
        ))

    @property
    def _api_survey_monkey(self):

        if self.api_survey_monkey is not None:
            return self.api_survey_monkey
        try:
            self.api_survey_monkey = ApiSurveyMonkey(self.client_id, self.client_secret)
            return self.api_survey_monkey

        except InvalidClientError:
            return None

    def _get_collector_reponses(self):

        return self._api_survey_monkey.get_collector_responses(self.collector_id).get("data")

    def verify_completion(self):
        if not self.completed_survey:
            responses = self._get_collector_reponses()
            uid = self.runtime.anonymous_student_id
            for response in responses:
                custom_variables = response.get("custom_variables", {})
                if custom_variables.get("uid") == uid:
                    self.completed_survey = True
                    self.runtime.publish(self, 'grade', {'value': self.weight, 'max_value': self.weight})

        return self.completed_survey

    def max_score(self):
        return self.weight
