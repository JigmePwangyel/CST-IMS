import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Get the logger for this module
_logger = logging.getLogger(__name__)


class Student(models.Model):
    _inherit = "op.student"

    student_number = fields.Char(string="Student Number", required=True)
    current_address_dzongkhag = fields.Char(string="Dzongkhag (Current Address)")
    current_address_gewog = fields.Char(string="Gewog (Current Address)")
    private_mobile_number = fields.Char(string="Mobile Number")
    private_email = fields.Char(string="Private Email")

    house_number = fields.Char(string="House Number")
    thram_number = fields.Char(string="Thram Number")
    village = fields.Char(string="Village")
    gewog = fields.Char(string="Gewog")
    dzongkhag = fields.Char(string="Dzongkhag")

    guardian = fields.Char(string="Guardian Name")
    guardian_contact = fields.Char(string="Contact Number")
    guardian_organization = fields.Char(string="Organization")
    relation_with_guardian = fields.Selection(
        [("parent", "Parent"), ("guardian", "Guardian")], string="Relation"
    )

    name_of_last_school = fields.Char(string="Last School Attended")
    index_no = fields.Char(string="Index Number")
    class_xii_percentage = fields.Char(string="Class 12 Percentage")

    # Might Change When we create Admission Module
    admission_date = fields.Date(
        string="Admission Date", help="Date when the student was admitted."
    )

    hostel_type = fields.Selection(
        [
            ("hostel", "Hostel"),
            ("self_catering", "Self-Catering"),
            ("days_scholar", "Days Scholar"),
        ],
        string="Hostel Type",
    )
    # course_id = fields.Many2one("op.course", string="Programme", store=True)
    scholarship_id = fields.Many2one(
        "cst.scholarship", string="Scholarship", store=True
    )
    scholarship_category = fields.Selection(
        string="Scholarship Category", related="scholarship_id.category", store=True
    )

    college_email = fields.Char(
        string="College Email", compute="_compute_college_email", default=""
    )
    batch_id = fields.Many2one("op.batch", "Batch", tracking=True, store=True)
    course_id = fields.Many2one(
        "op.course",
        string="Programme",
        related="batch_id.course_id",
        store=True,
        readonly=True,
    )

    partner_id = fields.Many2one(
        "res.partner", "Partner", required=False, ondelete="cascade"
    )

    @api.depends("student_number")
    def _compute_college_email(self):
        for rec in self:
            rec.college_email = f"{rec.student_number}.cst@rub.edu.bt"

    _sql_constraints = [
        (
            "unique_student_number",
            "UNIQUE(student_number)",
            "Student number must be unique!",
        )
    ]
    #
    # NOTE The FOLLOWING CODE DOES NOT WORK AND WE NEED TO UPDATE IT, ALSO ADD A WRITE METHOD AS WELL
    # Create a res.partner_id when student is created
    # @api.model_create_multi
    # def create(self, vals):
    #     # Create a res.partner if partner_id is not provided
    #     # Log the partner_id from vals
    #     # _logger.info("Partner ID Create Method: %s", vals.get("partner_id.id"))
    #     if not vals.get("partner_id"):
    #         full_name = " ".join(
    #             filter(
    #                 None,
    #                 [
    #                     vals.get("first_name", ""),
    #                     vals.get("middle_name", ""),
    #                     vals.get("last_name", ""),
    #                 ],
    #             )
    #         )

    #         partner_vals = {
    #             "name": full_name,
    #             "email": vals.get("college_email", ""),
    #             "phone": vals.get("private_mobile_number", ""),
    #             "is_company": False,
    #         }
    #         print("Create Method: ", partner_vals)

    #         partner = self.env["res.partner"].create(partner_vals)
    #         vals["partner_id"] = partner.id

    #     return super(Student, self).create(vals)

    @api.model_create_multi
    def create(self, vals):
        # Ensure vals is a list of dictionaries (as expected by model_create_multi)
        if isinstance(vals, list):
            # Iterate through each dictionary in the list
            for val in vals:
                # Create a res.partner if partner_id is not provided
                if not val.get("partner_id"):
                    full_name = " ".join(
                        filter(
                            None,
                            [
                                val.get("first_name", ""),
                                val.get("middle_name", ""),
                                val.get("last_name", ""),
                            ],
                        )
                    )

                    partner_vals = {
                        "name": full_name,
                        "email": val.get("college_email", ""),
                        "phone": val.get("private_mobile_number", ""),
                        "is_company": False,
                    }
                    _logger.info("Create Method: %s", partner_vals)

                    # Create partner record
                    partner = self.env["res.partner"].create(partner_vals)
                    val["partner_id"] = partner.id

            # Ensure vals is still a list after modification
            return super().create(vals)

        else:
            # If vals is a dictionary, process it directly
            if not vals.get("partner_id"):
                full_name = " ".join(
                    filter(
                        None,
                        [
                            vals.get("first_name", ""),
                            vals.get("middle_name", ""),
                            vals.get("last_name", ""),
                        ],
                    )
                )

                partner_vals = {
                    "name": full_name,
                    "email": vals.get("college_email", ""),
                    "phone": vals.get("private_mobile_number", ""),
                    "is_company": False,
                }
                _logger.info("Create Method: %s", partner_vals)

                # Create partner record
                partner = self.env["res.partner"].create(partner_vals)
                vals["partner_id"] = partner.id

            # Proceed with the creation of the main record
            return super().create([vals])  # Ensure vals is wrapped in a list

    # Overiding the Method get_activity from the Openeducat_activity module
    def get_activity(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Activity Logs",
            "view_mode": "list",
            "res_model": "op.activity",
            "domain": [("student_id", "=", self.ids)],
            "context": "{'create': True}",
        }

    leadership_log = fields.One2many(
        "cst.leadership", "student_id", string="Leadership Log"
    )
    leadership_count = fields.Integer(compute="compute_leadership_count")

    # Methods for Getting Student Leadership Information
    def compute_leadership_count(self):
        for rec in self:
            rec.leadership_count = self.env["cst.leadership"].search_count(
                [("student_id", "in", self.ids)]
            )

    def get_leadership(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Leadership Log",
            "view_mode": "list",
            "res_model": "cst.leadership",
            "domain": [("student_id", "=", self.ids)],
            "context": "{'create': True}",
        }

    discipline_log = fields.One2many(
        "cst.student.discipline", "student_id", string="Discipline Log"
    )
    discipline_count = fields.Integer(compute="compute_discipline_count")

    def compute_discipline_count(self):
        for rec in self:
            rec.discipline_count = self.env["cst.student.discipline"].search_count(
                [("student_id", "in", self.ids)]
            )

    def get_discipline_record(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Student Disciplinary Records",
            "view_mode": "list",
            "res_model": "cst.student.discipline",
            "domain": [("student_id", "=", self.ids)],
            "context": "{'create': True}",
        }

    # Achievement Log Personal
    achievement_log = fields.One2many(
        "cst.student.achievement", "student_id", string="Achievement Log"
    )
    achievement_count = fields.Integer(compute="compute_achievement_count")

    def compute_achievement_count(self):
        for rec in self:
            rec.achievement_count = self.env["cst.student.achievement"].search_count(
                [("student_id", "in", self.ids)]
            )

    def get_achievement_record(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Achievement Log",
            "view_mode": "list",
            "res_model": "cst.student.achievement",
            "domain": [("student_id", "=", self.ids)],
            "context": "{'create': True}",
        }

    #
    # ***Need to add new Functionality to uddate student years.
    # Introduced two new var, year and status where status -> active or graduated and year -> 1,2,3,4,5 depending on course
    # Automate this by writing script which runs when a new academic year is created.
    # Use scheduled action
    #

    year = fields.Integer("Year", related="batch_id.year", store=True)

    # This codes creates a student user by overidding the method

    def create_student_user(self):
        user_group = self.env.ref(
            # "cst_student_profile_module_custom.group_student_user"
            "base.group_portal"
        )
        users_res = self.env["res.users"]

        for record in self:
            if not record.user_id:
                # Check if user already exists with the same email
                existing_user = users_res.search(
                    [("login", "=", record.college_email)], limit=1
                )
                if existing_user:
                    record.user_id = existing_user
                    continue  # Skip user creation if already exists

                # Create the user as an internal user with a default password
                user_id = users_res.create(
                    {
                        "name": record.name,
                        "login": record.college_email,  # Email format with student number
                        "partner_id": record.partner_id.id,
                        "student_line": record.id,
                        "groups_id": [
                            (4, user_group.id)
                        ],  # Assign the custom student group
                        "password": "12345",  # Default password
                        "tz": self._context.get("tz"),
                        "share": False,  # Internal user (not a portal user)
                    }
                )
                # Link the created user to the student's record
                record.user_id = user_id


class Batch(models.Model):
    _inherit = "op.batch"

    year = fields.Integer(string="Year", default=1)
