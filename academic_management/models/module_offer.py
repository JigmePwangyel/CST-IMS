import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class OfferModule(models.Model):
    _name = "cst.offer.module"
    _description = "Offer Module for students"

    course_id = fields.Many2one("op.course", string="Course")
    term_id = fields.Many2one(
        "op.academic.term",
        domain=[("is_active", "=", True)],
        string="Academic Term",
        required=True,
    )

    subject_ids = fields.Many2many(
        "op.subject",
        "subject_offer_module_rel",
        "offer_module_id",
        "subject_id",
        string="Offer Module",
        ondelete="cascade",
    )

    batch_ids = fields.Many2one("op.batch", string="Batch")
    year = fields.Integer("Year", compute="_compute_year", store=True)

    @api.depends("batch_ids")
    def _compute_year(self):
        for record in self:
            record.year = record.batch_ids.year if record.batch_ids else 0

    _sql_constraints = [
        (
            "unique_batch_module",
            "unique(batch_ids)",
            "A batch can only be assigned to a module once!",
        )
    ]

    # --Helper methods
    def _update_subject_is_offered(self, subject_ids):
        for subject in subject_ids:
            if not subject:
                continue
            if subject:
                subject.is_offered = bool(
                    self.env["cst.offer.module"].search(
                        [("subject_ids", "in", subject.id)]
                    )
                )

    # ORM Methods
    @api.model
    def create(self, vals):
        # Create the OfferModule record
        record = super(OfferModule, self).create(vals)

        self._update_subject_is_offered(record.subject_ids)
        return record

    def write(self, vals):
        old_subject_ids = set(
            self.subject_ids.ids
        )  # Store old subject IDs before update
        result = super(OfferModule, self).write(
            vals
        )  # Returns True/False, not recordset

        if result:  # Ensure write was successful
            new_subject_ids = set(
                self.subject_ids.ids
            )  # Get new subject IDs after update

            added_subjects = new_subject_ids - old_subject_ids
            removed_subjects = old_subject_ids - new_subject_ids

            # Update the `is_offered` flag for added subjects (set to True)
            self._update_subject_is_offered(
                self.env["op.subject"].browse(added_subjects)
            )

            # Update the `is_offered` flag for removed subjects (set to False)
            self._update_subject_is_offered(
                self.env["op.subject"].browse(removed_subjects)
            )

        return result  # Return the original boolean result from `write`

    def unlink(self):

        subject_ids_to_unlink = self.subject_ids
        result = super(OfferModule, self).unlink()
        self._update_subject_is_offered(subject_ids_to_unlink)

        return result
