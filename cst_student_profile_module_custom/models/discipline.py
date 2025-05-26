from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class Disciplinary(models.Model):
    _name = "cst.student.discipline"
    _description = "Records student's discipline"
    _rec_name = "student_id"

    student_id = fields.Many2one("op.student", "Student", required=True)
    student_number = fields.Char(
        string="Student Number", related="student_id.student_number", store=True
    )

    offense_id = fields.Many2one(
        "cst.student.offense.type", string="Offense Type", required=True
    )
    offense_description = fields.Text(string="Offense Description", required=True)
    reported_by = fields.Many2one(
        "hr.employee", string="Reported By Staff", required=True
    )
    incident_date = fields.Date(string="Incident Date", required=True)
    disciplinary_action = fields.Selection(
        [
            ("warning", "Warning"),
            ("suspension", "Suspension"),
            ("expulsion", "Expulsion"),
            ("community_service", "Community Service"),
            ("other", "Other"),
        ],
        string="Disciplinary Action",
        required=True,
    )
    action_description = fields.Text(string="Action Description")

    remarks = fields.Text(string="Remarks")

    @api.model
    def _search_student_number(self, operator, value):
        """Allow search by student number"""
        student_ids = (
            self.env["op.student"].search([("student_number", operator, value)]).ids
        )
        return [("student_id", "in", student_ids)]


class OffenseType(models.Model):
    _name = "cst.student.offense.type"
    _description = "Student Offense Type"

    name = fields.Char(string="Name")
