from django.test import TestCase
from django.urls import reverse


class FAQsViewTest(TestCase):

    def test_faqs_page_returns_200(self):
        response = self.client.get(reverse('faqs_page:faqs'))
        self.assertEqual(response.status_code, 200)

    def test_faqs_uses_correct_template(self):
        response = self.client.get(reverse('faqs_page:faqs'))
        self.assertTemplateUsed(response, 'faqs/faqs.html')
