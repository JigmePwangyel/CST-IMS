import base64

from odoo import http
from odoo.http import request


class StudentInformationController(http.Controller):
    @http.route(["/my/student/profile"], type="http", auth="user", website=True)
    def portal_my_profile(self, **kw):
        student = request.env.user.student_line

        user = request.env.user
        student = (
            request.env["op.student"]
            .sudo()
            .search([("user_id", "=", user.id)], limit=1)
        )
        if not student:
            return request.render("website.404")

        return request.render(
            "cst_student_profile_module_custom.student_profile_portal",
            {
                "student": student,
            },
        )
