from odoo import http
from odoo.http import request


class ResultData(http.Controller):
    @http.route(["/student/results/"], type="http", auth="user", website="True")
    def display_marksheet(self, **kwargs):
        user = request.env.user

        # Check if user belongs to student group
        if not user.has_groups("base.group_portal"):
            return request.render(
                "cst_result_processing_module_custom.template_access_denied", {}
            )

        # Get student linked to user
        student = (
            request.env["op.student"]
            .sudo()
            .search([("user_id", "=", user.id)], limit=1)
        )
        if not student:
            return request.not_found()

        # Find marks of current student
        student_marks = (
            request.env["cst.exam.mark"]
            .sudo()
            .search([("student_id", "=", student.id)])
        )

        # Extract marksheet_ids from the marks records (through marksheet_sub_rel_id → marksheet_id)
        related_marksheet_ids = student_marks.mapped(
            "marksheet_subject_id.marksheet_id.id"
        )

        # Get declared marksheets only from that list
        declared_marksheets = (
            request.env["cst.exam.marksheet"]
            .sudo()
            .search([("id", "in", related_marksheet_ids), ("state", "=", "declared")])
        )

        return request.render(
            "cst_result_processing_module_custom.student_marksheet_template",
            {"marksheets": declared_marksheets, "student_id": student.id},
        )

    @http.route(
        ["/student/results/view/<int:marksheet_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def view_result_details(self, marksheet_id, **kwargs):
        user = request.env.user
        student = (
            request.env["op.student"]
            .sudo()
            .search([("user_id", "=", user.id)], limit=1)
        )
        if not student:
            return request.not_found()

        # Find marks linked to this marksheet and student
        marks = (
            request.env["cst.exam.mark"]
            .sudo()
            .search(
                [("marksheet_id", "=", marksheet_id), ("student_id", "=", student.id)]
            )
        )

        # Find the overall result
        overall_result = (
            request.env["cst.exam.result"]
            .sudo()
            .search(
                [("marksheet_id", "=", marksheet_id), ("student_id", "=", student.id)],
                limit=1,
            )
        )

        return request.render(
            "cst_result_processing_module_custom.student_result_details_template",
            {
                "marks": marks,
                "overall_result": overall_result,
            },
        )
