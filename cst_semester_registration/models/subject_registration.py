from odoo import fields, models


class StudentSubjectRegistration(models.Model):
    _name = "student.subject.registration"
    _description = "Student Subject Registration"

    # student_id = fields.Many2one('op.student', string='Student', required=True)
    subject_id = fields.Many2one("op.subject", string="Modules", required=True)
    registration_type = fields.Selection(
        [("regular", "Regular"), ("backpaper", "Backpaper"), ("repeat", "Repeat")],
        string="Registration Type",
        required=True,
    )
    registration_id = fields.Many2one(
        "cst.registration", string="Registration", ondelete="cascade"
    )

    _sql_constraints = [
        (
            "unique_subject_per_term",
            "unique(student_id, subject_id, registration_id)",
            "Already registered for this subject in this term",
        )
    ]
