import sqlite3
import unittest
from unittest.mock import patch

import tracker


class TrackerHistoryTest(unittest.TestCase):
    def test_imports_only_the_current_users_sessions(self):
        history = '\n'.join([
            'other pts/0 Wed Jan  1 10:00:00 2020 - Wed Jan  1 11:00:00 2020 (01:00)',
            'sample-other pts/0 Wed Jan  1 10:00:00 2020 - Wed Jan  1 12:00:00 2020 (02:00)',
            'sample pts/0 Wed Jan  1 10:00:00 2020 - Wed Jan  1 11:00:00 2020 (01:00)',
        ])
        with sqlite3.connect(':memory:') as connection:
            connection.executescript('''
                CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE presence (day TEXT PRIMARY KEY, seconds INTEGER NOT NULL);
            ''')
            with patch.object(tracker, 'run', return_value=history), patch.object(tracker.getpass, 'getuser', return_value='sample'):
                tracker.seed_from_wtmp(connection)
            self.assertEqual(connection.execute('SELECT day, seconds FROM presence').fetchall(), [('2020-01-01', 3600)])
            tracker.seed_from_wtmp(connection)
            self.assertEqual(connection.execute('SELECT SUM(seconds) FROM presence').fetchone()[0], 3600)


if __name__ == '__main__':
    unittest.main()
