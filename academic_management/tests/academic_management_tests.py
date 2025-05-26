from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestEducationModule(TransactionCase):

    def setUp(self):
        super().setUp()
        self.programme_model = self.env["op.programme"]
        self.module_model = self.env["op.module"]
        self.assessment_model = self.env["op.assessment"]
        self.offer_module_model = self.env["offer.module"]
        self.academic_year_model = self.env["op.academic.year"]
        self.term_model = self.env["op.academic.term"]
        self.user_model = self.env["res.users"]

    def test_01_create_programme(self):
        programme = self.programme_model.create({"name": "BSc CS", "code": "BSCS"})
        self.assertEqual(programme.name, "BSc CS")
        self.assertEqual(programme.code, "BSCS")

    def test_02_duplicate_programme_code_not_allowed(self):
        self.programme_model.create({"name": "BSc CS", "code": "BSCS"})
        with self.assertRaises(ValidationError):
            self.programme_model.create({"name": "BSc IT", "code": "BSCS"})

    def test_03_create_module(self):
        module = self.module_model.create({"name": "Data Structures", "code": "DS101"})
        self.assertEqual(module.name, "Data Structures")

    def test_04_compute_assessment_weightage(self):
        module = self.module_model.create({"name": "Algorithms", "code": "ALGO101"})
        assignment = self.assessment_model.create(
            {
                "name": "Assignment",
                "type": "assignment",
                "weightage": 40,
                "module_id": module.id,
            }
        )
        exam = self.assessment_model.create(
            {
                "name": "Exam",
                "type": "exam",
                "weightage": 60,
                "module_id": module.id,
            }
        )
        total_weightage = sum(module.assessment_ids.mapped("weightage"))
        self.assertEqual(total_weightage, 100)

    def test_05_total_assessment_weightage_should_be_100(self):
        module = self.module_model.create({"name": "Networks", "code": "NET101"})
        self.assessment_model.create(
            {
                "name": "Test1",
                "type": "test",
                "weightage": 50,
                "module_id": module.id,
            }
        )
        with self.assertRaises(ValidationError):
            self.assessment_model.create(
                {
                    "name": "Test2",
                    "type": "test",
                    "weightage": 60,
                    "module_id": module.id,
                }
            )

    def test_06_tutor_allocation_to_module(self):
        tutor = self.user_model.create(
            {
                "name": "Dr. Smith",
                "login": "drsmith@example.com",
                "email": "drsmith@example.com",
            }
        )
        module = self.module_model.create(
            {"name": "AI", "code": "AI101", "tutor_id": tutor.id}
        )
        self.assertEqual(module.tutor_id.id, tutor.id)

    def test_07_offer_module_to_repeat_student(self):
        offer = self.offer_module_model.create(
            {
                "module_id": self.module_model.create(
                    {"name": "ML", "code": "ML101"}
                ).id,
                "student_type": "repeat",
            }
        )
        self.assertEqual(offer.student_type, "repeat")

    def test_08_offer_module_to_regular_student_by_batch(self):
        offer = self.offer_module_model.create(
            {
                "module_id": self.module_model.create(
                    {"name": "DBMS", "code": "DB101"}
                ).id,
                "student_type": "regular",
                "batch_id": self.env["op.batch"].create({"name": "Batch 2025"}).id,
            }
        )
        self.assertEqual(offer.student_type, "regular")

    def test_09_programme_leader_view_restriction(self):
        leader = self.user_model.create(
            {
                "name": "Prof. Alice",
                "login": "alice@example.com",
                "email": "alice@example.com",
            }
        )
        programme = self.programme_model.create(
            {"name": "Physics", "code": "PHY101", "leader_id": leader.id}
        )
        programmes = self.programme_model.sudo(leader).search([])
        self.assertIn(programme, programmes)

    def test_10_create_academic_year(self):
        year = self.academic_year_model.create({"name": "2025-2026", "code": "AY25"})
        self.assertEqual(year.name, "2025-2026")

    def test_11_create_academic_term(self):
        year = self.academic_year_model.create({"name": "2025-2026", "code": "AY25"})
        term = self.term_model.create(
            {"name": "Term 1", "academic_year_id": year.id, "active": True}
        )
        self.assertTrue(term.active)

    def test_12_only_one_active_academic_term(self):
        year = self.academic_year_model.create({"name": "2025-2026", "code": "AY25"})
        self.term_model.create(
            {"name": "Term 1", "academic_year_id": year.id, "active": True}
        )
        with self.assertRaises(ValidationError):
            self.term_model.create(
                {"name": "Term 2", "academic_year_id": year.id, "active": True}
            )
