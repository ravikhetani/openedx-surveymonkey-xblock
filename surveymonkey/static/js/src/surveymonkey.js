/* Javascript for SurveyMonkeyXBlock. */
function SurveyMonkeyXBlock(runtime, element) {

    var verifyCompletion = runtime.handlerUrl(element, "verify_completion");

    $(function ($) {
        if(window.location.hash.startsWith("#completion")){
            $(".surveymonkey_block_completion").show();
        } else {
            $(".surveymonkey_block").show();
        }
    });
}
