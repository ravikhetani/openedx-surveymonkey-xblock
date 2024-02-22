"""
This Xblock allows to embed a survey link in a unit course.
If the mode track-able is selected, the user anonymous id will be sent as a query parameter
"""
import logging
import pkg_resources

from openedx.core.lib.courses import get_course_by_id
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from microsite_configuration import microsite
from oauthlib.oauth2 import InvalidClientError, InvalidClientIdError
from submissions import api as submissions_api
from web_fragments.fragment import Fragment
from webob.response import Response
from xblock.core import XBlock
from xblock.fields import Boolean, Float, Integer, Scope, String
from xblock.validation import ValidationMessage
from xblockutils.resources import ResourceLoader
from xblockutils.studio_editable import StudioEditableXBlockMixin

from .api_surveymonkey import ApiSurveyMonkey

LOG = logging.getLogger(__name__)
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

    completed_survey = Boolean(
        scope=Scope.user_state,
        default=False,
    )

    survey_id = String(
        scope=Scope.settings,
    )

    inline_survey_view = Boolean(
        display_name=_("Inline survey view"),
        help=_(
            """
            True if you want to show the survey as a course content,
            otherwise it will show the external link to the survey.
            """
        ),
        scope=Scope.settings,
        default=False,
    )

    is_for_external_course = Boolean(
        display_name=_("External course"),
        help=_(
            """
            True if the survey is for an external course.
            """
        ),
        scope=Scope.settings,
        default=False,
    )

    overwrite_survey_questions = Boolean(
        display_name=_("Overwrite survey questions."),
        help=_("""
            True if you want to overwrite the questions of the survey with the headings passed to Question headings setting.
        """),
        scope=Scope.settings,
        default=False
    )

    previous_survey_name = String(
        display_name=_("Previous survey name."),
        help=_("The previous survey name to recap the responses."),
        default=None,
        scope=Scope.settings,
    )

    previous_survey_id = String(
        scope=Scope.settings,
    )

    default_overwritten_question_headings_text = """SurveyMonkey question heading one.\r\n
        SurveyMonkey question heading two.\r\n
        Split every question in a new line.\r\n
        If you want to recap the user's response from a previous survey,\r\n
        just add the heading of the question you want to recap embraced by {question to recap}.\r\n"""

    overwritten_question_headings = String(
        display_name=_("Question headings."),
        scope=Scope.settings,
        help=_("Write the questions to overwrite the headings of the SurveyMonkey questions."),
        default=default_overwritten_question_headings_text,
        multiline_editor="text",
        resettable_editor=True,
    )

    surveymonkey_api_cache_duration = Integer(
        display_name=_("SurveyMonkey API cache duration."),
        help=_("""
            Specify the time in seconds to caching the results of the SurveyMonkey API.
            If you set to 0 the cache will be deleted and you could reach the maximun SurveyMonkey API calls.
            Use it if you want to reset the cache in case you made any changes to the survey in SurveyMonkey.
        """),
        scope=Scope.settings,
        default=86400,
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
        "inline_survey_view",
        "is_for_external_course",
        "overwrite_survey_questions",
        "previous_survey_name",
        "overwritten_question_headings",
        "surveymonkey_api_cache_duration",
    )

    def validate_field_data(self, validation, data):
        try:
            api_survey_monkey = ApiSurveyMonkey(
                data.client_id,
                data.client_secret,
                data.surveymonkey_api_cache_duration,
            )
        except InvalidClientError:
            validation.add(ValidationMessage(ValidationMessage.ERROR, u"Invalid client id or client secret"))
            return

        self.survey_id = self._validate_survey_name(validation, data.survey_name, api_survey_monkey)

        if not self.survey_id:
            return None

        self._get_survey_link(self.survey_id, validation, api_survey_monkey)

        if data.overwrite_survey_questions:
            self.previous_survey_id = self._validate_survey_name(validation, data.previous_survey_name, api_survey_monkey)

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
        frag.initialize_js(
            'SurveyMonkeyXBlock',
            json_args={
                "is_for_external_course": self.is_for_external_course,
            },
        )
        return frag

    def studio_view(self, context=None):
        """  Returns edit studio view fragment """
        context = {
            "completion_page": self.get_handler_url("completion"),
            "confirmation_page": self.get_handler_url("confirmation"),
        }
        frag = super(SurveyMonkeyXBlock, self).studio_view(context)
        frag.add_content(LOADER.render_template("static/html/surveymonkeystudio.html", context))
        frag.add_javascript(self.resource_string("static/js/src/studio_view.js"))
        frag.initialize_js('StudioViewEdit')
        return frag

    def get_handler_url(self, handler_name):
        base = microsite.get_value_for_org(
            self.course_id.org,
            "LMS_ROOT_URL",
            settings.LMS_ROOT_URL,
        )

        if base.endswith("/"):
            base = base[:-1]

        return "{base}/courses/{course_key}/xblock/{usage_key}/handler/{handler_name}".format(
            base=base,
            course_key=self.course_id,
            usage_key=self.location,
            handler_name=handler_name,
        )

    @property
    def context(self):

        link = self.survey_link

        if self.trackable:
            link = "{}?uid={}".format(link, self.runtime.anonymous_student_id)

        if self.overwrite_survey_questions and not (hasattr(self.xmodule_runtime, 'is_author_mode') or self.completed_survey):
            self.overwrite_survey_question_headings()

        context = {
            "title": self.display_name,
            "introductory_text": self.introductory_text,
            "text_link": self.text_link,
            "survey_link": link,
            "completed_survey": self.verify_completion() if not hasattr(self.xmodule_runtime, 'is_author_mode') else True,
            "completion_page": self.get_handler_url("completion"),
            "inline_survey_view": self.inline_survey_view,
            "is_for_external_course": self.is_for_external_course,
        }

        return context

    def _validate_survey_name(self, validation, survey_name, api_surveymonkey):
        """
        This method searches survey list by survey title and sets a message if the survey is not unique.
        """
        survey_data = self.get_survey_data_by_name(api_surveymonkey, validation, survey_name)

        if not survey_data:
            return None

        return survey_data[0].get("id", "")

    def _get_survey_link(self, suvey_id, validation, api_surveymonkey):
        """
        Gets the survey link by calling the survey collector.

        Args:
            suvey_id: ID of the survey.
            validation: Xblock validation object.
            api_surveymonkey: Instance of api_survemonkey.ApiSurveyMonkey.
        """
        collectors = api_surveymonkey.get_collectors(
            suvey_id,
            self.location.block_id,
            **{"include": "url,type,survey_id"}
        )
        data_collectors = collectors.get("data", [])

        if not data_collectors:
            validation.add(ValidationMessage(
                ValidationMessage.ERROR, u"The survey must have at least one defined collector."
            ))
            return None
        for data_collector in data_collectors:
            if data_collector.get("type") == "weblink":
                self.survey_link = data_collector.get("url")
                return None

        validation.add(ValidationMessage(
            ValidationMessage.ERROR, u"The survey must have at least one weblink defined collector."
        ))

    def get_survey_data_by_name(self, api_surveymonkey, validation, survey_name):
        """
        Returns the survey data by name.

        Args:
            api_surveymonkey: Instance of api_survemonkey.ApiSurveyMonkey.
            validation: Xblock validation object.
            survey_name: Survey name string.
        Returns:
            survey_data: https://api.surveymonkey.com/v3/surveys/ survey_name data.
            None: If the survey does not exists or there are more than one survey with the
                same name.
        """
        response = api_surveymonkey.get_surveys()
        data_response = response.get("data", [])

        survey_data = [survey for survey in data_response if survey["title"] == survey_name]
        survey_data_length = len(survey_data)

        if not survey_data_length:
            validation.add(
                ValidationMessage(ValidationMessage.ERROR, u"{} survey does not exist.".format(survey_name)),
            )
            return None
        elif survey_data_length > 1:
            validation.add(ValidationMessage(
                ValidationMessage.ERROR, u"There are two or more surveys with the {} name.".format(survey_name),
            ))
            return None

        return survey_data

    def _check_completion_from_submissions(self):
        """
        """
        completion = False
        last_submission = None
        try:
            submissions = submissions_api.get_submissions(self.student_item)
            if submissions:
                completion = True
                last_submission = submissions[0]
        except Exception:
            LOG.info(
                "Error getting submissions for the survey %s related to course %s",
                self.survey_name,
                self.course_id.to_deprecated_string(),
            )

        return completion, last_submission

    @property
    def student_item(self):
        item = dict(
            student_id=self.runtime.anonymous_student_id,
            course_id=self.course_id.to_deprecated_string(),
            item_id=self.location.block_id,
            item_type="surveymonkey",
        )
        return item

    @property
    def _api_survey_monkey(self):

        if self.api_survey_monkey is not None:
            return self.api_survey_monkey
        try:
            self.api_survey_monkey = ApiSurveyMonkey(
                self.client_id,
                self.client_secret,
                self.surveymonkey_api_cache_duration,
            )
            return self.api_survey_monkey

        except InvalidClientIdError:
            return None

    def verify_completion(self):
        if not self.completed_survey:
            submission_status, last_submission = self._check_completion_from_submissions()
            if submission_status and last_submission:
                self.completed_survey = True
                # submissions_api.set_score(last_submission.get("uuid"), self.weight, self.weight)
                return True

        return self.completed_survey

    def max_score(self):
        return self.weight

    @XBlock.handler
    def completion(self, request, suffix=''):

        context = {
            "course": get_course_by_id(self.course_id),
            "completed_survey": self.verify_completion(),
            "css": self.resource_string("static/css/surveymonkey.css"),
            "online_help_token": "online_help_token",
        }
        return Response(LOADER.render_template("static/html/surveymonkey_completion_page.html", context))

    @XBlock.handler
    def confirmation(self, request, suffix=''):

        uid = request.params.get('uid')
        user = self.runtime.get_real_user(uid)

        try:
            if user and self.is_for_external_course:
                submissions_api.create_submission(
                    self.student_item,
                    {"survey_completed":True}
                )
        except Exception:
            LOG.info(
                "Error creating a submission for the survey %s related to course %s",
                self.survey_name,
                self.course_id.to_deprecated_string(),
            )

        course = get_course_by_id(self.course_id)
        context = {
            "completed_survey": self.verify_completion(),
            "css": self.resource_string("static/css/surveymonkey.css"),
            "course_link": course.other_course_settings.get("external_course_target"),
        }
        return Response(LOADER.render_template("static/html/surveymonkey_confirmation_page.html", context))

    def overwrite_survey_question_headings(self):
        """
        Overwrites the survey question headings.

        Takes the values returned from self.get_overwritten_question_from_field
        to overwrite the question heading with the user's response.

        Raises:
            Exception: If previous_survey_id or self.survey_id were not found.
        """
        if not (self.previous_survey_id or self.survey_id):
            raise Exception("Not enough arguments were found.")

        previous_responses = self.get_user_previous_survey_responses()
        overwritten_questions = self.get_overwritten_question_from_field()
        new_question_headings = []

        for overwritten_question in overwritten_questions:
            overwritten_question_heading = overwritten_question

            for previous_response in previous_responses:
                question_heading = "{{{question_heading}}}".format(
                    question_heading=previous_response.get("question_heading", ""),
                )

                if question_heading in overwritten_question_heading:
                    overwritten_question_heading = overwritten_question_heading.replace(question_heading, previous_response.get("question_answer", ""))

            new_question_headings.append(overwritten_question_heading)

        if not new_question_headings:
            return None

        survey_details = self._api_survey_monkey.get_survey_details(self.survey_id, self.location.block_id)
        survey_pages = survey_details.get("pages", [])

        if not survey_pages:
            return None

        # Let's take the first page of the survey because API calls do not support pagination.
        survey_questions = survey_pages[0].get("questions", [])

        for index, new_question_heading in enumerate(new_question_headings):
            patch_data = {
                "headings": [{
                    "heading": new_question_heading,
                }],
            }

            try:
                self._api_survey_monkey.patch_question_data(
                    self.survey_id,
                    survey_pages[0].get("id", ""),
                    survey_questions[index].get("id", ""),
                    **patch_data
                )
            except IndexError:
                # This means that there are no more questions in the survey, therefore,
                # it's not necessary to make more API calls.
                break

        return None

    def get_overwritten_question_from_field(self):
        """
        Parses and returns the questions contained in the overwritten_question_headings field.
        Splits each question into a new line and then return them as a items in a list.

        Returns:
            List: Containing the question headings to overwrite.
        """
        if (self.overwritten_question_headings == self.default_overwritten_question_headings_text or
                not self.overwrite_survey_questions):
            return []

        overwritten_headings = self.overwritten_question_headings.splitlines()
        headings_data = []

        for overwritten_heading in overwritten_headings:
            # This is to avoid the blank spaces values.
            if not overwritten_heading:
                continue

            headings_data.append(overwritten_heading)

        return headings_data

    def get_user_previous_survey_responses(self):
        """
        Returns the previous question responses for the corresponding user anonymous id.

        Returns:
            List: List of objects:
                [{
                    "page_id": Previous page id of the survey.
                    "question_id": Previous question id of the survey.
                    "question_heading": Previous survey question header.
                    "question_answer": User answer of the previous question.
                }]
        """
        kwargs = {"simple": "true"}
        previous_survey_responses = self._api_survey_monkey.get_survey_responses(self.previous_survey_id, **kwargs)

        if not previous_survey_responses:
            return []

        user_id = self.runtime.anonymous_student_id
        user_response = {}

        for response in previous_survey_responses.get("data", []):
            custom_variables = response.get("custom_variables", {})

            if custom_variables.get("uid") == user_id:
                user_response = response
                break

        if not user_response:
            return []

        page_questions = user_response.get("pages", [])

        if not page_questions:
            return []

        # Let's take the first page of the survey because API calls do not support pagination.
        page_data = page_questions[0]

        previous_survey_questions = page_data.get("questions", [])
        previous_data = []

        for previous_response in previous_survey_questions:
            answers = previous_response.get("answers", [])

            if not answers:
                continue

            previous_data.append({
                "page_id": page_data.get("id", ""),
                "question_id": previous_response.get("id", ""),
                "question_heading": previous_response.get("heading", ""),
                "question_answer": answers[0].get("simple_text", ""),
            })

        return previous_data
