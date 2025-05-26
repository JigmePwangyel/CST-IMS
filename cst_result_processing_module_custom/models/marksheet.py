import logging
from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError

# Initialize logger
_logger = logging.getLogger(__name__)


class Marksheet(models.Model):
    _name = "cst.exam.marksheet"
    _description = "Marksheet Declaration"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
    ]

    # ------------------------------
    # Attributes of CST student marksheet
    # ------------------------------
    name = fields.Char("Marksheet Name", copy=False, required=True)
    exam_type = fields.Selection(
        [
            ("regular", "Regular Exam"),
            ("ra", "Re-assessment Exam"),
        ],
        string="Exam Type",
        required=True,
        tracking=True,
    )
    start_date = fields.Datetime(
        "Start Date",
        required=True,
        tracking=True,
        default=lambda self: date.today(),
    )
    end_date = fields.Datetime(
        "End Date",
        required=True,
        tracking=True,
        default=lambda self: date.today(),
    )
    batch_id = fields.Many2one("op.batch", string="Batch", required=True, tracking=True)
    course_id = fields.Many2one(
        "op.course", related="batch_id.course_id", string="Programme"
    )
    term_id = fields.Many2one(
        "op.academic.term",
        domain=[("is_active", "=", True)],
        string="Academic Term",
        required=True,
        tracking=True,
    )
    date_of_declaration = fields.Date(
        string="Date of Declaration", default=None, compute="compute_declaration_date"
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("declared", "Declared"),
        ],
        string="State",
        default="draft",
        tracking=True,
    )
    module_count = fields.Integer(compute="compute_module_count")
    result_count = fields.Integer(compute="compute_result_count")

    # --------
    # Computed Methods
    # --------
    @api.depends("state")
    def compute_declaration_date(self):
        for rec in self:
            if rec.state == "declared":
                rec.date_of_declaration = date.today()
            elif not rec.state == "declared":
                rec.date_of_declaration = None

            else:
                rec.date_of_declaration = None

    # -------
    # Constrains
    # -------
    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.start_date > record.end_date:
                    raise ValidationError("Start date cannot be after the end date.")

    # --Helper methods
    def compute_regular_result(self):
        for marksheet in self:
            marks = self.env["cst.exam.mark"].search(
                [("marksheet_subject_id.marksheet_id", "=", marksheet.id)]
            )
            student_ids = marks.mapped("student_id")
            for student in student_ids:
                student_marks = marks.filtered(lambda m: m.student_id.id == student.id)

                is_repeat = any(mark.is_repeat_student for mark in student_marks)

                if is_repeat:
                    percentage = None
                    result = None
                else:
                    total_obtained = sum(student_marks.mapped("final_total_marks"))
                    total_possible = len(student_marks) * 100
                    percentage = (
                        (total_obtained / total_possible) * 100 if total_possible else 0
                    )

                    fail_count = len(
                        student_marks.filtered(lambda m: m.remarks in ["ra", "fail"])
                    )

                    result = (
                        "fail"
                        if fail_count > 3
                        else "pass" if percentage >= 40 else "fail"
                    )

                self.env["cst.exam.result"].create(
                    {
                        "student_id": student.id,
                        "marksheet_id": marksheet.id,
                        "percentage": percentage,
                        "result": result,
                        "marks_ids": [(6, 0, student_marks.ids)],
                    }
                )

    def compute_ra_result(self):
        Mark = self.env["cst.exam.mark"]

        for marksheet in self:
            course_id = marksheet.course_id.id
            term_id = marksheet.term_id.id

            current_marksheet_id = marksheet.id
            # 1. Get all marks linked directly to the current marksheet
            marksheet_subject_lines = self.env["marksheet.subject.rel"].search(
                [("marksheet_id", "=", marksheet.id)]
            )

            current_marks = marksheet_subject_lines.mapped("marks_id")

            # 2. Get unique (student_id)s involved in this marksheet
            student_ids = current_marks.mapped("student_id").ids

            # 3. Filter all marks based on (student_id, term_id, course_id)
            all_relevant_marks = Mark.search(
                [
                    ("student_id", "in", student_ids),
                    ("marksheet_subject_id.term_id", "=", term_id),
                    ("marksheet_subject_id.course_id", "=", course_id),
                ]
            )

            # 4. Compute percentage for each student
            for student_id in student_ids:
                student_marks = all_relevant_marks.filtered(
                    lambda m: m.student_id.id == student_id
                )

                # Dictionary to store best mark per subject
                unique_subject_marks = {}
                for mark in student_marks:
                    subj_id = mark.subject_id.id
                    existing = unique_subject_marks.get(subj_id)

                    if not existing:
                        unique_subject_marks[subj_id] = mark
                    else:
                        # Prefer 'ra' if available
                        if mark.mark_type == "ra" and existing.mark_type != "ra":
                            unique_subject_marks[subj_id] = mark
                        # If same type, keep the existing (first one)

                selected_marks = unique_subject_marks.values()

                total_marks = sum(m.final_total_marks for m in selected_marks)
                count = len(selected_marks)
                percentage = total_marks / count if count > 0 else 0

                # Print each record for the student
                print(
                    f"Student ID: {student_id} | Total Marks: {total_marks} | Number of Records: {count} | Percentage: {percentage:.2f}%"
                )

                # Also print all individual marks for the student
                print("All Marks: ")
                for mark in student_marks:
                    print(
                        f"Mark ID: {mark.id} | Subject: {mark.marksheet_subject_id.subject_id.name} | Final Marks: {mark.final_total_marks}"
                    )

                # Print marks used in percentage computation
                print("Marks Used in Percentage Calculation:")
                for mark in selected_marks:
                    print(
                        f"✔ Mark ID: {mark.id} | Subject: {mark.marksheet_subject_id.subject_id.name} | Final Marks: {mark.final_total_marks} | Type: {mark.mark_type}"
                    )

                print("-" * 50)  # Separator between students' records

                # If you have a percentage field to store in mark or another model, update it here
                # Filter only 'ra' type marks
                ra_marks = student_marks.filtered(lambda m: m.mark_type == "ra")

                # Create the result with only RA marks in marks_ids
                self.env["cst.exam.result"].create(
                    {
                        "student_id": student_id,
                        "marksheet_id": current_marksheet_id,
                        "percentage": percentage,
                        "result": False,
                        "marks_ids": [(6, 0, ra_marks.ids)],
                    }
                )

    # -- Business Logic Function

    def declare_marksheet(self):
        for marksheet in self:
            if marksheet.state == "declared":
                if marksheet.exam_type == "regular":
                    marksheet.compute_regular_result()
                else:
                    marksheet.compute_ra_result()

    # -------
    # Actions
    # -------
    def action_confirm(self):
        for rec in self:
            if rec.state == "draft":  # Allow state transition only from draft
                rec.state = "confirmed"
            else:
                raise ValidationError("Cannot confirm, as the state is not draft.")

    def action_declare(self):
        for rec in self:
            if rec.state != "confirmed":
                raise ValidationError("Cannot declare, as the state is not confirmed")

            subject_rels = self.env["marksheet.subject.rel"].search(
                [("marksheet_id", "=", rec.id)]
            )
            not_validated = subject_rels.filtered(lambda s: s.state != "validated")
            if not_validated:
                subject_names = ", ".join(not_validated.mapped("subject_id.name"))
                raise ValidationError(
                    f"Cannot declare marksheet because the following subjects are not validated:\n{subject_names}"
                )

            # Proceed with declaration
            rec.state = "declared"
            rec.declare_marksheet()

    def action_reset(self):
        for rec in self:
            if rec.state == "confirmed" or "declared":
                self.state = "draft"
            else:
                raise ValidationError(
                    "You can only reset a confirmed or a declared marksheet."
                )

    def compute_module_count(self):
        for rec in self:
            module_count = self.env["marksheet.subject.rel"].search_count(
                [("marksheet_id", "=", self.ids)]
            )
            rec.module_count = module_count

    def get_modules(self):
        self.ensure_one()

        # Get the existing action
        action = self.env.ref(
            "cst_result_processing_module_custom.action_open_upload_marks"
        )

        # You can modify the domain or context if needed
        action = action.read()[0]  # Read the action and get the dictionary

        # Modify the domain or context if necessary
        action["domain"] = [("marksheet_id", "=", self.id)]  # Or self.ids if needed

        return action

    def compute_result_count(self):
        for rec in self:
            result_count = self.env["cst.exam.result"].search_count(
                [("marksheet_id", "=", self.ids)]
            )
            rec.result_count = result_count

    def get_results(self):
        self.ensure_one()
        action = self.env.ref("cst_result_processing_module_custom.action_open_result")
        action = action.read()[0]
        action["domain"] = [("marksheet_id", "=", self.id)]
        return action

    # --------
    # ---
    # ORM methods
    # -----------

    @api.model_create_multi
    def create(self, vals_list):
        marksheets = super(Marksheet, self).create(vals_list)

        subject_rel_vals = []
        for marksheet in marksheets:
            subjects = self.env["cst.offer.module"].search(
                [
                    ("batch_ids", "=", marksheet.batch_id.id),
                    ("term_id", "=", marksheet.term_id.id),
                    ("course_id", "=", marksheet.course_id.id),
                ]
            )

            if not subjects:
                _logger.warning(
                    f"No subjects found for batch {marksheet.batch_id.id}, term {marksheet.term_id.id}, course {marksheet.course_id.id}"
                )
            for subject in subjects:
                for subject_record in subject.subject_ids:
                    subject_rel_vals.append(
                        {
                            "marksheet_id": marksheet.id,
                            "subject_id": subject_record.id,  # Here subject_record refers to each record in the many2many field
                        }
                    )

        if subject_rel_vals:
            self.env["marksheet.subject.rel"].create(subject_rel_vals)

        return marksheets


