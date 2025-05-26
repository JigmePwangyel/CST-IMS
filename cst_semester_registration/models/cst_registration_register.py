from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class RegistrationRegister(models.Model):
    _name = "cst.registration.register"
    _description = "Registration Register"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Register Name", required=True, tracking=True)
    start_date = fields.Date(
        string="Start Date", required=True, tracking=True, default=fields.Date.today()
    )
    end_date = fields.Date(
        string="End Date",
        required=True,
        tracking=True,
        default=lambda self: fields.Date.today() + relativedelta(days=30),
    )
    term_id = fields.Many2one(
        "op.academic.term",
        domain=[("is_active", "=", True)],
        string="Academic Term",
        required=True,
        tracking=True,
    )
    batch_id = fields.Many2one("op.batch", string="Batch", tracking=True)
    course_id = fields.Many2one(
        "op.course", string="Course", related="batch_id.course_id", store=True
    )
    registration_ids = fields.One2many(
        "cst.registration", "register_id", string="Student Registrations"
    )
    state = fields.Selection(
        [("draft", "Draft"), ("ongoing", "Ongoing"), ("closed", "Closed")],
        string="Status",
        default="draft",
        tracking=True,
        compute="_auto_update_state",
        store=True,
    )
    active = fields.Boolean(default=True)
    registration_count = fields.Integer(
        string="Registration Count", compute="_compute_registration_count"
    )
    is_published = fields.Boolean(string="Published", default=False, tracking=True)
    duration_days = fields.Integer(
        string="Duration (Days)", compute="_compute_duration"
    )

    # Action Methods
    def confirm_register(self):
        for rec in self:
            if rec.state == "draft":
                rec.is_published = True
                rec.state = "ongoing"
            else:
                raise ValidationError(
                    _("Only registers in 'Draft' state can be turned into ongoing")
                )

    def close_register(self):
        for rec in self:
            if rec.state == "ongoing":
                rec.is_published = False
                rec.state = "closed"
            else:
                raise ValidationError(
                    _("Register can only be closed if state is in ongoing")
                )

    def set_to_draft(self):
        self.write({"state": "draft"})

    def toggle_publish(self):
        for record in self:
            if record.state != "ongoing":
                raise ValidationError(
                    _("Only registers in 'Ongoing' state can be published")
                )
            record.is_published = not record.is_published

    # Computed Methods
    @api.depends("start_date", "end_date")
    def _compute_duration(self):
        for record in self:
            if record.start_date and record.end_date:
                delta = record.end_date - record.start_date
                record.duration_days = delta.days
            else:
                record.duration_days = 0

    @api.depends("end_date")
    def _auto_update_state(self):
        today = fields.Date.today()
        for record in self:
            if record.end_date and record.end_date < today:
                record.state = "closed"

    @api.depends("registration_ids")
    def _compute_registration_count(self):
        for record in self:
            record.registration_count = len(record.registration_ids)

    # Constraint Methods
    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError(_("End Date cannot be set before Start Date."))

    @api.constrains("is_published", "batch_id")
    def _check_unique_published_per_batch(self):
        for record in self:
            if record.is_published and record.batch_id:
                existing = self.search(
                    [
                        ("is_published", "=", True),
                        ("batch_id", "=", record.batch_id.id),
                        ("id", "!=", record.id),
                    ],
                    limit=1,
                )
                if existing:
                    raise ValidationError(
                        _("Only one published register allowed per batch")
                    )

    # View Actions
    def open_registrations(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Registrations"),
            "res_model": "cst.registration",
            "domain": [("register_id", "=", self.id)],
            "view_mode": "list,form",
            "context": {"default_register_id": self.id},
        }
