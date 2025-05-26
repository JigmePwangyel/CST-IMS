import base64

from odoo import http
from odoo.http import request


class StudentLeaveController(http.Controller):

    # Helper Methods
    def _check_student_group(self, user):
        if not user.has_group("base.group_portal"):
            return request.render(
                "cst_student_leave_module_custom.template_leave_access_denied", {}
            )
        return None

    def _return_error_template(self):
        return request.render(
            "cst_student_leave_module_custom.template_leave_error_template",
            {},
        )

    # GET ALL Leave of specific logged in user
    @http.route("/my/student/leave", type="http", auth="user", website=True)
    def get_student_leave(self, **kwargs):

        user = request.env.user
        denied = self._check_student_group(user)
        if denied:
            return denied
        student = (
            request.env["op.student"]
            .sudo()
            .search([("user_id", "=", user.id)], limit=1)
        )
        if not student:
            return self._return_error_template()

        state = kwargs.get("state")
        domain = [("student_id", "=", student.id)]

        if state:
            domain.append(("state", "=", state))
        student_leaves = request.env["cst.student.leave"].sudo().search(domain)

        return request.render(
            "cst_student_leave_module_custom.portal_student_leave_template",
            {"leave_data": student_leaves},
        )

    # GET the form through which students can apply for leave
    @http.route("/my/student/leave/apply", type="http", auth="user", website=True)
    def get_leave_application_form(self, **kwargs):
        user = request.env.user
        denied = self._check_student_group(user)
        if denied:
            return denied
        student = (
            request.env["op.student"]
            .sudo()
            .search([("user_id", "=", user.id)], limit=1)
        )
        if not student:
            return self._return_error_template()
        leave_types = request.env["cst.student.leave.type"].sudo().search([])
        print("The leave types are: ", leave_types)
        return request.render(
            "cst_student_leave_module_custom.student_leave_application_form",
            {"student": student, "leave_types": leave_types},
        )

    # POST end point when users submit leave application form
    @http.route(
        "/my/student/leave/apply/submit",
        type="http",
        auth="user",
        website=True,
        csrf=True,
    )
    def post_leave_application(self, **kwargs):
        user = request.env.user
        denied = self._check_student_group(user)
        if denied:
            return denied

        # Accessing form data
        student_id = int(kwargs.get("student_id"))
        leave_type = int(kwargs.get("leave_type"))
        from_date = kwargs.get("start_date")
        to_date = kwargs.get("end_date")
        description = kwargs.get("description")
        attachment = request.httprequest.files.get("attachment")

        attachment_id = None

        print("Student ID:", student_id)
        print("Leave Type ID:", leave_type)
        print("From Date:", from_date)
        print("To Date:", to_date)
        print("Description:", description)
        print("Attachment:", attachment)

        if attachment:
            attachment_id = (
                request.env["ir.attachment"]
                .sudo()
                .create(
                    {
                        "name": attachment.filename,
                        "datas": base64.b64encode(attachment.read()),
                        "res_model": "cst.student.leave",  # temporary, link it after leave created
                        "res_id": 0,  # temporarily zero
                    }
                )
            )

        # Create the Leave Application
        leave_application = (
            request.env["cst.student.leave"]
            .sudo()
            .create(
                {
                    "student_id": student_id,
                    "holiday_status_id": leave_type,
                    "date_from": from_date,
                    "date_to": to_date,
                    "state": "confirm",
                    "name": description,
                }
            )
        )

        print("Attachment ID is:", attachment_id)
        print("leave application is:", leave_application)
        # Link the attachment if it exists
        if attachment_id:
            leave_application.supported_attachment_ids = [(6, 0, [attachment_id.id])]

        return request.render(
            "cst_student_leave_module_custom.template_leave_success",  # Replace with your success page
            {},
        )

    # GET request to view more info about the leave
    @http.route(
        "/my/student/leave/view/<int:leave_id>", type="http", auth="user", website=True
    )
    def view_leave_application(self, leave_id, **kwargs):
        # Fetch the leave record
        leave_record = request.env["cst.student.leave"].sudo().browse(leave_id)

        # Check if record exists
        if not leave_record.exists():
            return request.not_found()

        # Render the leave detail page
        return request.render(
            "cst_student_leave_module_custom.leave_detail_page",
            {
                "leave": leave_record,
            },
        )
