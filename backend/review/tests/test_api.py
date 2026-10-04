import base64
import hashlib
import json
import uuid
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from review.models import TraceRun, AnalysisRevision, AuditEvent
from review import services

SOURCE = b'\xef\xbb\xbftime_min,signal_au\r\n0,0\r\n1,2\r\n2,0\r\n'
PASSWORD = 'Test-only-analysis-791!'


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('analyst', password=PASSWORD)
        self.client = APIClient()
        self.client.force_login(self.user)

    def upload(self, request_id=None, source=SOURCE):
        return self.client.post('/api/traces/', {'file': SimpleUploadedFile('triangle.csv', source), 'request_id': str(request_id or uuid.uuid4())}, format='multipart')

    def run_id(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201, response.data)
        return response.data['run_id']

    def save(self, run, version=1, **extra):
        return self.client.post(f'/api/traces/{run}/revisions/', {'start_time': .5, 'end_time': 1.5, 'reason': 'Initial peak selection.', 'expected_version': version, 'request_id': str(uuid.uuid4()), **extra}, format='json')

    def complete(self, run, revision, version=2, **extra):
        return self.client.post(f'/api/traces/{run}/complete-review/', {'revision_id': revision, 'expected_version': version, 'request_id': str(uuid.uuid4()), 'review_note': 'Interval checked.', **extra}, format='json')

    def test_import_detail_and_source_bytes(self):
        run = self.run_id()
        detail = self.client.get(f'/api/traces/{run}/').data
        self.assertEqual(detail['run_version'], 1)
        self.assertEqual(detail['revisions'], [])
        self.assertEqual(detail['points'], [[0, 0], [1, 2], [2, 0]])
        self.assertNotIn('source_bytes', detail)
        source = self.client.get(f'/api/traces/{run}/source/')
        self.assertEqual(b''.join(source.streaming_content), SOURCE)
        self.assertEqual(detail['source_sha256'], hashlib.sha256(SOURCE).hexdigest())
        self.assertEqual(source['Cache-Control'], 'private, no-store')

    def test_preview_does_not_persist(self):
        run = self.run_id()
        result = self.client.post(f'/api/traces/{run}/preview/', {'start_time': .5, 'end_time': 1.5}, format='json')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data['area_fraction_percent'], 75)
        self.assertEqual(AuditEvent.objects.count(), 1)
        self.assertEqual(AnalysisRevision.objects.count(), 0)
        self.assertEqual(TraceRun.objects.get().run_version, 1)

    def test_two_revisions_and_completion(self):
        run = self.run_id()
        first = self.save(run)
        self.assertEqual(first.status_code, 201, first.data)
        second = self.save(run, 2, start_time=0, end_time=2, reason='Include whole signal.')
        self.assertEqual(second.data['revision']['revision_number'], 2)
        self.assertEqual(second.data['revision']['area_fraction_percent'], 100)
        completed = self.complete(run, second.data['revision']['id'], 3)
        self.assertEqual(completed.status_code, 200, completed.data)
        detail = self.client.get(f'/api/traces/{run}/').data
        self.assertEqual(detail['status'], 'reviewed')
        self.assertEqual(detail['run_version'], 4)
        self.assertEqual(detail['revisions'][1]['area_fraction_percent'], 75)
        self.assertEqual(detail['review']['revision_id'], second.data['revision']['id'])
        self.assertEqual([e['version_after'] for e in detail['audit_events']], [1, 2, 3, 4])

    def test_reason_and_unknown_fields(self):
        run = self.run_id()
        for changes in [{'reason': '  '}, {'reason': 'x'*1001}, {'area_fraction_percent': 100}, {'created_by': 99}, {'status': 'reviewed'}, {'start_time': True}, {'start_time': '0.5'}]:
            with self.subTest(changes=changes):
                self.assertEqual(self.save(run, **changes).status_code, 400)
        self.assertEqual(AnalysisRevision.objects.count(), 0)

    def test_direct_writes_lock_and_old_completion(self):
        run = self.run_id()
        self.assertEqual(self.complete(run, str(uuid.uuid4()), 1).status_code, 409)
        first = self.save(run).data['revision']
        second = self.save(run, 2, reason='Rechecked boundaries.').data['revision']
        self.assertEqual(self.complete(run, first['id'], 3).status_code, 409)
        self.assertEqual(self.complete(run, second['id'], 3).status_code, 200)
        self.assertEqual(self.save(run, 4).data['error']['code'], 'review_locked')
        self.assertEqual(self.client.post(f'/api/traces/{run}/preview/', {'start_time': 0, 'end_time': 2}, format='json').status_code, 409)
        self.assertEqual(self.complete(run, second['id'], 4).status_code, 409)

    def test_stale_version_rejected(self):
        run = self.run_id()
        self.save(run)
        result = self.save(run)
        self.assertEqual(result.status_code, 409)
        self.assertEqual(result.data['error']['current_version'], 2)
        self.assertEqual(AnalysisRevision.objects.count(), 1)

    def test_idempotency_for_all_operations(self):
        import_id = uuid.uuid4()
        original = self.upload(import_id)
        repeated = self.upload(import_id)
        self.assertTrue(repeated.data['replayed'])
        self.assertEqual(original.data['run_id'], repeated.data['run_id'])
        run = original.data['run_id']
        revision_request = str(uuid.uuid4())
        revision = self.save(run, request_id=revision_request)
        retried = self.save(run, request_id=revision_request)
        self.assertEqual(revision.data['revision'], retried.data['revision'])
        self.assertTrue(retried.data['replayed'])
        completion_request = str(uuid.uuid4())
        completed = self.complete(run, revision.data['revision']['id'], request_id=completion_request)
        retried = self.complete(run, revision.data['revision']['id'], request_id=completion_request)
        self.assertEqual(completed.data['review'], retried.data['review'])
        self.assertTrue(retried.data['replayed'])
        self.assertTrue(self.save(run, request_id=revision_request).data['replayed'])
        self.assertEqual(self.save(run, request_id=revision_request, reason='Different').data['error']['code'], 'idempotency_conflict')
        self.assertEqual(AuditEvent.objects.count(), 3)
        self.assertEqual(TraceRun.objects.get().run_version, 3)

    def test_intentional_duplicate_imports_allowed(self):
        a, b = self.upload(), self.upload()
        self.assertNotEqual(a.data['run_id'], b.data['run_id'])

    def test_unknown_import_fields_and_invalid_file(self):
        result = self.client.post('/api/traces/', {'file': SimpleUploadedFile('triangle.csv', SOURCE), 'request_id': str(uuid.uuid4()), 'status': 'reviewed'}, format='multipart')
        self.assertEqual(result.status_code, 400)
        self.assertEqual(self.upload(source=b'time_min,signal_au\n0,1\n0,2').status_code, 400)
        self.assertEqual(TraceRun.objects.count(), 0)

    def test_oversized_upload_and_body(self):
        self.assertEqual(self.upload(source=b'x'*262145).status_code, 413)
        self.assertEqual(self.upload(source=b'x'*600000).status_code, 413)
        self.assertEqual(TraceRun.objects.count(), 0)

    def test_ownership_all_routes(self):
        run = self.run_id()
        other = get_user_model().objects.create_user('other', password=PASSWORD)
        self.client.force_login(other)
        self.assertEqual(self.client.get('/api/traces/').data['items'], [])
        for path in ['', 'source/', 'report/']:
            self.assertEqual(self.client.get(f'/api/traces/{run}/{path}').status_code, 404)
        self.assertEqual(self.save(run).status_code, 404)
        self.assertEqual(self.complete(run, str(uuid.uuid4())).status_code, 404)
        self.assertEqual(self.client.post(f'/api/traces/{run}/preview/', {'start_time': 0, 'end_time': 2}, format='json').status_code, 404)

    def test_no_update_delete_paths_or_admin(self):
        run = self.run_id()
        revision = self.save(run).data['revision']
        for method in [self.client.patch, self.client.put, self.client.delete]:
            self.assertIn(method(f'/api/traces/{run}/', {}, format='json').status_code, [404, 405])
            self.assertIn(method(f'/api/traces/{run}/revisions/', {}, format='json').status_code, [404, 405])
        self.assertEqual(self.client.get('/admin/').status_code, 404)
        record = AnalysisRevision.objects.get(pk=revision['id'])
        with self.assertRaises(ValidationError):
            record.save()
        with self.assertRaises(ValidationError):
            record.delete()
        event = AuditEvent.objects.first()
        with self.assertRaises(ValidationError):
            event.save()

    def test_audit_failure_rolls_back_all_mutations(self):
        with patch('review.services.AuditEvent.objects.create', side_effect=RuntimeError('test failure')):
            with self.assertRaises(RuntimeError):
                services.import_trace(self.user, SimpleUploadedFile('a.csv', SOURCE), uuid.uuid4())
        self.assertEqual(TraceRun.objects.count(), 0)
        run = self.run_id()
        with patch('review.services.AuditEvent.objects.create', side_effect=RuntimeError('test failure')):
            with self.assertRaises(RuntimeError):
                services.save_revision(self.user, run, .5, 1.5, 'Reason', 1, uuid.uuid4())
        self.assertEqual(TraceRun.objects.get().run_version, 1)
        self.assertEqual(AnalysisRevision.objects.count(), 0)
        revision = self.save(run).data['revision']
        with patch('review.services.AuditEvent.objects.create', side_effect=RuntimeError('test failure')):
            with self.assertRaises(RuntimeError):
                services.complete_review(self.user, run, uuid.UUID(revision['id']), 2, uuid.uuid4())
        row = TraceRun.objects.get()
        self.assertEqual(row.status, 'draft')
        self.assertIsNone(row.reviewed_revision_id)
        self.assertEqual(row.run_version, 2)
        self.assertEqual(AuditEvent.objects.count(), 2)

    def test_report_immutable_self_contained_no_recalculation(self):
        run = self.run_id()
        self.assertEqual(self.client.get(f'/api/traces/{run}/report/').status_code, 409)
        revision = self.save(run).data['revision']
        self.complete(run, revision['id'])
        first = self.client.get(f'/api/traces/{run}/report/').content
        with patch('review.services.analyze_trace', side_effect=AssertionError('Historical calculation forbidden')):
            second = self.client.get(f'/api/traces/{run}/report/').content
        self.assertEqual(first, second)
        get_user_model().objects.filter(pk=self.user.pk).update(username='renamed')
        self.assertEqual(first, self.client.get(f'/api/traces/{run}/report/').content)
        data = json.loads(first)
        self.assertEqual(data['review']['revision_id'], revision['id'])
        self.assertEqual(data['revisions'][0]['area_fraction_percent'], 75)
        self.assertEqual(base64.b64decode(data['source']['content']), SOURCE)
        download = self.client.get(f'/api/traces/{run}/report/?download=1')
        self.assertEqual(b''.join(download.streaming_content), first)
        self.assertIn('attachment;', download['Content-Disposition'])

    def test_list_pagination_does_not_return_points(self):
        self.upload(); self.upload()
        page = self.client.get('/api/traces/?limit=1').data
        next_page = self.client.get('/api/traces/?limit=1&offset=1').data
        self.assertEqual(page['total'], 2)
        self.assertEqual(len(page['items']), 1)
        self.assertNotEqual(page['items'][0]['id'], next_page['items'][0]['id'])
        self.assertNotIn('points', page['items'][0])


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class AuthenticationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('analyst', password=PASSWORD)
        self.client = APIClient(enforce_csrf_checks=True)

    def test_login_requires_csrf_and_rotates_token(self):
        before = self.client.get('/api/session/').json()['csrf_token']
        self.assertEqual(self.client.post('/api/login/', {'username': 'analyst', 'password': PASSWORD}).status_code, 403)
        response = self.client.post('/api/login/', {'username': 'analyst', 'password': PASSWORD}, HTTP_X_CSRFTOKEN=before)
        self.assertEqual(response.status_code, 200)
        after = response.json()['csrf_token']
        self.assertNotEqual(before, after)
        self.assertEqual(self.client.post('/api/logout/', HTTP_X_CSRFTOKEN=before).status_code, 403)
        self.assertEqual(self.client.post('/api/logout/', HTTP_X_CSRFTOKEN=after).status_code, 204)
        self.assertFalse(self.client.get('/api/session/').json()['authenticated'])

    def test_all_domain_routes_need_login(self):
        token = self.client.get('/api/session/').json()['csrf_token']
        run = str(uuid.uuid4())
        for path in ['traces/', f'traces/{run}/', f'traces/{run}/source/', f'traces/{run}/report/']:
            response = self.client.get('/api/' + path)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.data['error']['code'], 'authentication_required')
        for suffix, data in [('preview/', {}), ('revisions/', {}), ('complete-review/', {})]:
            self.assertEqual(self.client.post(f'/api/traces/{run}/{suffix}', data, format='json', HTTP_X_CSRFTOKEN=token).status_code, 403)

    def test_csrf_on_authenticated_mutations(self):
        token = self.client.get('/api/session/').json()['csrf_token']
        token = self.client.post('/api/login/', {'username': 'analyst', 'password': PASSWORD}, HTTP_X_CSRFTOKEN=token).json()['csrf_token']
        run = str(uuid.uuid4())
        for path in ['traces/', f'traces/{run}/preview/', f'traces/{run}/revisions/', f'traces/{run}/complete-review/', 'logout/']:
            response = self.client.post('/api/' + path, {}, format='multipart' if path == 'traces/' else 'json')
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.data['error']['code'], 'csrf_failed')
        response = self.client.post('/api/traces/', {'file': SimpleUploadedFile('a.csv', SOURCE), 'request_id': str(uuid.uuid4())}, format='multipart', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 201)
