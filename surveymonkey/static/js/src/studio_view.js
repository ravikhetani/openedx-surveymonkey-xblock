/* Javascript for StudioView. */
function StudioViewEdit(runtime, element) {
    "use strict";

    /*eslint no-undef: "error"*/
    StudioEditableXBlockMixin(runtime, element);

    $(function ($) {
        $(".list-input.settings-list").append($("#completion-page"));
    });
}
