"""TO-DO: Write a description of what this XBlock is."""

import pkg_resources

from django.utils.translation import ugettext_lazy as _

from xblock.core import XBlock
from xblock.fields import Scope, String, Boolean
from xblock.fragment import Fragment
from xblockutils.resources import ResourceLoader
from xblockutils.studio_editable import StudioEditableXBlockMixin

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
        display_name=_("SurveyMonkey Link"),
        help=_("Enter the survey link."),
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

    # Possible editable fields
    editable_fields = (
        "display_name",
        "survey_link",
        "text_link",
        "trackable",
        "introductory_text",
    )

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
        }

        return context
