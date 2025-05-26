import logging
from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)  # Create a logger


class ExamMarks(models.Model):
    _name = "cst.exam.mark"
    _description = "Mark Model"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
    ]
    student_id = fields.Many2one("op.student", string="Student Name")
    student_number = fields.Char(
        compute="compute_student_number", string="Student Number", store=True
    )
    marksheet_subject_id = fields.Many2one(
        "marksheet.subject.rel",
        string="Marksheet - Subject",
        required=True,
    )
    state = fields.Selection(
        "marksheet.subject.rel", related="marksheet_subject_id.state", store=True
    )
    subject_id = fields.Many2one(
        "op.subject",
        string="Subject",
        related="marksheet_subject_id.subject_id",
        store=True,  # Store in DB for better performance
        readonly=True,  # Prevent manual editing
    )
    tutor_id = fields.Many2one(
        "hr.employee",
        string="Mark Uploader",
        related="marksheet_subject_id.tutor_id",
    )
    marksheet_id = fields.Many2one(
        "cst.exam.marksheet",
        string="Marksheet",
        related="marksheet_subject_id.marksheet_id",
        store=True,
        readonly=True,
    )
    exam_type = fields.Selection(
        "cst.exam.marksheet",
        related="marksheet_id.exam_type",
        store=True,
        readonly=True,
    )
    subject_type = fields.Selection(
        related="subject_id.moduletype",
        string="Module Type",
        readonly=True,
    )
    subject_code = fields.Char(
        related="subject_id.code",
        string="Module Code",
        readonly=True,
    )
    credit = fields.Float(
        "Credit", related="subject_id.credit", readonly=True, store=True
    )
    ca_weightage = fields.Float(
        "CA", related="subject_id.ca_weightage", readonly=True, store=True
    )
    practical_weightage = fields.Float(
        "Practical", related="subject_id.practical_weightage", readonly=True, store=True
    )
    exam_weightage = fields.Float(
        "Exam", related="subject_id.exam_weightage", readonly=True, store=True
    )
    ca_marks = fields.Float(string="CA", default=0.0)
    practical_marks = fields.Float(string="Practical", default=0.0)
    exam_marks = fields.Float(string="Final Exam", default=0.0)
    mark_type = fields.Selection(
        [
            ("regular", "Resular"),
            ("ra", "Re-assessment"),
            ("repeat", "repeat"),
        ],
        store=True,
        readonly=True,
        compute="compute_mark_type",
    )
    total_marks = fields.Float(
        string="Total Marks", default=0.0, compute="calculate_total_marks"
    )
    final_total_marks = fields.Float(
        string="Total Marks Obtained",
        compute="compute_final_total_marks",
        readonly=True,
    )
    remarks = fields.Selection(
        [
            ("pass", "Pass"),
            ("fail", "Fail"),
            ("ra", "Re-assessment"),
            ("pass_ra", "Passed Re-assessment"),
            ("failed_ra", "Failed Re-assessment"),
        ],
        string="Remarks",
        compute="compute_remarks",
        store=True,
    )
    is_deferred = fields.Boolean(string="Defer exam", default=False)
    is_repeat_student = fields.Boolean(string="Repeat Student", default=False)
    result_id = fields.Many2one("cst.exam.result", string="Result")

    # ---Helper Methods
    def check_mark_validity(self, vals):
        for rec in self:
            if vals.get("ca_marks", 0) > vals.get("ca_weightage", rec.ca_weightage):
                raise ValidationError("CA Marks cannot exceed CA Weightage.")
            if vals.get("practical_marks", 0) > vals.get(
                "practical_weightage", rec.practical_weightage
            ):
                raise ValidationError(
                    "Practical Marks cannot exceed Practical Weightage."
                )
            if vals.get("exam_marks", 0) > vals.get(
                "exam_weightage", rec.exam_weightage
            ):
                raise ValidationError("Exam Marks cannot exceed Exam Weightage.")

    @api.depends("total_marks", "remarks", "exam_type", "is_deferred")
    def compute_final_total_marks(self):
        for rec in self:
            # Default: Use computed total_marks
            rec.final_total_marks = rec.total_marks

            # Special case: Passed RA and not deferred
            if (
                rec.exam_type == "ra"
                and rec.remarks in ("pass", "pass_ra")  # Ensure it passed
                and not rec.is_deferred
            ):
                rec.final_total_marks = 50.00

    def _evaluate_remark(self, pass_label, fail_label):
        for rec in self:
            if rec.total_marks < 50:
                rec.remarks = fail_label
                continue

            if rec.subject_type == "with_practical":
                if (
                    rec.ca_marks <= rec.ca_weightage * 0.4
                    or rec.practical_marks <= rec.practical_weightage * 0.4
                    or rec.exam_marks <= rec.exam_weightage * 0.4
                ):
                    rec.remarks = fail_label
                else:
                    rec.remarks = pass_label

            elif rec.subject_type == "without_practical":
                if (
                    rec.ca_marks <= rec.ca_weightage * 0.4
                    or rec.exam_marks <= rec.exam_weightage * 0.4
                ):
                    rec.remarks = fail_label
                else:
                    rec.remarks = pass_label

            elif rec.subject_type == "without_exam":
                if rec.ca_marks <= rec.ca_weightage * 0.4:
                    rec.remarks = fail_label
                else:
                    rec.remarks = pass_label

            if rec.exam_type == "ra":
                if rec.remarks == pass_label and not rec.is_deferred:
                    print("##########TOTAL MARKS: 50")
                    rec.total_marks = 50.00

    @api.depends("state")
    def compute_remarks(self):
        for rec in self:
            if rec.state == "validated":
                if rec.exam_type == "regular":
                    rec._evaluate_remark(pass_label="pass", fail_label="ra")
                else:
                    rec._evaluate_remark(pass_label="pass_ra", fail_label="failed_ra")
            else:
                rec.remarks = False

    @api.depends("ca_marks", "practical_marks", "exam_marks")
    def calculate_total_marks(self):
        for rec in self:
            rec.total_marks = (
                rec.total_marks + rec.ca_marks + rec.practical_marks + rec.exam_marks
            )

    # ---Actions
    @api.depends("student_id")
    def compute_student_number(self):
        for record in self:
            # Check if student_id exists
            if record.student_id:
                record.student_number = record.student_id.student_number
            else:
                record.student_number = ""

    @api.depends("marksheet_id")
    def compute_mark_type(self):
        for record in self:
            if record.is_repeat_student:
                record.mark_type = "repeat"
                break

            if record.marksheet_id.exam_type == "regular":
                record.mark_type = "regular"
                break

            if record.marksheet_id.exam_type == "ra":
                record.mark_type = "ra"
                break

    # ----ORM
    @api.model_create_multi
    def create(self, val_list):
        for vals in val_list:
            self.check_mark_validity(vals)

        marks = super(ExamMarks, self).create(val_list)
        return marks

    def write(self, vals):
        self.check_mark_validity(vals)
        marks = super(ExamMarks, self).write(vals)
        return marks
