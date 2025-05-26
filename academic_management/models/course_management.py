from odoo import api, fields, models


class CourseManagement(models.Model):
    _inherit = "op.course"

    module_ids = fields.One2many("cst.offer.module", "course_id", string="Modules")

    departments_id = fields.Many2one("hr.department", "Department", required=True)

    programme_leader_id = fields.Many2one(
        "hr.employee", "Programme Leader", required=True
    )
