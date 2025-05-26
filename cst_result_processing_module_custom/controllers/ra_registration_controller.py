from odoo import http
from odoo.http import request


class RARegistrationController(http.Controller):

    # Helper Methods
    def _check_student_group(self):
        if not request.env.user.has_group("base.group_portal"):
            return request.render(
                "cst_result_processing_module_custom.template_access_denied", {}
            )
        return None

    def _check_if_already_registered(self):
        student = (
            request.env["op.student"]
            .sudo()
            .search([("user_id", "=", request.env.user.id)], limit=1)
        )
        if not student:
            return False  # or redirect / show error

        ra_register = (
            request.env["cst.exam.ra.register"]
            .sudo()
            .search([("is_published", "=", True)], limit=1)
        )

        if not ra_register:
            return False

        existing_request = (
            request.env["cst.exam.ra.request"]
            .sudo()
            .search(
                [
                    ("student_id", "=", student.id),
                    ("ra_register_id", "=", ra_register.id),
                ],
                limit=1,
            )
        )

        if existing_request:
            return request.render(
                "cst_result_processing_module_custom.already_applied_template",
                {"ra_register": ra_register, "existing_request": existing_request},
            )
        return False

    # Routes
    # GET to fect ra-registration card
    @http.route("/student/ra-registration", type="http", auth="user", website=True)
    def ra_registration_page(self, **kwargs):
        denied = self._check_student_group()
        if denied:
            return denied

        already_registered = self._check_if_already_registered()

        if already_registered:
            return already_registered

        ra_register = (
            request.env["cst.exam.ra.register"]
            .sudo()
            .search([("is_published", "=", True)], limit=1)
        )

        return request.render(
            "cst_result_processing_module_custom.ra_registration_template",
            {
                "ra_register": ra_register,
            },
        )

    # GET Request to fecth application form
    @http.route(
        "/student/ra-registration/apply", type="http", auth="user", website=True
    )
    def ra_apply_form(self, **kwargs):
        denied = self._check_student_group()
        if denied:
            return denied

        already_registered = self._check_if_already_registered()
        if already_registered:
            return already_registered

        ra_register = (
            request.env["cst.exam.ra.register"]
            .sudo()
            .search([("is_published", "=", True)], limit=1)
        )
        if not ra_register:
            return request.redirect("/student/ra-registration")

        student = (
            request.env["op.student"]
            .sudo()
            .search([("user_id", "=", request.env.user.id)], limit=1)
        )
        if not student:
            return request.redirect("/student/ra-registration")

        # Search for result where student has passed for the current RA term
        result = (
            request.env["cst.exam.result"]
            .sudo()
            .search(
                [
                    ("student_id", "=", student.id),
                    ("marksheet_id.term_id", "=", ra_register.term_id.id),
                    (
                        "result",
                        "=",
                        "pass",
                    ),  # Assuming 'state' is used to indicate pass/fail
                ],
                limit=1,
            )
        )

        if not result:
            return request.render(
                "cst_result_processing_module_custom.template_not_eligible", {}
            )

        # Check if any of the marks has remark = 'ra'
        has_ra_remark = any(mark.remarks == "ra" for mark in result.marks_ids)

        if not has_ra_remark:
            return request.render(
                "cst_result_processing_module_custom.template_not_eligible", {}
            )

        ra_marks = result.marks_ids.filtered(lambda m: m.remarks == "ra")
        subjects = (
            request.env["op.subject"]
            .sudo()
            .browse(ra_marks.mapped("marksheet_subject_id.subject_id.id"))
        )

        return request.render(
            "cst_result_processing_module_custom.ra_application_form",
            {
                "ra_register": ra_register,
                "student": student,
                "subject_ids": subjects,
            },
        )

    # POST Request to post ra application
    @http.route(
        "/student/ra-registration/submit",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def ra_registration_submit(self, **kwargs):

        # Retrieve the form data  dd
        ra_register_id = int(kwargs.get("ra_register_id"))
        student_id = int(kwargs.get("student_id"))
        subject_ids = list(map(int, request.httprequest.form.getlist("subject_ids[]")))

        if isinstance(subject_ids, str):  # In case only one subject was checked
            subject_ids = [int(subject_ids)]
        else:
            subject_ids = list(map(int, subject_ids))  # Convert all to integers
            # If it's already a list, map over i

        # Fetch the RA register record based on the ID
        ra_register = request.env["cst.exam.ra.register"].sudo().browse(ra_register_id)
        if not ra_register:
            return request.redirect("/student/ra-registration")

        # Fetch the student record
        student = request.env["op.student"].sudo().browse(student_id)
        if not student:
            return request.redirect("/student/ra-registration")

        # Ensure the student is eligible and has selected subjects
        if not subject_ids:
            return request.render(
                "cst_result_processing_module_custom.template_no_subject_selected", {}
            )

        # Check if any selected subject is eligible for re-assessment
        eligible_subjects = request.env["op.subject"].sudo().browse(subject_ids)
        if not eligible_subjects:
            return request.render(
                "cst_result_processing_module_custom.template_not_eligible", {}
            )

        # print("RA Register: ", ra_register_id)
        # print("Stduent ID : ", student_id)
        # print("Subject IDS : ", subject_ids)
        # Create the RA application record
        ra_application = (
            request.env["cst.exam.ra.request"]
            .sudo()
            .create(
                {
                    "ra_register_id": ra_register.id,
                    "student_id": student.id,
                    "subject_ids": [
                        (6, 0, subject_ids)
                    ],  # Many2many field for subjects
                }
            )
        )

        # Optionally, you can add additional logic for sending confirmation emails or notifications.

        # Redirect user to confirmation page or show success message
        return request.redirect("/student/ra-registration")

    # GET Request to fetch application details
    @http.route("/student/my-ra-application", type="http", auth="user", website=True)
    def view_my_ra_application(self, **kwargs):
        denied = self._check_student_group()
        if denied:
            return denied

        already_registered = self._check_if_already_registered()

        ra_register = (
            request.env["cst.exam.ra.register"]
            .sudo()
            .search([("is_published", "=", True)], limit=1)
        )

        if not already_registered:
            return request.render(
                "cst_result_processing_module_custom.ra_registration_template",
                {
                    "ra_register": ra_register,
                },
            )
        student = (
            request.env["op.student"]
            .sudo()
            .search([("user_id", "=", request.env.user.id)], limit=1)
        )
        ra_request = (
            request.env["cst.exam.ra.request"]
            .sudo()
            .search([("student_id", "=", student.id)], limit=1)
        )

        return request.render(
            "cst_result_processing_module_custom.view_my_ra_application",
            {
                "ra_request": ra_request,
            },
        )
