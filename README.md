# Xblock Openedx-Surveymonkey

The Openedx-Surveymonkey Xblock allows to embed a survey link inside a unit, also, allows to include the survey description and title. The xblock allows you to include the user anonymous id as a custom variable,  that is a logic feature that allows you to track data about respondents by passing one or more values through a survey link and into your survey results.

## Installation
Install the requirements into the Python virtual environment of your `edx-platform` installation by running the following command from the root folder:
```
$ pip install -r requirements.txt
```

##  Enabling in Studio

After successful installation, you can activate this component for a course following these steps:

* From the main page of a specific course, navigate to `Settings -> Advanced Settings` from the top menu.
* Check for the `Advanced Module List` policy key, and Add ``"surveymonkey"`` to the policy value list.
* Click the "Save changes" button.

## Usage

### Course Author criteria
-   I can add a “SurveyMonkey” Xblock.
-   I can set in a SurveyMonkey-XBlock a survey URL.
-   I can choose to make the survey trackable (i.e. pass user id across via URL) - or not.
-   I can add some introductory text which is displayed to the student above the survey link.
-   I can define the text used to link to the survey (or leave it blank to use the default).
-   I can define the text used in the xblock title


### Student view criteria
-   Clicking over the link opens the survey in a new browser tab.
-   If user tracking is selected, then the survey URL includes a `user_anonymous_id` custom var with the student's anonymous user id

## About this XBlock
The  Openedx-Surveymonkey XBlock was built by [eduNEXT](https://www.edunext.co/), a company specialized in open edX development and open edX cloud services.

##  How to contribute
* Fork this repository.
* Commit your changes on a new branch
* Make a pull request to the master branch
* Wait for the code review and merge process
