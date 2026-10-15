import os
import time
import tempfile
import sqlite3
import unittest
from unittest.mock import MagicMock, patch
import sys

# Add repo to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../cli")))

from cli.sync_logic import KognitoSyncManager, is_ignored_path


class TestSyncDuplicatePrevention(unittest.TestCase):
    def test_is_ignored_path(self):
        self.assertTrue(is_ignored_path("~test.docx"))
        self.assertTrue(is_ignored_path("~$test.docx"))
        self.assertTrue(is_ignored_path(".hidden.txt"))
        self.assertTrue(is_ignored_path("test.tmp"))
        self.assertTrue(is_ignored_path("test.swp"))
        self.assertTrue(is_ignored_path("test.bak"))
        self.assertTrue(is_ignored_path("test.txt~"))
        self.assertTrue(is_ignored_path("goutputstream-12345"))
        self.assertTrue(is_ignored_path("desktop.ini"))
        self.assertTrue(is_ignored_path("Thumbs.db"))
        self.assertTrue(is_ignored_path(".DS_Store"))
        
        # Valid files
        self.assertFalse(is_ignored_path("documento.txt"))
        self.assertFalse(is_ignored_path("nota.docx"))
        self.assertFalse(is_ignored_path("informe_final.pdf"))

    def test_upload_new_file_prevents_duplicate_when_already_in_db(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            sync_dir = os.path.join(temp_dir, "sync")
            os.makedirs(os.path.join(sync_dir, "Personal"), exist_ok=True)
            
            manager = KognitoSyncManager("http://dummy-server", "user", "pass", sync_dir, db_path)
            
            test_file = os.path.join(sync_dir, "Personal", "mi_texto.txt")
            with open(test_file, "w") as f:
                f.write("Hola mundo")
                
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Mock httpx.post for first upload
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"id": "doc-uuid-1", "updated_at": "2026-10-01T12:00:00"}
            
            with patch("httpx.post", return_value=mock_resp) as mock_post:
                res1 = manager.upload_new_file(cursor, test_file)
                conn.commit()
                
                self.assertIsNotNone(res1)
                doc_id1, path1 = res1
                self.assertEqual(doc_id1, "doc-uuid-1")
                self.assertEqual(mock_post.call_count, 1)
                
                # Second call to upload_new_file with the same path should NOT call POST again
                mock_put = MagicMock()
                mock_put.status_code = 200
                mock_put.json.return_value = {"updated_at": "2026-10-01T12:00:01"}
                with patch("httpx.put", return_value=mock_put) as mock_put_patch:
                    res2 = manager.upload_new_file(cursor, test_file)
                    conn.commit()
                    
                    # Should not have called httpx.post a second time!
                    self.assertEqual(mock_post.call_count, 1)
                    self.assertIsNotNone(res2)
                    doc_id2, path2 = res2
                    self.assertEqual(doc_id2, "doc-uuid-1")

    def test_internal_move_not_reuploaded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            sync_dir = os.path.join(temp_dir, "sync")
            os.makedirs(os.path.join(sync_dir, "Personal"), exist_ok=True)
            
            manager = KognitoSyncManager("http://dummy-server", "user", "pass", sync_dir, db_path)
            manager.is_running = True
            
            root_file = os.path.join(sync_dir, "texto_raiz.txt")
            with open(root_file, "w") as f:
                f.write("Contenido")
                
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"id": "doc-uuid-root", "updated_at": "2026-10-01T12:00:00"}
            
            with patch("httpx.post", return_value=mock_resp) as mock_post:
                # Uploading root file moves it to Personal/texto_raiz.txt
                res = manager.upload_new_file(cursor, root_file)
                conn.commit()
                
                personal_file = os.path.join(sync_dir, "Personal", "texto_raiz.txt")
                self.assertTrue(os.path.exists(personal_file))
                self.assertFalse(os.path.exists(root_file))
                self.assertEqual(mock_post.call_count, 1)
                
                # Now simulate watchdog emitting on_moved for the internal move
                manager.handle_local_move(root_file, personal_file)
                
                # Post should STILL be 1 (never called a second time)
                self.assertEqual(mock_post.call_count, 1)

    def test_atomic_save_updates_instead_of_duplicate_upload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            sync_dir = os.path.join(temp_dir, "sync")
            os.makedirs(os.path.join(sync_dir, "Personal"), exist_ok=True)
            
            manager = KognitoSyncManager("http://dummy-server", "user", "pass", sync_dir, db_path)
            manager.is_running = True
            
            target_file = os.path.join(sync_dir, "Personal", "doc.txt")
            with open(target_file, "w") as f:
                f.write("Version 1")
                
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Pre-register document
            manager.register_in_db(cursor, target_file, "doc-123", None, None, "2026-10-01T10:00:00")
            conn.commit()
            
            # Editor creates temp file and renames it to target_file (atomic save)
            temp_file = os.path.join(sync_dir, "Personal", "doc.txt.tmp")
            with open(temp_file, "w") as f:
                f.write("Version 2 with more text")
            # Advance mtime so it's definitely different from registration
            os.utime(temp_file, (time.time() + 5, time.time() + 5))
                
            mock_post = MagicMock()
            mock_put = MagicMock()
            mock_put.status_code = 200
            mock_put.json.return_value = {"updated_at": "2026-10-01T10:01:00"}
            
            with patch("httpx.post", mock_post), patch("httpx.put", return_value=mock_put) as patched_put:
                os.replace(temp_file, target_file)
                manager.handle_local_move(temp_file, target_file)
                
                # Should have called PUT (update) and NOT POST (upload)
                self.assertEqual(mock_post.call_count, 0)
                self.assertEqual(patched_put.call_count, 1)


    def test_debounced_change_coalesces_create_and_modify(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            sync_dir = os.path.join(temp_dir, "sync")
            os.makedirs(os.path.join(sync_dir, "Personal"), exist_ok=True)
            
            manager = KognitoSyncManager("http://dummy-server", "user", "pass", sync_dir, db_path)
            manager.is_running = True
            
            doc_file = os.path.join(sync_dir, "Personal", "rapid_note.txt")
            with open(doc_file, "w") as f:
                f.write("Some text")
                
            mock_post = MagicMock()
            mock_post.status_code = 200
            mock_post.json.return_value = {"id": "doc-uuid-rapid", "updated_at": "2026-10-01T10:00:00"}
            
            with patch("httpx.post", mock_post):
                # Trigger multiple rapid events: create, modify, modify
                manager.handle_local_change(doc_file, "create")
                manager.handle_local_change(doc_file, "modify")
                manager.handle_local_change(doc_file, "modify")
                
                # Should have only ONE timer running
                with manager._debounce_lock:
                    self.assertEqual(len(manager._debounce_timers), 1)
                
                # Trigger the debounced callback manually
                manager._process_debounced_change(doc_file, "modify")
                
                # Exactly ONE upload happened!
                self.assertEqual(mock_post.call_count, 1)


if __name__ == "__main__":
    unittest.main()

