from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AcademicTermManagement(models.Model):
    _inherit = "op.academic.term"

    is_active = fields.Boolean(string="Is Active", store=True)

    @api.constrains("is_active", "academic_year_id")
    def _check_only_one_active(self):
        """Ensure only one active academic term per academic year at a time"""
        for term in self:
            if term.is_active:
                # Search for any other active term in the same academic year
                active_terms = self.search(
                    [
                        ("is_active", "=", True),
                        ("academic_year_id", "=", term.academic_year_id.id),
                        ("id", "!=", term.id if term.id else False),
                    ]
                )
                if active_terms:
                    raise ValidationError(
                        "There can only be one active academic term per academic year."
                    )
