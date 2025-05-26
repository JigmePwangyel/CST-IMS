from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class activity(models.Model):
    _inherit = "op.activity"
    student_number = fields.Char(
        string="Student Number", related="student_id.student_number", store=True
    )


class Leadership(models.Model):
    _name = "cst.leadership"
    _description = "Student Activity"
    _rec_name = "student_id"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    student_id = fields.Many2one("op.student", "Student", required=True)
    type_id = fields.Many2one("cst.leadership.type", "Leadership Type")
    description = fields.Text("Description")
    from_date = fields.Date("From (Date)")
    to_date = fields.Date("To (Date)")
    active = fields.Boolean(default=True)

    student_number = fields.Char(
        string="Student Number", related="student_id.student_number", store=True
    )


class LeadershipType(models.Model):
    _name = "cst.leadership.type"
    _description = "Leadership Type"

    name = fields.Char("Name", size=128, required=True)
