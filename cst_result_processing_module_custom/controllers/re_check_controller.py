import base64
import logging

from odoo import fields, http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class ReCheckApplicationController(http.Controller):

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

        re_register = (
            request.env["cst.exam.re.eval.registar"]
            .sudo()
            .search([("is_published", "=", True), ("type", "=", "recheck")], limit=1)
        )

        if not re_register:
            return False

        existing_request = (
            request.env["cst.exam.re.eval.application"]
            .sudo()
            .search(
                [
                    ("student_id", "=", student.id),
                    ("re_eval_registar_id", "=", re_register.id),
                ],
                limit=1,
            )
        )

        if existing_request:
            return request.render(
                "cst_result_processing_module_custom.already_applied_recheck_template",
                {"re_register": re_register, "existing_request": existing_request},
            )
        return False

    def get_fee_products(self, fee_type):
        # Search for active FeeStructure with matching fee_type
        fee_structures = (
            request.env["cst.fee.structure"]
            .sudo()
            .search([("fee_type", "=", fee_type), ("is_active", "=", True)])
        )

        # Get all product records linked to these fee structures
        products = fee_structures.mapped("fee_component_ids")
        return products

    def generate_invoice_line(self, products, total_subjects):
        invoice_lines = []

        for product in products:
            invoice_lines.append(
                (
                    0,
                    0,
                    {
                        "name": product.name,
                        "quantity": total_subjects,
                        "price_unit": product.lst_price,
                        "product_id": product.id,
                    },
                )
            )
        return invoice_lines

    # GET THE FORM for re_evaluation
    @http.route(
        "/student/re_check_application/",
        type="http",
        auth="user",
        website=True,
    )
    def re_check_application_form(self, **kwargs):
        denied = self._check_student_group()
        if denied:
            return denied

        already_registered = self._check_if_already_registered()

        if already_registered:
            return already_registered

        # Fetch the ReEvalRegistar record based on the is_published=True
        registar = (
            request.env["cst.exam.re.eval.registar"]
            .sudo()
            .search([("is_published", "=", True), ("type", "=", "recheck")], limit=1)
        )
        _logger.info("The Registar is: %s", registar)

        student = (
            request.env["op.student"]
            .sudo()
            .search([("user_id", "=", request.env.user.id)], limit=1)
        )

        exam_marks = (
            request.env["cst.exam.mark"]
            .sudo()
            .search(
                [
                    ("student_id", "=", student.id),
                    (
                        "marksheet_subject_id.marksheet_id.term_id",
                        "=",
                        registar.term_id.id,
                    ),
                ]
            )
        )

        _logger.info("The exam_marks is: %s", exam_marks)

        subjects = (
            request.env["op.subject"]
            .sudo()
            .browse(exam_marks.mapped("marksheet_subject_id.subject_id.id"))
        )
        _logger.info("The SUBJECTS ARE : %s", subjects)

        # Render the application form
        return request.render(
            "cst_result_processing_module_custom.reeval_application_form",
            {"registar": registar, "student": student, "subject_ids": subjects},
        )

    # Submit Recheck form
    @http.route(
        "/student/re_check_application/submit",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def submit_re_eval_application(self, **post):
        _logger.info("The post is: %s", post)
        # Get the data from the form

        registar_id = int(post.get("registar_id"))
        student_id = int(post.get("student_id"))

        attachment_file = post.get("attachment")
        attachment_data = False
        filename = False
        mimetype = False

        if attachment_file:
            attachment_data = base64.b64encode(attachment_file.read()).decode("utf-8")
            filename = attachment_file.filename
            mimetype = attachment_file.mimetype

        subject_ids = list(map(int, request.httprequest.form.getlist("subject_ids[]")))

        if isinstance(subject_ids, str):  # In case only one subject was checked
            subject_ids = [int(subject_ids)]
        else:
            subject_ids = list(map(int, subject_ids))  # Convert all to integers
            # If it's already a list, map over i
        total_subjects = len(subject_ids)

        # Ensure the student has selected subjects
        if not subject_ids:
            return request.render(
                "cst_result_processing_module_custom.template_no_subject_selected", {}
            )

        # Get the ReEvalRegistar object
        registar = request.env["cst.exam.re.eval.registar"].sudo().browse(registar_id)

        # Student ID
        student = request.env["op.student"].sudo().browse(student_id)

        # Create the application if the register is published
        if registar.is_published:
            # Creating the invoice
            products = self.get_fee_products("re_check")
            invoice_lines = self.generate_invoice_line(products, total_subjects)
            print("The invoice_lines are", invoice_lines)
            invoice = None
            if invoice_lines:
                invoice = (
                    request.env["account.move"]
                    .sudo()
                    .create(
                        {
                            "move_type": "out_invoice",
                            "partner_id": student.partner_id.id,
                            "invoice_origin": "Re-Check Application",
                            "invoice_line_ids": invoice_lines,
                        }
                    )
                )
                invoice.action_post()
            # Creating the application
            application_vals = {
                "re_eval_registar_id": registar_id,
                "student_id": student_id,
                "subject_ids": [(6, 0, subject_ids)],  # Many2many relation
                "attachment": attachment_data,
                "attachment_filename": filename,
                "invoice_id": invoice.id,
            }
            request.env["cst.exam.re.eval.application"].sudo().create(application_vals)

            if invoice_lines:
                return request.redirect(f"/my/invoices?sortby=state&filterby=invoices")
            return request.render(
                "cst_result_processing_module_custom.thanks_recheck",
                {},
            )

        else:
            raise ValidationError("This re-evaluation register is not published yet.")

    # GET View my request
    # GET Request to fetch application details
    @http.route(
        "/student/my/recheck/application", type="http", auth="user", website=True
    )
    def view_my_re_check_application(self, **kwargs):
        denied = self._check_student_group()
        if denied:
            return denied

        already_registered = self._check_if_already_registered()

        registar = (
            request.env["cst.exam.re.eval.registar"]
            .sudo()
            .search([("is_published", "=", True), ("type", "=", "recheck")], limit=1)
        )

        if not already_registered:
            return request.render(
                "cst_result_processing_module_custom.recheck_application_form",
                {
                    "registar": registar,
                },
            )

        student = (
            request.env["op.student"]
            .sudo()
            .search([("user_id", "=", request.env.user.id)], limit=1)
        )
        re_eval_request = (
            request.env["cst.exam.re.eval.application"]
            .sudo()
            .search(
                [
                    ("student_id", "=", student.id),
                    ("re_eval_registar_id", "=", registar.id),
                ],
                limit=1,
            )
        )

        return request.render(
            "cst_result_processing_module_custom.view_my_re_check_application",
            {"re_eval_request": re_eval_request, "registar": registar},
        )
