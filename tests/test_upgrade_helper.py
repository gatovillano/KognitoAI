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

    @patch('scripts.upgrade_helper.os.path.isfile')
    def test_find_ext_install_py(self, mock_isfile):
        # 1. Test local path exists
        mock_isfile.side_effect = lambda path: 'kognito-ai/extensions/ext_local' in path
        path = uh.find_ext_install_py('ext_local')
        self.assertIn('kognito-ai/extensions/ext_local/install.py', path)

        # 2. Test parent path exists when local doesn't
        mock_isfile.side_effect = lambda path: 'Proyectos/KognitoAI/extensions/ext_parent' in path
        path = uh.find_ext_install_py('ext_parent')
        self.assertIn('Proyectos/KognitoAI/extensions/ext_parent/install.py', path)

    @patch('scripts.upgrade_helper.os.path.isdir')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="from extensions.jitsi_meet.backend.router import ...")
    @patch('scripts.upgrade_helper.os.path.isfile')
    def test_is_extension_active(self, mock_isfile, mock_open, mock_isdir):
        # Test backend dir heuristic
        mock_isdir.side_effect = lambda path: path.endswith('api/gallery_selection_panel')
        self.assertTrue(uh.is_extension_active('gallery_selection_panel'))

        # Test skill dir heuristic
        mock_isdir.side_effect = lambda path: path.endswith('skills/kai_ethno_skill')
        self.assertTrue(uh.is_extension_active('kai_ethno'))

        # Test registry in main.py heuristic
        mock_isdir.side_effect = lambda path: False
        mock_isfile.return_value = True  # main.py exists
        self.assertTrue(uh.is_extension_active('jitsi_meet'))

if __name__ == '__main__':
    unittest.main()
