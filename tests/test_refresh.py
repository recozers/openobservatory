import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from dcheat.gee import _ee


class EarthEngineAuthTests(unittest.TestCase):
    def test_service_account_environment(self):
        ee = MagicMock()
        key = json.dumps({'client_email': 'robot@example.invalid', 'project_id': 'source-project', 'private_key': 'test-only'})
        with patch.dict(sys.modules, ee=ee), patch.dict(os.environ, {'EE_SERVICE_ACCOUNT_JSON': key, 'EE_PROJECT': 'override-project'}, clear=True):
            self.assertIs(_ee(), ee)
        ee.ServiceAccountCredentials.assert_called_once_with('robot@example.invalid', key_data=key)
        ee.Initialize.assert_called_once_with(ee.ServiceAccountCredentials.return_value, project='override-project')
        ee.Authenticate.assert_not_called()

    def test_file_credentials_and_project_from_key(self):
        ee = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'key.json'
            path.write_text(json.dumps({'client_email': 'robot@example.invalid', 'project_id': 'key-project'}))
            with patch.dict(sys.modules, ee=ee), patch.dict(os.environ, {'GOOGLE_APPLICATION_CREDENTIALS': str(path)}, clear=True):
                _ee()
        ee.Initialize.assert_called_once_with(ee.ServiceAccountCredentials.return_value, project='key-project')

    def test_bad_key_does_not_leak_or_fall_back(self):
        ee = MagicMock()
        with patch.dict(sys.modules, ee=ee), patch.dict(os.environ, {'EE_SERVICE_ACCOUNT_JSON': 'private-material'}, clear=True):
            with self.assertRaisesRegex(ValueError, '^Invalid Earth Engine service-account JSON$'):
                _ee()
        ee.Authenticate.assert_not_called()

    def test_ci_never_starts_interactive_auth(self):
        ee = MagicMock()
        ee.Initialize.side_effect = RuntimeError('expired')
        with patch.dict(sys.modules, ee=ee), patch.dict(os.environ, {'CI': 'true'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'credentials unavailable in CI'):
                _ee()
        ee.Authenticate.assert_not_called()

    def test_local_oauth_still_works(self):
        ee = MagicMock()
        ee.Initialize.side_effect = [RuntimeError('expired'), None]
        with patch.dict(sys.modules, ee=ee), patch.dict(os.environ, {'EE_PROJECT': 'local-project'}, clear=True):
            _ee()
        ee.Authenticate.assert_called_once()
        self.assertEqual(ee.Initialize.call_count, 2)


if __name__ == '__main__':
    unittest.main()
