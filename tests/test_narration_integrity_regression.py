import unittest
from scripts.narration_body import story_body

class CompleteReadingTests(unittest.TestCase):
    def test_does_not_drop_fact_from_sentence_containing_brand(self):
        text = "La redacción ORBIUNO confirmó el cierre de la vía.\n\nEl tránsito se restableció a las cinco."
        got = story_body(text)
        self.assertIn("confirmó el cierre de la vía", got)
        self.assertIn("El tránsito se restableció a las cinco", got)
        self.assertNotIn("ORBIUNO", got)
        self.assertEqual(len(got.split("\n\n")), 2)

    def test_excludes_promotion_not_journalism(self):
        got = story_body("El Ministerio publicó su informe. Síguenos en ORBIUNO para más.\n\nLa fecha es el martes.")
        self.assertIn("El Ministerio publicó su informe.", got)
        self.assertNotIn("Síguenos", got)
        self.assertIn("La fecha es el martes.", got)
