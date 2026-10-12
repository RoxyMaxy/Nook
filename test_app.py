import unittest
import json
import io
import base64
from app import app
from parser_helper import parse_gemma_json, limit_words

class TestNookApplication(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()

    def test_health_check(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get('status'), 'healthy')
        self.assertEqual(data.get('app'), 'Nook Fieldwork')

    def test_config_endpoint(self):
        response = self.client.get('/api/config')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('model_id', data)
        self.assertIn('ai_ready', data)

    def test_index_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Nook', html)
        self.assertIn('Observe', html)
        self.assertIn('Investigate', html)
        self.assertIn('Create', html)

    def test_parser_helper_sanitization(self):
        raw_llm_output = """
        ```json
        {
          "seen": ["Deep green serrated edge", "Velvety surface hairs with light sheen"],
          "possible_identification": "Possible juvenile stinging nettle Urtica dioica specimen.",
          "alternatives": ["Deadnettle Lamium album mimicking toxic defense traits."],
          "hypotheses": ["Germinated under nitrogen-rich damp compost topsoil."],
          "uncertain": "Root rhizome network obscured underground.",
          "investigation_question": "Do the lower leaves show square stems?",
          "observation_mission": "Observe if insects perch on the hairs without touching.",
          "atelier": "Sketch the leaf margin contours with dry stick in soil."
        }
        ```
        """
        card = parse_gemma_json(raw_llm_output)
        self.assertIsInstance(card["seen"], list)
        self.assertEqual(len(card["seen"]), 2)
        self.assertEqual(len(card["alternatives"]), 1)
        self.assertEqual(len(card["hypotheses"]), 1)
        self.assertTrue(len(card["possible_identification"].split()) <= 25)

    def test_analyze_endpoint_json_fallback(self):
        # 1x1 transparent GIF base64
        tiny_gif = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
        payload = {"image": f"data:image/gif;base64,{tiny_gif}"}
        response = self.client.post(
            '/api/analyze',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('field_card', data)
        self.assertIn('possible_identification', data['field_card'])

    def test_narrate_endpoint(self):
        payload = {"text": "Specimen identified as wild clover."}
        response = self.client.post(
            '/narrate',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.mimetype in ['audio/mpeg', 'audio/wav'])
        self.assertGreater(len(response.data), 100)

if __name__ == '__main__':
    unittest.main()
