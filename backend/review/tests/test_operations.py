from io import StringIO
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command, CommandError
from django.test import TransactionTestCase, override_settings
from review import services
from review.models import TraceRun
from review.reports import report_bytes


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class OperationsTests(TransactionTestCase):
    def test_account_initialization_preserves_existing_credentials(self):
        with patch.dict(os.environ, TRACEREVIEW_ANALYST_PASSWORD='Initial-test-password-731!'):
            call_command('init_analyst', username='local-analyst', stdout=StringIO())
        user = get_user_model().objects.get(username='local-analyst')
        original = user.password
        with patch.dict(os.environ, TRACEREVIEW_ANALYST_PASSWORD='Replacement-not-applied-442!'):
            call_command('init_analyst', username='local-analyst', stdout=StringIO())
        user.refresh_from_db()
        self.assertEqual(user.password, original)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_backup_restored_in_new_process_keeps_exact_review_and_source(self):
        user = get_user_model().objects.create_user('backup-analyst')
        source = b'\xef\xbb\xbftime_min,signal_au\r\n0,0\r\n1,2\r\n2,0\r\n'
        run_id = services.import_trace(user, SimpleUploadedFile('original.csv', source), uuid.uuid4())['run_id']
        receipt = services.save_revision(user, run_id, .5, 1.5, 'Preserve this revision.', 1, uuid.uuid4())
        services.complete_review(user, run_id, uuid.UUID(receipt['revision']['id']), 2, uuid.uuid4())
        expected = report_bytes(TraceRun.objects.get(pk=run_id))
        with tempfile.TemporaryDirectory(prefix='tracereview-backup-') as directory:
            backup = Path(directory) / 'backup.sqlite3'
            restored = Path(directory) / 'restored.sqlite3'
            call_command('backup_database', str(backup), stdout=StringIO())
            with self.assertRaises(CommandError):
                call_command('backup_database', str(backup), stdout=StringIO())
            shutil.copyfile(backup, restored)
            code = (
                'import os,sys;sys.path.insert(0,"backend");'
                'os.environ["DJANGO_SETTINGS_MODULE"]="config.settings";'
                'import django;django.setup();'
                'from review.models import TraceRun;from review.reports import report_bytes;'
                'sys.stdout.buffer.write(report_bytes(TraceRun.objects.get()))'
            )
            for _ in range(2):
                actual = subprocess.check_output([sys.executable, '-c', code], cwd=settings.BASE_DIR,
                                                 env={**os.environ, 'TRACEREVIEW_DB': str(restored)}, timeout=20)
                self.assertEqual(actual, expected)
