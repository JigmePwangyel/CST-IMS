from odoo import http
from odoo.http import request


class ExamController(http.Controller):

    # Helper Methods
    def _check_student_group(self):
        if not request.env.user.has_group("base.group_portal"):
            return request.render(
                "cst_result_processing_module_custom.template_access_denied", {}
            )
        return None

    # GET to fetch exam card
    @http.route("/my/exam", type="http", auth="user", website=True)
    def exam_page(self, **kwargs):
        denied = self._check_student_group()
        if denied:
            return denied

        return request.render(
            "cst_result_processing_module_custom.exam_portal_template",
            {"page_name": "Exams"},
        )
