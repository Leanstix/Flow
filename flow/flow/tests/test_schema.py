from django.test import TestCase


HTTP_METHODS = {'get', 'post', 'put', 'patch', 'delete'}


class RichSchemaTests(TestCase):
    def setUp(self):
        response = self.client.get('/swagger.json')
        self.assertEqual(response.status_code, 200, response.content.decode('utf-8', errors='ignore'))
        self.schema = response.json()

    def operation(self, path, method):
        self.assertIn(path, self.schema['paths'])
        self.assertIn(method, self.schema['paths'][path])
        return self.schema['paths'][path][method]

    def test_every_documented_http_operation_is_rich(self):
        operations = []
        for path, path_item in self.schema.get('paths', {}).items():
            for method, operation in path_item.items():
                if method not in HTTP_METHODS:
                    continue
                operations.append((path, method, operation))

        self.assertGreater(len(operations), 40)
        for path, method, operation in operations:
            with self.subTest(path=path, method=method):
                self.assertTrue(operation.get('summary'))
                self.assertGreater(len(operation.get('description', '')), 80)
                self.assertTrue(operation.get('tags'))
                self.assertTrue(operation.get('responses'))

    def test_bearer_authentication_and_public_endpoint_overrides(self):
        schemes = self.schema.get('securityDefinitions', {})
        self.assertIn('Bearer', schemes)
        self.assertEqual(schemes['Bearer']['name'], 'Authorization')
        self.assertEqual(schemes['Bearer']['in'], 'header')

        login = self.operation('/api/login/', 'post')
        self.assertEqual(login.get('security'), [])

        posts = self.operation('/api/posts/', 'get')
        self.assertEqual(posts.get('security'), [{'Bearer': []}])
        self.assertIn('401', posts['responses'])

    def test_key_features_have_specific_operation_documentation(self):
        create_post = self.operation('/api/posts/', 'post')
        self.assertEqual(create_post['summary'], 'Create a text, image or video post')
        self.assertIn('edit and export the final video locally before upload', create_post['description'])

        reply = self.operation('/api/posts/comments/{comment_id}/reply/', 'post')
        self.assertEqual(reply['summary'], 'Reply to any comment or reply')
        self.assertIn('any thread depth', reply['description'])

        seller = self.operation('/api/marketplace/listings/{id}/contact_seller/', 'post')
        self.assertEqual(seller['summary'], 'Start a listing-aware seller conversation')
        self.assertIn('exact item', seller['description'])

        send_message = self.operation('/api/conversations/{id}/send_message/', 'post')
        self.assertEqual(send_message['summary'], 'Send a message or typed attachment')
        self.assertIn('attachment_type', send_message['description'])

    def test_legacy_marketplace_alias_is_marked_deprecated(self):
        legacy_list = self.operation('/api/adds/listings/', 'get')
        self.assertTrue(legacy_list.get('deprecated'))

        canonical_list = self.operation('/api/marketplace/listings/', 'get')
        self.assertFalse(canonical_list.get('deprecated', False))

    def test_top_level_description_contains_websocket_contract(self):
        description = self.schema['info']['description']
        self.assertIn('/ws/conversations/{conversation_id}/', description)
        self.assertIn('/ws/notifications/', description)
        self.assertIn('/ws/call/{room_name}/', description)
        self.assertIn('/ws/calls/', description)
