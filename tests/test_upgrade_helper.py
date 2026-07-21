import os
import json
import unittest
from unittest.mock import patch, MagicMock

# Import helper
import scripts.upgrade_helper as uh

class TestUpgradeHelper(unittest.TestCase):
    @patch('scripts.upgrade_helper.os.path.isdir')
    @patch('scripts.upgrade_helper.os.listdir')
    @patch('scripts.upgrade_helper.os.path.isfile')
    def test_get_installed_extensions(self, mock_isfile, mock_listdir, mock_isdir):
        mock_listdir.return_value = ['fediverso', 'some_file.txt']
        mock_isdir.side_effect = lambda path: path.endswith('extensions') or 'fediverso' in path or 'api/fediverso' in path
        mock_isfile.side_effect = lambda path: 'install.py' in path
        
        extensions = uh.get_installed_extensions()
        self.assertEqual(extensions, ['fediverso'])

    @patch('scripts.upgrade_helper.get_installed_extensions')
    @patch('scripts.upgrade_helper.subprocess.run')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('scripts.upgrade_helper.os.makedirs')
    @patch('scripts.upgrade_helper.os.path.exists')
    def test_pre_upgrade(self, mock_exists, mock_makedirs, mock_file, mock_run, mock_get_extensions):
        mock_get_extensions.return_value = ['fediverso']
        uh.pre_upgrade()
        
        mock_file.assert_called_with(uh.STATE_FILE, "w", encoding="utf-8")
        mock_run.assert_called_once()
        self.assertIn('--uninstall', mock_run.call_args[0][0])

    @patch('scripts.upgrade_helper.os.path.exists')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data='["fediverso"]')
    @patch('scripts.upgrade_helper.subprocess.run')
    @patch('scripts.upgrade_helper.os.path.isfile')
    @patch('scripts.upgrade_helper.os.remove')
    def test_post_upgrade(self, mock_remove, mock_isfile, mock_run, mock_file, mock_exists):
        mock_exists.return_value = True
        mock_isfile.return_value = True
        
        uh.post_upgrade()
        
        mock_run.assert_called_once()
        self.assertNotIn('--uninstall', mock_run.call_args[0][0])
        mock_remove.assert_called_with(uh.STATE_FILE)

if __name__ == '__main__':
    unittest.main()
