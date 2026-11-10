import unittest
from unittest.mock import patch, MagicMock
from uuid import UUID
from argon2 import PasswordHasher
from registration import validate_registration, register_user, RegistrationGuard

class RegistrationTests(unittest.TestCase):
    def test_validation_and_normalization(self):
        self.assertEqual(validate_registration('  Alice_1 ', 'a-long-password'), 'alice_1')
        for name, password in [('ab', 'a-long-password'), ('bad name','a-long-password'), ('alice','short'), ('alice',' '*12), ('alice','x'*129)]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_registration(name,password)

    def test_hash_and_identity_binding(self):
        context=MagicMock();conn=context.__enter__.return_value
        with patch('registration.user_transaction',return_value=context) as transaction:
            user_id=register_user(object(),'Alice_1','a-long-password')
        self.assertIsInstance(user_id,UUID)
        self.assertEqual(transaction.call_args.args[1],user_id)
        args=conn.execute.call_args.args[1]
        self.assertEqual(args[:2],(user_id,'alice_1'))
        self.assertNotEqual(args[2],'a-long-password')
        self.assertTrue(PasswordHasher().verify(args[2],'a-long-password'))

class GuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_per_address_limit_and_expiry(self):
        guard=RegistrationGuard()
        for _ in range(5):self.assertTrue(guard.allow('192.0.2.1',now=0))
        self.assertFalse(guard.allow('192.0.2.1',now=1))
        self.assertTrue(guard.allow('192.0.2.2',now=1))
        self.assertTrue(guard.allow('192.0.2.1',now=901))

    async def test_global_limit(self):
        guard=RegistrationGuard()
        for i in range(30):self.assertTrue(guard.allow(str(i),now=0))
        self.assertFalse(guard.allow('new',now=1))

class EndpointTests(unittest.TestCase):
    def make_client(self):
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.testclient import TestClient
        from registration import register_endpoint
        app=Starlette(routes=[Route('/api/auth/register',register_endpoint,methods=['POST'],max_body_size=4096)])
        app.state.web_origin='https://example.test';app.state.settings=object();app.state.registration_guard=RegistrationGuard()
        return TestClient(app)

    @patch('registration.env_bool',return_value=True)
    @patch('registration.register_user',return_value=UUID('11111111-1111-4111-8111-111111111111'))
    def test_origin_validation_duplicate_and_limit(self,create,enabled):
        from psycopg.errors import UniqueViolation
        body={'login_name':'Alice_1','password':'a-long-password'}
        with self.make_client() as client:
            self.assertEqual(client.post('/api/auth/register',json=body).status_code,403)
            self.assertEqual(client.post('/api/auth/register',headers={'origin':'https://evil.test'},json=body).status_code,403)
            headers={'origin':'https://example.test'}
            self.assertEqual(client.post('/api/auth/register',headers=headers,json=[]).status_code,400)
            self.assertEqual(client.post('/api/auth/register',headers=headers,json={'login_name':'alice','password':'x'}).status_code,400)
            response=client.post('/api/auth/register',headers=headers,json=body)
            self.assertEqual(response.status_code,201)
            self.assertNotIn('set-cookie',response.headers)
            create.side_effect=UniqueViolation('duplicate')
            self.assertEqual(client.post('/api/auth/register',headers=headers,json=body).status_code,409)
            create.side_effect=None
            for _ in range(3):self.assertEqual(client.post('/api/auth/register',headers=headers,json=body).status_code,201)
            self.assertEqual(client.post('/api/auth/register',headers=headers,json=body).status_code,429)
            self.assertEqual(create.call_count,5)

    @patch('registration.env_bool',return_value=False)
    def test_closed_registration(self,enabled):
        with self.make_client() as client:
            self.assertEqual(client.post('/api/auth/register',headers={'origin':'https://example.test'},json={}).status_code,403)

    @patch('registration.env_bool',return_value=True)
    def test_body_limit(self,enabled):
        with self.make_client() as client:
            self.assertEqual(client.post('/api/auth/register',headers={'origin':'https://example.test'},json={'password':'x'*5000}).status_code,413)

if __name__=='__main__':unittest.main()
