import base64
import logging
from datetime import datetime

from odoo import fields, http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class RegistrationPortalController(http.Controller):

    # Helper Methods
    # def _check_student_group(self):
    #     if not request.env.user.has_group("base.group_portal"):
    #         return request.render(
    #             "cst_semester_registration.template_access_denied", {}
    #         )
    #     return None

    def _check_if_already_registered(self):
        student = (
            request.env["op.student"]
            .sudo()
            .search([("user_id", "=", request.env.user.id)], limit=1)
        )

        if not student:
            return request.render(
                "cst_semester_registration.template_student_not_found", {}
            )

        register = (
            request.env["cst.registration.register"]
            .sudo()
            .search(
                [("state", "=", "ongoing")],
                limit=1,
            )
        )

        if not register:
            return request.render(
                "cst_semester_registration.template_no_active_registration", {}
            )

        existing_registration = (
            request.env["cst.registration"]
            .sudo()
            .search(
                [("student_id", "=", student.id), ("register_id", "=", register.id)],
                limit=1,
            )
        )

        if existing_registration:
            return request.render(
                "cst_semester_registration.template_already_registered",
                {"existing_registration": existing_registration},
            )
        return None

    def check_backpaper(self, marks):
        backpapers = set()
        subject_remark_map = {}

        for rec in marks:
            subject_id = rec.subject_id.id
            remark = rec.remarks

            if subject_id not in subject_remark_map:
                subject_remark_map[subject_id] = set()

            subject_remark_map[subject_id].add(remark)

        for subject_id, remarks in subject_remark_map.items():
            # If no 'pass' or 'pass_ra', it's a backpaper
            if "pass" not in remarks and "pass_ra" not in remarks:
                subject = request.env["op.subject"].sudo().browse(subject_id)
                # Check if subject_id exists in cst.offer.module with the correct batch
                offer_module = (
                    request.env["cst.offer.module"]
                    .sudo()
                    .search(
                        [
                            ("subject_ids", "=", subject_id),
                        ],
                        limit=1,
                    )
                )
                # Check is_offered = true in op.subject so as to handle special case
                if offer_module or subject.is_offered_to_repeat:
                    backpapers.add(subject_id)

        if not backpapers:
            return False, []
        return True, list(backpapers)

    def compute_repeat_module(self, marks, term_id):
        subject_ids = set()

        for mark in marks:
            if mark.marksheet_id.term_id.id == term_id.id and mark.remarks in [
                "fail",
                "ra",
                "fail_ra",
            ]:
                subject_ids.add(mark.subject_id.id)
        repeat_modules = set()

        if subject_ids:
            subjects = request.env["op.subject"].sudo().browse(list(subject_ids))
            for subject in subjects:
                if subject.is_offered_to_repeat or subject.is_offered:
                    repeat_modules.add(subject.id)
        repeat_modules = request.env["op.subject"].browse(list(repeat_modules))
        return repeat_modules

    @http.route(
        "/student/semester_registration", type="http", auth="user", website=True
    )
    def show_registration_form(self, **kwargs):
        """Display semester registration form with integrated eligibility check"""
        # Check if already registered
        already_registered = self._check_if_already_registered()
        if already_registered:
            print("Already Registered")
            return already_registered

        # Get current student
        student = (
            request.env["op.student"]
            .sudo()
            .search([("user_id", "=", request.env.user.id)], limit=1)
        )
        if not student:
            return request.render(
                "cst_semester_registration.template_student_not_found", {}
            )

        # Check active registration period
        register = (
            request.env["cst.registration.register"]
            .sudo()
            .search(
                [
                    ("state", "=", "ongoing"),
                    ("is_published", "=", True),
                ],
                limit=1,
            )
        )
        print("The register is: ", register)
        if not register:
            return request.render(
                "cst_semester_registration.template_no_active_registration", {}
            )

        # --- Start of integrated eligibility check ---
        active_term = (
            request.env["op.academic.term"]
            .sudo()
            .search([("is_active", "=", True)], limit=1)
        )

        if not active_term:
            return request.render(
                "cst_semester_registration.template_no_active_term", {}
            )

        # Initialize variables
        regular_subjects = []

        # Find immediate previous term (now properly defined)
        previous_term = (
            request.env["op.academic.term"]
            .sudo()
            .search(
                [
                    ("term_end_date", "<", active_term.term_start_date),
                    ("term_end_date", "!=", False),
                    ("term_start_date", "!=", False),
                ],
                order="term_end_date desc",
                limit=1,
            )
        )

        print("The previous term is: ", previous_term)
        # First Thing CHeck whether student is eligible to register
        # LOGIC Immediate Semester ghi result

        # For Backpaper.
        # Check marks for all syvjects
        # Now if two subjects result is available for a particular student and result is pass. Student dont have backpaper for that subject
        # We can also get the count of repeat from here as well

        if not previous_term:
            return request.render(
                "cst_semester_registration.template_no_active_term", {}
            )

        # Check immediate term results first
        immediate_result = (
            request.env["cst.exam.result"]
            .sudo()
            .search(
                [
                    ("student_id", "=", student.id),
                    ("marksheet_id.term_id", "=", previous_term.id),
                ],
                limit=1,
            )
        )

        offer_module = (
            request.env["cst.offer.module"]
            .sudo()
            .search([("batch_ids", "in", [student.batch_id.id])], limit=1)
        )
        regular_subjects = (
            offer_module.subject_ids.filtered(lambda x: x.active)
            if offer_module
            else []
        )
        marks = (
            request.env["cst.exam.mark"]
            .sudo()
            .search([("student_id", "=", student.id)])
        )

        have_back, backpapers = self.check_backpaper(marks)
        backpaper_subjects = request.env["op.subject"].browse(backpapers)

        print("Immediate Result: ", immediate_result)
        print("regular_subjects: ", regular_subjects)
        print("have_back: ", have_back)
        print("backpapers: ", backpaper_subjects)

        if immediate_result:
            # Fail previous semester and no backpapers
            if immediate_result.result != "pass" and not have_back:
                return request.render(
                    "cst_semester_registration.template_reg_not_eligible", {}
                )

            # Fail previous semester with backpapers
            elif immediate_result.result != "pass" and have_back:
                return request.render(
                    "cst_semester_registration.template_registration_form",
                    {
                        "student": student,
                        "register": register,
                        "has_regular_subject": False,
                        "regular_subjects": regular_subjects,
                        "has_repeat_subject": True,
                        "repeatable_subjects": backpaper_subjects,
                        "is_repeat": False,
                    },
                )

            # Pass previous semester with backpapers
            elif immediate_result.result == "pass" and have_back:
                return request.render(
                    "cst_semester_registration.template_registration_form",
                    {
                        "student": student,
                        "register": register,
                        "has_regular_subject": True,
                        "regular_subjects": regular_subjects,
                        "has_repeat_subject": True,
                        "repeatable_subjects": backpaper_subjects,
                        "is_repeat": False,
                    },
                )

            # Pass previous semester with no backpapers
            elif immediate_result.result == "pass" and not have_back:
                return request.render(
                    "cst_semester_registration.template_registration_form",
                    {
                        "student": student,
                        "register": register,
                        "has_regular_subject": True,
                        "regular_subjects": regular_subjects,
                        "has_repeat_subject": False,
                        "repeatable_subjects": backpaper_subjects,
                        "is_repeat": False,
                    },
                )

        # For Repeat Students compute new repeat modules
        else:
            # Is to find the result for that student with the creation_date nearest to the current date.
            today = datetime.today()
            closest_result = (
                request.env["cst.exam.result"]
                .sudo()
                .search(
                    [
                        ("student_id", "=", student.id),
                        ("start_date", "<=", today),
                    ],
                    order="start_date desc",
                    limit=1,
                )
            )

            if closest_result:
                term_id = closest_result.marksheet_id.term_id
                print("The term is: ", term_id.name)
                print("Backpapers are: ", backpaper_subjects)
                repeat_modules = self.compute_repeat_module(marks, term_id)
                print("Repeat Modules are: ", repeat_modules)

                backpaper_subjects = backpaper_subjects - repeat_modules

                have_back = bool(backpaper_subjects)

                print("Closest Result is: ", closest_result)
                print("Repeat Modules are: ", repeat_modules)
                return request.render(
                    "cst_semester_registration.template_registration_form",
                    {
                        "student": student,
                        "register": register,
                        "has_regular_subject": False,
                        "regular_subjects": regular_subjects,
                        "has_repeat_subject": have_back,
                        "repeatable_subjects": backpaper_subjects,
                        "is_repeat": True,
                        "repeat_modules": repeat_modules,
                    },
                )
            else:
                print("No exam result found.")

        # Students not eligible
        return request.render("cst_semester_registration.template_reg_not_eligible", {})

    # Helper Method
    # def create_registration(self, application):

    # def create_subject_registration(self, regular_subject_ids, repeat_subject_ids):

    def valid_number_of_subjects(self, total_subject):
        if total_subject <= 7:
            return True
        return False

    def get_fee_structure(self, fee_type):
        """Get the active fee structure for a given fee_type."""
        return (
            request.env["cst.fee.structure"]
            .sudo()
            .search([("fee_type", "=", fee_type), ("is_active", "=", True)], limit=1)
        )

    def generate_invoice_lines(
        self,
        main_fee_structure,
        repeat_fee_structure,
        backpaper_fee_structure,
        regular_subject_ids,
        is_repeat_subject_ids,
        backpaper_subject_ids,
    ):
        invoice_lines = []

        is_regular = bool(regular_subject_ids)
        is_repeat = bool(is_repeat_subject_ids)
        is_backpaper = bool(backpaper_subject_ids)

        # Case 1: Only Regular
        if is_regular and not is_repeat and not is_backpaper:
            if main_fee_structure:
                for product in main_fee_structure.fee_component_ids:
                    invoice_lines.append(
                        (
                            0,
                            0,
                            {
                                "product_id": product.id,
                                "name": product.name,
                                "quantity": 1,
                                "price_unit": product.lst_price,
                            },
                        )
                    )

        # Case 2: Regular + Backpaper
        elif is_regular and not is_repeat and is_backpaper:
            if main_fee_structure:
                for product in main_fee_structure.fee_component_ids:
                    invoice_lines.append(
                        (
                            0,
                            0,
                            {
                                "product_id": product.id,
                                "name": product.name,
                                "quantity": 1,
                                "price_unit": product.lst_price,
                            },
                        )
                    )
            if backpaper_fee_structure:
                backpaper_quantity = len(backpaper_subject_ids)
                for product in backpaper_fee_structure.fee_component_ids:
                    invoice_lines.append(
                        (
                            0,
                            0,
                            {
                                "product_id": product.id,
                                "name": product.name,
                                "quantity": backpaper_quantity,
                                "price_unit": product.lst_price,
                            },
                        )
                    )

        # Case 3: Repeat Only
        elif is_repeat and not is_backpaper:
            if repeat_fee_structure:
                repeat_quantity = len(is_repeat_subject_ids)
                for product in repeat_fee_structure.fee_component_ids:
                    invoice_lines.append(
                        (
                            0,
                            0,
                            {
                                "product_id": product.id,
                                "name": product.name,
                                "quantity": repeat_quantity,
                                "price_unit": product.lst_price,
                            },
                        )
                    )

        # Case 4: Repeat + Backpaper
        elif is_repeat and is_backpaper:
            if repeat_fee_structure:
                repeat_quantity = len(is_repeat_subject_ids)
                for product in repeat_fee_structure.fee_component_ids:
                    invoice_lines.append(
                        (
                            0,
                            0,
                            {
                                "product_id": product.id,
                                "name": product.name,
                                "quantity": repeat_quantity,
                                "price_unit": product.lst_price,
                            },
                        )
                    )
            if backpaper_fee_structure:
                backpaper_quantity = len(backpaper_subject_ids)
                for product in backpaper_fee_structure.fee_component_ids:
                    invoice_lines.append(
                        (
                            0,
                            0,
                            {
                                "product_id": product.id,
                                "name": product.name,
                                "quantity": backpaper_quantity,
                                "price_unit": product.lst_price,
                            },
                        )
                    )

        # Case 5: Only Backpaper
        elif not is_regular and not is_repeat and is_backpaper:
            if backpaper_fee_structure:
                backpaper_quantity = len(backpaper_subject_ids)
                for product in backpaper_fee_structure.fee_component_ids:
                    invoice_lines.append(
                        (
                            0,
                            0,
                            {
                                "product_id": product.id,
                                "name": product.name,
                                "quantity": backpaper_quantity,
                                "price_unit": product.lst_price,
                            },
                        )
                    )

        return invoice_lines

    # POST FORM end point
    @http.route(
        "/student/semester_registration/submit",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def submit_registration(self, **post):
        print("KWARGS: ", post)

        register_id = int(post.get("register_id"))
        student_id = int(post.get("student_id"))

        # Regular Subject IDs
        regular_subject_ids = list(
            map(int, request.httprequest.form.getlist("regular_subject_ids[]"))
        )
        if isinstance(regular_subject_ids, str):  # In case only one subject was checked
            regular_subject_ids = [int(regular_subject_ids)]
        else:
            regular_subject_ids = list(
                map(int, regular_subject_ids)
            )  # Convert all to integers
            # If it's already a list, map over i

        # Backpaper (Repeat) Subject IDs
        backpaper_subjects_raw = list(
            map(int, request.httprequest.form.getlist("repeat_subject_ids[]"))
        )
        if isinstance(backpaper_subjects_raw, str):
            backpaper_subjects_raw = [int(backpaper_subjects_raw)]
        else:
            backpaper_subjects_raw = list(map(int, backpaper_subjects_raw))

        # Is Repeat Subject IDs (for additional flagging if necessary)
        is_repeat_subjects_raw = list(
            map(int, request.httprequest.form.getlist("is_repeat_subject_ids[]"))
        )
        if isinstance(is_repeat_subjects_raw, str):
            is_repeat_subjects_raw = [int(is_repeat_subjects_raw)]
        else:
            is_repeat_subjects_raw = list(map(int, is_repeat_subjects_raw))

        # Print to verify
        print("Register ID:", register_id)
        print("Student ID:", student_id)
        print("Regular Subjects:", regular_subject_ids)
        print("Backpaper Subjects:", backpaper_subjects_raw)
        print("Is Repeat Subjects:", is_repeat_subjects_raw)

        # Check if the submission is valid.
        # Total subjects
        total_subjects = (
            len(regular_subject_ids)
            + len(backpaper_subjects_raw)
            + len(is_repeat_subjects_raw)
        )

        # Call the function
        valid_number_of_subjects = self.valid_number_of_subjects(total_subjects)
        if not valid_number_of_subjects:
            return request.render(
                "cst_semester_registration.template_invalid_number_of_subjects", {}
            )

        # First Compute Total Fees Required
        student = request.env["op.student"].sudo().browse(student_id)
        scholarship_category = (
            student.scholarship_id.category if student.scholarship_id else "gov"
        )

        # Registration Type
        """
            To identify regular-> will have data in regular_subject_ids
            To identify regular with backpaper -> will have data in regular_subject_ids and backpaper_subjects_raw
            To identify repeat -> will have data in is_repeat_subjects_raw
            To identify repeat with backpaper -> will have data in is_repeat_subjects_raw and backpaper_subjects_raw
            To identify only back -> only have data in backpaper_subjects_raw

            Only Regular -> Fee calculation based on scholarship 
            Regular with backpaper -> Fee calculation based on scholarship and repeat_fee_structure
            Repeat -> Fee calculation based on repeat 
            Repeat with backpaper -> Fee calculation based only on repeat and backpaper fee structure
            Only back -> Fee caclculation based on backpaper
        """
        # Create Invoice on model account.move if inovie line is not 0 else go and render thank you page after creatinf registratuon and subject regis
        # Main Fee Structure
        main_fee_structure = self.get_fee_structure(fee_type=scholarship_category)

        # Repeat Fee Structure (only if repeat subjects exist)
        repeat_fee_structure = None
        if is_repeat_subjects_raw:
            repeat_fee_structure = self.get_fee_structure(fee_type="repeat_module_fee")

        # Backpaper Fee Structure (only if backpaper subjects exist)
        backpaper_fee_structure = None
        if backpaper_subjects_raw:
            backpaper_fee_structure = self.get_fee_structure(fee_type="back_paper")

        invoice_lines = self.generate_invoice_lines(
            main_fee_structure,
            repeat_fee_structure,
            backpaper_fee_structure,
            regular_subject_ids,
            is_repeat_subjects_raw,
            backpaper_subjects_raw,
        )
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
        invoice_id = False
        if invoice:
            invoice_id = invoice.id

        # Create Registration on model cst.registration
        registration_vals = {
            "register_id": register_id,
            "student_id": student_id,
            "invoice_id": invoice_id,
        }
        registration = request.env["cst.registration"].sudo().create(registration_vals)

        # Create Subject Registration on model student.subject.registration
        # Create Subject Registrations
        registration_records = []

        # Regular Subjects
        for subject_id in regular_subject_ids:
            registration_records.append(
                (
                    0,
                    0,
                    {
                        "subject_id": int(subject_id),
                        "registration_type": "regular",
                        "registration_id": int(registration.id),
                    },
                )
            )

        # Backpaper Subjects
        for subject_id in backpaper_subjects_raw:
            registration_records.append(
                (
                    0,
                    0,
                    {
                        "subject_id": int(subject_id),
                        "registration_type": "backpaper",
                        "registration_id": int(registration.id),
                    },
                )
            )

        # Repeat Subjects
        for subject_id in is_repeat_subjects_raw:
            registration_records.append(
                (
                    0,
                    0,
                    {
                        "subject_id": int(subject_id),
                        "registration_type": "repeat",
                        "registration_id": int(registration.id),
                    },
                )
            )

        # Now create the records
        request.env["student.subject.registration"].sudo().create(
            [reg[2] for reg in registration_records]
        )

        if invoice:
            # Render
            return request.redirect(f"/my/invoices?sortby=state&filterby=invoices")
        return request.render(
            "cst_semester_registration.template_thank_you_registration", {}
        )

    @http.route(
        "/student/my/semester_registration", type="http", auth="user", website=True
    )
    def view_my_registration(self, **kwargs):
        denied = self._check_student_group()
        if denied:
            return denied

        student = (
            request.env["op.student"]
            .sudo()
            .search([("user_id", "=", request.env.user.id)], limit=1)
        )

        registration = (
            request.env["cst.registration"]
            .sudo()
            .search(
                [("student_id", "=", student.id)], order="create_date desc", limit=1
            )
        )

        if not registration:
            return request.redirect("/student/semester_registration")

        return request.render(
            "cst_semester_registration.view_my_registration",
            {"registration": registration},
        )
