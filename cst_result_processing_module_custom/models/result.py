import logging
from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)  # Create a logger


class Result(models.Model):
    _name = "cst.exam.result"
    _description = "Result Declaration"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
    ]

    # -----------
    # Attributes
    # -----------
    name = fields.Char(string="Name", compute="_compute_name", store=True)

    result = fields.Selection(
        [("pass", "Pass"), ("fail", "Fail")],
        string="Result",
        compute="_compute_result",
        store=True,
    )

    percentage = fields.Float(
        "Total Percentage", compute="_total_percentage", store=True
    )
    marks_ids = fields.One2many("cst.exam.mark", "result_id", string="Exam Marks ID")
    student_id = fields.Many2one(
        "op.student", compute="compute_student_id", string="Student", store=True
    )

    student_number = fields.Char(
        string="Student Number", compute="compute_student_number", store=True
    )
    marksheet_id = fields.Many2one(
        "cst.exam.marksheet",
        compute="compute_marksheet_id",
        store=True,
    )
    start_date = fields.Datetime(related="marksheet_id.start_date", store=True)
    total_marks = fields.Float(string="Total Marks")

    # ----------
    # Computation Methods
    # ----------
    @api.depends("student_number", "marksheet_id.term_id", "marksheet_id.exam_type")
    def _compute_name(self):
        for rec in self:
            semester = (
                rec.marksheet_id.term_id.name
                if rec.marksheet_id and rec.marksheet_id.term_id
                else ""
            )
            student_num = rec.student_number or ""
            exam_type = (
                rec.marksheet_id.exam_type
                if rec.marksheet_id and rec.marksheet_id.exam_type
                else ""
            )
            rec.name = f"{student_num} {semester} {exam_type} Result".strip()

    @api.depends("marks_ids")
    def compute_marksheet_id(self):
        for rec in self:
            if rec.marks_ids:
                rec.marksheet_id = rec.marks_ids[0].marksheet_id
            else:
                rec.marksheet_id = False

    @api.depends("marks_ids")
    def compute_student_id(self):
        for rec in self:
            if rec.marks_ids:
                rec.student_id = rec.marks_ids[0].student_id
            else:
                rec.student_id = False

    def update_reassessment_remarks_to_fail(self):
        for rec in self:
            if not rec.student_id:
                _logger.warning(f"Student ID missing for Result ID: {rec.id}")
                continue

            print(
                f"Updating RA remarks for Student ID: {rec.student_id.id}, Result ID: {rec.id}"
            )

            related_marks = self.env["cst.exam.mark"].search(
                [
                    ("student_id", "=", rec.student_id.id),
                    ("result_id", "=", rec.id),
                    ("remarks", "in", ["ra", "failed_ra"]),
                ]
            )

            print(f"Found related marks: {related_marks}")

            if related_marks:
                related_marks.write({"remarks": "fail"})
                print(f"Updated {len(related_marks)} mark(s) to 'fail'")
            else:
                print(
                    f"No related marks found for Student ID {rec.student_id.id} and Result ID {rec.id}"
                )

    # FOR MANUAL COMPUTATION OF RESULT NOT USED FOR AUTO GEENRATEING RESULTS
    @api.depends("marks_ids.student_id")
    def compute_result(self):
        for rec in self:
            if rec.marksheet_id.exam_type == "ra":
                rec.result = False
                rec.percentage = False
                continue

            total_marks = 0
            count = 0
            fail_count = 0

            for mark in rec.marks_ids:
                total_marks += mark.final_total_marks
                count += 1
                if mark.remarks in ["fail", "ra", "failed_ra"]:
                    fail_count += 1

            rec.total_marks = total_marks
            rec.percentage = (total_marks / (count * 100)) * 100 if count else 0

            if fail_count > 3 or rec.percentage < 50:
                rec.result = "fail"
                print("Hellodojdaisojdioasiojdiosaiodj")
                rec.update_reassessment_remarks_to_fail()
            else:
                rec.result = "pass"

    @api.depends("student_id")
    def compute_student_number(self):
        for record in self:
            # Check if student_id exists
            if record.student_id:
                record.student_number = record.student_id.student_number
            else:
                record.student_number = ""

    @api.model
    def create(self, vals):
        record = super(Result, self).create(vals)
        if record.result == "fail" and record.marksheet_id.exam_type == "regular":
            record.update_reassessment_remarks_to_fail()
        return record
