import logging

_logger = logging.getLogger(__name__)


from datetime import date, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StudentLeave(models.Model):
    """For Student Leave we are not inheriting the hr.leave module as the modle doesnot allow non employee to apply for leave"""

    _name = "cst.student.leave"
    _description = "Student Leave"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
    ]

    # ------------------------------
    # Attributes of CST student leave
    # ------------------------------

    name = fields.Char(
        "Description",
        copy=False,
    )

    student_id = fields.Many2one(
        "op.student",
        help="Getting the student id from the user",
        default=lambda self: self.env.user.student_line,
        store="True",
    )

    holiday_status_id = fields.Many2one(
        "cst.student.leave.type",
        store=True,
        string="Time Off Type",
        required=True,
        readonly=False,
        tracking=True,
    )

    course_id = fields.Many2one(
        "op.course", string="Programme", compute="_compute_course_id", store=True
    )

    student_leave_approved_by_pl = fields.Boolean(
        string="Student Leave Approved By PL",
        compute="_compute_approved_by_pl",
        store="True",
    )

    leave_approver_id = fields.Many2one(
        "hr.employee",
        store=True,
        help="Stores the leave approver id",
        compute="_compute_leave_approver_id",
    )

    approver_user_id = fields.Many2one(
        related="leave_approver_id.user_id",
        string="Approver User",
        store=True,
        readonly=True,
    )

    state = fields.Selection(
        [
            ("confirm", "To Approve"),
            ("refuse", "Refused"),
            ("validate", "Approved"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        store=True,
        tracking=True,
        copy=False,
        readonly=False,
        default="confirm",
        help="The status is set to 'To Submit', when a time off request is created."
        + "\nThe status is 'To Approve', when time off request is confirmed by user."
        + "\nThe status is 'Refused', when time off request is refused by Approver."
        + "\nThe status is 'Approved', when time off request is approved by Approcer.",
    )

    notes = fields.Text("Reasons", readonly=False)

    attachment_ids = fields.One2many("ir.attachment", "res_id", string="Attachments")

    supported_attachment_ids = fields.Many2many(
        "ir.attachment",
        string="Attach File",
        compute="_compute_supported_attachment_ids",
        inverse="_inverse_supported_attachment_ids",
    )
    supported_attachment_ids_count = fields.Integer(
        compute="_compute_supported_attachment_ids"
    )

    leave_type_support_document = fields.Boolean(
        related="holiday_status_id.support_document"
    )

    date_from = fields.Date(
        "Start Date",
        store=True,
        index=True,
        tracking=True,
        default=lambda self: date.today(),
    )
    date_to = fields.Date(
        "End Date", store=True, tracking=True, default=lambda self: date.today()
    )

    number_of_days = fields.Integer(
        "Number of days",
        compute="_compute_number_of_days",
        inverse="_inverse_number_of_days",
        store=True,
        tracking=True,
        help="Number of days of the time off request. Used in the calculation.",
    )

    active = fields.Boolean(default=True)

    # CONSTRAINTS
    _sql_constraints = [
        (
            "date_check",
            "CHECK ((date_from <= date_to))",
            "The start date must be before or equal to the end date.",
        ),
        (
            "duration_check",
            "CHECK ( number_of_days >= 0 )",
            "Number of Days should be positive",
        ),
    ]

    # ----------------------
    #
    # Compute Method Call
    #
    # ----------------------

    @api.depends("student_id")
    def _compute_course_id(self):
        for rec in self:
            rec.course_id = rec.student_id.course_id

    # Computing the leave approver id
    @api.depends("holiday_status_id", "course_id", "student_leave_approved_by_pl")
    def _compute_leave_approver_id(self):
        for rec in self:
            if rec.student_leave_approved_by_pl:
                if not rec.course_id:
                    raise ValidationError(
                        "You need to be enrolled in a programme to take a Leave Approved by Programme Leader"
                    )
                rec.leave_approver_id = rec.course_id.programme_leader_id
            else:
                rec.leave_approver_id = rec.holiday_status_id.faculty_validator

    @api.depends("holiday_status_id")
    def _compute_approved_by_pl(self):
        for rec in self:
            if rec.holiday_status_id.student_leave_validation_type == "pl":
                rec.student_leave_approved_by_pl = True
            else:
                rec.student_leave_approved_by_pl = False

    @api.depends("date_from", "date_to")
    def _compute_number_of_days(self):
        for record in self:
            if record.date_from and record.date_to:
                delta = (record.date_to - record.date_from).days
                if delta >= 0:
                    record.number_of_days = delta + 1  # Include the start date
                else:
                    raise ValidationError(
                        "Your leave start date should be earlier than the end date."
                    )
            else:
                record.number_of_days = 0

    def _inverse_number_of_days(self):
        for record in self:
            if record.date_from and record.date_to:
                delta = (record.date_to - record.date_from).days
                if delta >= 0:
                    record.number_of_days = delta + 1  # Include the start date
                else:
                    raise ValidationError(
                        "Your leave start date should be earlier than the end date."
                    )
            else:
                record.number_of_days = 0

    @api.depends("leave_type_support_document", "attachment_ids")
    def _compute_supported_attachment_ids(self):
        for holiday in self:
            holiday.supported_attachment_ids = holiday.attachment_ids
            holiday.supported_attachment_ids_count = len(holiday.attachment_ids.ids)

    def _inverse_supported_attachment_ids(self):
        for holiday in self:
            holiday.attachment_ids = holiday.supported_attachment_ids

    # -------------------------
    #
    # Main Actions
    #
    # --------------------------
    # Send email to notified time off officer
    def send_email_notified(self, leave_request):
        template = self.env.ref(
            "cst_student_leave_module_custom.inform_leave_to_notified_faculty",
            raise_if_not_found=False,
        )

        if not template:
            _logger.warning("Email template not found.")
            return False

        company_email = self.env.company.email or "cst.ims.odoo@gmail.com"
        template.email_from = company_email

        notified_users = leave_request.holiday_status_id.notify_ids.mapped("id")
        _logger.info("Notified Users: %s", notified_users)

        for user in notified_users:
            # Fetch the employee record for the user
            employee = self.env["res.users"].browse(user).employee_id

            # Ensure the employee has a valid email
            if not employee.work_email:
                _logger.warning(f"No work email found for employee {employee.name}")
                continue

            _logger.info(f"Sending email to {employee.work_email}")
            # Send email to the employee's work email
            template.with_context(user=employee).sudo().send_mail(
                leave_request.id,
                force_send=True,
                email_values={"email_to": employee.work_email},
            )

        return True

    # Send Email to approver
    def send_leave_status_email(self, leave_request):
        """
        Sends an email to the student about the status of the leave
        """
        # Get the email template
        template = self.env.ref(
            "cst_student_leave_module_custom.inform_student_leave_status_email"
        )  # Replace with your email template ID

        if not template:
            return False  # If the email template is not found

        company_email = self.env.company.email or "cst.ims.odoo@gmail.com"
        template.email_from = company_email
        # Send the email using the template
        template.sudo().send_mail(leave_request.id, force_send=True)

        return True

    def action_approve(self):
        for rec in self:
            if not (
                rec.leave_approver_id.user_id.id == self.env.user.id
                or self.env.user.has_group(
                    "cst_student_leave_module_custom.student_leave_admin_group"
                )
            ):
                raise ValidationError("You are not authorized to approve this leave.")

            self.state = "validate"

            try:
                self.send_email_notified(rec)
                self.send_leave_status_email(rec)
            except Exception as e:
                _logger.error(f"Failed to send leave request email: {str(e)}")

    def action_refuse(self):
        for rec in self:
            if not (
                rec.leave_approver_id.user_id.id == self.env.user.id
                or self.env.user.has_group(
                    "cst_student_leave_module_custom.student_leave_admin_group"
                )
            ):
                raise ValidationError("You are not authorized to refuse this leave.")
            self.state = "refuse"

            self.send_leave_status_email(rec)

    def action_cancel(self):
        if self.state == "validate":
            raise ValidationError(
                "You cannot cancel an approved leave. Contact the administrator or the leave approver to reset/cancel the leave"
            )
        else:
            self.state = "cancel"

    def action_reset_confirm(self):
        for rec in self:
            if not (
                rec.leave_approver_id.user_id.id == self.env.user.id
                or self.env.user.has_group(
                    "cst_student_leave_module_custom.student_leave_admin_group"
                )
            ):
                raise ValidationError("You are not authorized to reset this leave.")
            self.state = "confirm"

    @api.model
    def get_leave_approval_link(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        action = self.env.ref(
            "cst_student_leave_module_custom.action_open_student_leave",
            raise_if_not_found=False,
        )
        if action:
            action_id = action.id
        else:
            # Handle the case where the action isn't found
            action_id = None
            # Optionally log or print a message for debugging
            _logger.warning(
                "Action ID not found: cst_student_leave_module_custom.action_open_student_leave"
            )
        action_id = self.env.ref(
            "cst_student_leave_module_custom.action_open_student_leave"
        ).id
        form_url = f"{base_url}/web#id={self.id}&model=cst.student.leave&view_type=form&action={action_id}"
        return form_url

    # Send Email to approver
    def send_leave_request_email(self, leave_request):
        """
        Sends an email to the approver when a leave request is created.
        """
        # Get the email template
        template = self.env.ref(
            "cst_student_leave_module_custom.inform_leave_email"
        )  # Replace with your email template ID

        if not template:
            return False  # If the email template is not found

        company_email = self.env.company.email or "cst.ims.odoo@gmail.com"
        template.email_from = company_email
        # Send the email using the template
        template.sudo().send_mail(leave_request.id, force_send=True)

        return True

    # ----------------------------
    #
    # ORM Method
    #
    # -----------------------------
    @api.model_create_multi
    def create(self, vals_list):  # Accept a list of dictionaries
        for vals in vals_list:  # Iterate over each dictionary in the list
            student_id = vals.get("student_id")
            date_from = vals.get("date_from")
            date_to = vals.get("date_to")

            if date_from and date_to:
                overlapping_leaves = self.search(
                    [
                        ("student_id", "=", student_id),
                        ("state", "in", ["confirm", "refuse", "validate"]),
                        ("date_from", "<=", date_to),
                        ("date_to", ">=", date_from),
                    ]
                )

                if overlapping_leaves:
                    raise ValidationError(
                        "You have overlapping leaves for the requested dates. Attempting to double-book your time off won't magically make your vacation 2x better!"
                    )

        # Now call the super method correctly
        leave_requests = super(StudentLeave, self).create(vals_list)

        # Send email notifications for each created leave request
        for leave_request in leave_requests:
            try:
                self.send_leave_request_email(leave_request)
            except Exception as e:
                _logger.error(f"Failed to send leave request email: {str(e)}")

        return leave_requests

    def write(self, vals):
        # Fetch the student's leave dates from the current record
        for leave in self:
            student_id = leave.student_id.id
            old_date_from = leave.date_from
            old_date_to = leave.date_to

            # Check if the user is modifying the dates (date_from or date_to)
            if "date_from" in vals or "date_to" in vals:
                # If date_from is modified, use the new value, else keep the old one
                new_date_from = vals.get("date_from", old_date_from)
                new_date_to = vals.get("date_to", old_date_to)

                # Search for overlapping leaves for the same student
                overlapping_leaves = self.search(
                    [
                        ("student_id", "=", student_id),
                        (
                            "state",
                            "in",
                            ["confirm", "refuse", "validate"],
                        ),  # Only consider non-cancelled requests
                        ("id", "!=", leave.id),  # Exclude the current leave record
                        (
                            "date_from",
                            "<=",
                            new_date_to,
                        ),  # Existing leave starts before the new one ends
                        (
                            "date_to",
                            ">=",
                            new_date_from,
                        ),  # Existing leave ends after the new one starts
                    ]
                )

                # If there are any overlapping leaves, raise a validation error
                if overlapping_leaves:
                    raise ValidationError(
                        "The student has already requested leave for the selected dates. Please choose different dates."
                    )

        # Proceed with the actual record update if no validation errors
        return super(StudentLeave, self).write(vals)
