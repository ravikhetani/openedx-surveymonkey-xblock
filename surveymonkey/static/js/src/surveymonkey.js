/* Javascript for SurveyMonkeyXBlock. */
function SurveyMonkeyXBlock(runtime, element) {

    var verifyCompletion = runtime.handlerUrl(element, "verify_completion");

    $(function ($) {
        /* Here's where you'd do things on page load. */
    });

    $(".done", element).click(function(eventObject) {
        $.ajax({
            type: "GET",
            url: verifyCompletion,
            success: updateState
        });
    });

    function updateState(data){
        if(data.completed){
            $(".done").hide();
            $(".status-message").text(gettext("Completed"));
        }
    }
}
