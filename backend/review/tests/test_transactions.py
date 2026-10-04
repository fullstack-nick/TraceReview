from concurrent.futures import ThreadPoolExecutor
import sqlite3
import threading
import uuid
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connections, OperationalError
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIClient
from review.exceptions import DomainError
from review.models import AnalysisRevision, AuditEvent, TraceRun
from review import services


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('race-analyst')
        receipt = services.import_trace(self.user, SimpleUploadedFile('race.csv', b'time_min,signal_au\n0,0\n1,2\n2,0\n'), uuid.uuid4())
        self.run = receipt['run_id']

    def race(self, operations):
        barrier = threading.Barrier(len(operations))
        user_id = self.user.pk
        def worker(operation):
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=user_id)
                barrier.wait(timeout=10)
                try:
                    return operation(user)
                except DomainError as error:
                    return error.code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(operations)) as executor:
            return list(executor.map(worker, operations))

    def test_two_saves_compete_for_same_version(self):
        results = self.race([lambda user: services.save_revision(user, self.run, .5, 1.5, 'First tab', 1, uuid.uuid4()),
                             lambda user: services.save_revision(user, self.run, .4, 1.6, 'Second tab', 1, uuid.uuid4())])
        self.assertEqual(sum(isinstance(r, dict) for r in results), 1)
        self.assertIn('version_conflict', results)
        self.assertEqual(AnalysisRevision.objects.count(), 1)
        self.assertEqual(AuditEvent.objects.count(), 2)
        self.assertEqual(TraceRun.objects.get().run_version, 2)

    def test_save_and_completion_cannot_lock_unintended_revision(self):
        initial = services.save_revision(self.user, self.run, .5, 1.5, 'First selection', 1, uuid.uuid4())
        revision_id = uuid.UUID(initial['revision']['id'])
        results = self.race([lambda user: services.save_revision(user, self.run, .4, 1.6, 'Revised', 2, uuid.uuid4()),
                             lambda user: services.complete_review(user, self.run, revision_id, 2, uuid.uuid4())])
        self.assertEqual(sum(isinstance(r, dict) for r in results), 1)
        run = TraceRun.objects.get()
        self.assertEqual(run.run_version, 3)
        self.assertEqual(AuditEvent.objects.count(), 3)
        if run.status == 'reviewed':
            self.assertEqual(run.reviewed_revision_id, revision_id)
            self.assertEqual(run.latest_revision_id, revision_id)
            self.assertEqual(AnalysisRevision.objects.count(), 1)
        else:
            self.assertEqual(AnalysisRevision.objects.count(), 2)

    def test_simultaneous_same_id_is_one_commit(self):
        operation_id = uuid.uuid4()
        def save(user):
            return services.save_revision(user, self.run, .5, 1.5, 'Same intent', 1, operation_id)
        results = self.race([save, save])
        self.assertTrue(all(isinstance(r, dict) for r in results), results)
        self.assertEqual(sorted(r['replayed'] for r in results), [False, True])
        self.assertEqual(AnalysisRevision.objects.count(), 1)

    def test_busy_error_maps_to_retryable_503(self):
        client = APIClient(); client.force_login(self.user)
        with patch('review.views.services.save_revision', side_effect=OperationalError('database is locked')):
            result = client.post(f'/api/traces/{self.run}/revisions/', {'start_time': .5, 'end_time': 1.5, 'reason': 'Busy test', 'expected_version': 1, 'request_id': str(uuid.uuid4())}, format='json')
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.data['error']['code'], 'database_busy')
        self.assertEqual(AnalysisRevision.objects.count(), 0)

    def test_real_file_database_and_immediate_lock(self):
        db = connections['default']
        self.assertFalse(str(db.settings_dict['NAME']).startswith('file:memory'))
        self.assertNotEqual(str(db.settings_dict['NAME']), ':memory:')
        with sqlite3.connect(db.settings_dict['NAME'], timeout=.05) as a, sqlite3.connect(db.settings_dict['NAME'], timeout=.05) as b:
            a.execute('BEGIN IMMEDIATE')
            with self.assertRaises(sqlite3.OperationalError):
                b.execute('BEGIN IMMEDIATE')
            a.rollback()
