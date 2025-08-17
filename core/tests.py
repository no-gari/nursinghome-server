import json
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch

from .models import ChatMessage


class AuthChatTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="pass12345")

    def test_login_logout(self):
        login_url = reverse("core:login")
        response = self.client.post(login_url, {"username": "tester", "password": "pass12345"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

        logout_url = reverse("core:logout")
        response = self.client.post(logout_url)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    @patch("core.views.RAGService")
    def test_chat_history_saved_only_for_authenticated_users(self, mock_rag):
        mock_rag.return_value.chat.return_value = {"answer": "hi", "sources": []}
        chat_url = reverse("core:chatbot_api")

        # Authenticated
        self.client.login(username="tester", password="pass12345")
        response = self.client.post(chat_url, data=json.dumps({"query": "hello"}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ChatMessage.objects.filter(user=self.user).count(), 2)

        # Anonymous
        self.client.logout()
        response = self.client.post(chat_url, data=json.dumps({"query": "hi"}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ChatMessage.objects.filter(user=self.user).count(), 2)