class MarksheetSubject(models.Model):
    _name = "marksheet.subject.rel"
    _description = "Marksheet - Subject Relation"
    _inherit = ["mail.thread"]
    _rec_name = "display_name"
    marksheet_id = fields.Many2one(
        "cst.exam.marksheet",
        string="Marksheet",
        required=True,
        help="Specify the marksheet",
    )
    marksheet_status = fields.Selection(related="marksheet_id.state", readonly=True)
    exam_type = fields.Selection(
        [
            ("regular", "Regular Exam"),
            ("ra", "Re-assessment Exam"),
        ],
        string="Exam Type",
        related="marksheet_id.exam_type",
    )
    term_id = fields.Many2one(
        "op.academic.term",
        domain=[("is_active", "=", True)],
        string="Academic Term",
        related="marksheet_id.term_id",
    )
    subject_id = fields.Many2one(
        "op.subject",
        string="Subject",
        required=True,
        help="Specify the subject",
    )
    tutor_id = fields.Many2one(
        "hr.employee",
        string="Tutor",
        store=True,
    )
    subject_type = fields.Selection("op.subject", related="subject_id.moduletype")
    ca_weightage = fields.Float("op.subject", related="subject_id.ca_weightage")
    practical_weightage = fields.Float(
        "op.subject", related="subject_id.practical_weightage"
    )
    exam_weightage = fields.Float("op.subject", related="subject_id.exam_weightage")
    credit = fields.Float(
        "Credit", related="subject_id.credit", readonly=True, store=True
    )
    marks_id = fields.One2many(
        "cst.exam.mark",  # Child model
        "marksheet_subject_id",  # The field in the child model that links to the parent
        string="Student Marks",
    )

    # Computed name to show in UI
    display_name = fields.Char(compute="_compute_display_name")
    batch_id = fields.Many2one("op.batch", related="marksheet_id.batch_id")
    course_id = fields.Many2one(
        "op.course",
        string="Programme",
        related="marksheet_id.course_id",
    )
    term_id = fields.Many2one(
        "op.academic.term",
        related="marksheet_id.term_id",
    )
    subject_ids_domain = fields.Binary(
        string="Subjects Domain", compute="_get_subject_domain"
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("marks_uploading", "Marks Uploading"),
            ("confirmed", "Confirmed"),
            ("validated", "Validated"),
        ],
        string="State",
        default="draft",
        tracking=True,
    )
    is_editable_now = fields.Boolean(
        "Is Editable Now", compute="_compute_is_editable_now", store=True
    )
    start_datetime = fields.Datetime(related="marksheet_id.start_date")
    end_datetime = fields.Datetime(related="marksheet_id.end_date")

    # ----Helper Methods
    @api.depends("start_datetime", "end_datetime")
    def _compute_is_editable_now(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_editable_now = bool(
                rec.start_datetime
                and rec.end_datetime
                and rec.start_datetime <= now <= rec.end_datetime
            )

    @api.depends("subject_id")
    def _compute_tutor_id(self):
        for rec in self:
            rec.tutor_id = rec.subject_id.tutor_id if rec.subject_id else False

    @api.depends("marksheet_id", "subject_id")
    def _compute_display_name(self):
        for record in self:
            record.display_name = (
                f"{record.marksheet_id.name} - {record.subject_id.name}"
            )

    @api.depends("marksheet_id")
    def _get_subject_domain(self):
        offer_modules = self.env["cst.offer.module"].search(
            [
                ("course_id", "=", self.course_id.id),
                ("term_id", "=", self.term_id.id),
                ("batch_ids", "=", self.batch_id.id),
            ]
        )
        subject_ids = offer_modules.mapped("subject_ids")
        _logger.info(
            f"Setting subject_id domain with matching subject IDs: {subject_ids.ids}"
        )
        for rec in self:
            rec.subject_ids_domain = [("id", "in", subject_ids.ids)]

    # ---Action for buttons
    def mark_upload(self):
        self.state = "marks_uploading"

    def confirm_upload(self):
        self.state = "confirmed"

    def validate_upload(self):
        self.state = "validated"

    def action_reset(self):
        self.state = "draft"

    # ---ORM Methods
    # ---Helper Methods
    def _prepare_vals_set_tutor(self, vals_list):
        """Set tutor_id in vals if missing based on subject."""
        for vals in vals_list:
            if not vals.get("tutor_id") and vals.get("subject_id"):
                subject = self.env["op.subject"].browse(vals["subject_id"])
                if subject and subject.tutor_id:
                    vals["tutor_id"] = subject.tutor_id.id

    def _create_student_marks(self):
        """Create related student marks for this record."""
        if not self.batch_id:
            return  # Safety check: no batch, no students

        students = self.env["op.student"].search(
            [
                ("batch_id", "=", self.batch_id.id),
            ]
        )

        mark_vals = []
        for student in students:
            mark_vals.append(
                {
                    "marksheet_subject_id": self.id,
                    "student_id": student.id,
                    # Add other default values if needed
                }
            )

        if mark_vals:
            self.env["cst.exam.mark"].create(mark_vals)

    @api.model_create_multi
    def create(self, vals_list):
        # 1. Prepare values (set tutor_id if missing)
        self._prepare_vals_set_tutor(vals_list)

        # 2. Create the main records
        records = super(MarksheetSubject, self).create(vals_list)

        # 3. For each record, create student marks
        for record in records:
            record._create_student_marks()

        return records
