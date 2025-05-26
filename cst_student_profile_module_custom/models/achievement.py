from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StudentAchievement(models.Model):
    _name = "cst.student.achievement"
    _description = "Student Achievements and Certificates"
    _rec_name = "student_id"

    student_id = fields.Many2one("op.student", string="Student", required=True)
    student_number = fields.Char(
        string="Student Number", related="student_id.student_number", store=True
    )
    achievement_name = fields.Char(string="Achievement Name", required=True)
    achievement_description = fields.Text(string="Achievement Description")
    certificate_filename = fields.Char(
        string="Certificate Filename", compute="_compute_certificate_name"
    )

    certificate_file = fields.Binary(
        string="Certificate (Image or PDF)", required=False
    )

    achievement_date = fields.Date(string="Achievement Date ", required=True)

    @api.depends("achievement_name", "student_id")
    def _compute_certificate_name(self):
        for record in self:
            if record.achievement_name and record.student_id:
                record.certificate_filename = (
                    f"{record.student_number}_{record.achievement_name}_certificate"
                )
            else:
                record.certificate_filename = "Untitled_Certificate"
