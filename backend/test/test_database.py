#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright 2017-2018 - Edoardo Morassutto <edoardo.morassutto@gmail.com>
import os
import unittest
from unittest.mock import patch

from terry.config import Config
from terry.database import Database
from terry.schema import Schema
from test.utils import Utils


class TestDatabase(unittest.TestCase):
    def setUp(self):
        Utils.prepare_test(connect_database=False)

    def test_gen_id(self):
        MIN_ID_LENGTH = 10
        id = Database.gen_id()
        self.assertIsInstance(id, str)
        self.assertGreaterEqual(len(id), MIN_ID_LENGTH)

    def test_connect_to_database(self):
        Database.connected = False
        Database.connect_to_database()

    def test_double_connect_to_database(self):
        Database.connected = False
        Database.connect_to_database()
        with self.assertRaises(RuntimeError) as ex:
            Database.connect_to_database()
        self.assertEqual("Database already loaded", ex.exception.args[0])

    def test_disconnect_database(self):
        Database.connected = True
        Database.disconnect_database()
        self.assertFalse(Database.connected)

    def test_invalid_database_path(self):
        Config.db = "/path/that/not/exists"
        Database.connected = False
        with self.assertRaises(Exception):
            Database.connect_to_database()

    def test_missing_db(self):
        db_path = Utils.new_tmp_file()
        os.remove(db_path)
        Config.db = db_path
        Database.connected = False
        Database.connect_to_database()

    def test_database_upgrade(self):
        backup = Schema.UPDATERS
        Schema.UPDATERS = [
            "CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);",
            # this table is needed
            "CREATE TABLE dummy_test (foo INTEGER);",
            "INSERT INTO dummy_test VALUES(42);",
        ]

        Database.connected = False
        Database.connect_to_database()
        Database.c.execute("SELECT * FROM dummy_test")
        row = Database.c.fetchone()
        self.assertEqual(42, row[0])
        Database.c.execute("SELECT * FROM metadata WHERE key = 'schema_version'")
        row = Database.c.fetchone()

        self.assertEqual(len(Schema.UPDATERS) - 1, int(row[1]))

        Schema.UPDATERS = backup

    def test_get_meta(self):
        Database.connected = False
        Database.connect_to_database()

        schema_version = Database.get_meta_int("schema_version", None)
        self.assertEqual(len(Schema.UPDATERS) - 1, schema_version)

    def test_get_meta_none(self):
        Database.connected = False
        Database.connect_to_database()

        Database.set_meta("test", None)
        Database.set_meta("test2", "None")
        self.assertEqual(Database.get_meta("test", None), None)
        self.assertEqual(Database.get_meta_int("test", None), None)
        self.assertEqual(Database.get_meta("test2", None), "None")

    def test_get_meta_default(self):
        Database.connected = False
        Database.connect_to_database()

        meta = Database.get_meta("this_key_doesnt_exist", "default_value_is_cool")
        self.assertEqual("default_value_is_cool", meta)

    def test_get_meta_default_not_used(self):
        Database.connected = False
        Database.connect_to_database()

        Database.set_meta("this_key_doesnt_exist", "cool_value")
        meta = Database.get_meta("this_key_doesnt_exist", "default_value_is_not_cool")
        self.assertEqual("cool_value", meta)

    def test_get_meta_type(self):
        Database.connected = False
        Database.connect_to_database()

        schema_version = Database.get_meta_int("schema_version", None)
        self.assertIsInstance(schema_version, int)

    def test_get_meta_default_type(self):
        Database.connected = False
        Database.connect_to_database()

        meta = Database.get_meta_int("not_existing_key", "42")
        self.assertIsInstance(meta, str)

    def test_get_meta_type_bool(self):
        Database.connected = False
        Database.connect_to_database()

        Database.set_meta("boooool", str(True))
        self.assertTrue(Database.get_meta_bool("boooool", None))
        Database.set_meta("boooool2", str(False))
        self.assertFalse(Database.get_meta_bool("boooool2", None))

    def test_set_meta(self):
        Database.connected = False
        Database.connect_to_database()

        Database.set_meta("random_key", str(42))
        value = Database.get_meta_int("random_key", None)
        self.assertEqual(42, value)

    def test_set_meta_overwrite(self):
        Database.connected = False
        Database.connect_to_database()

        Database.set_meta("random_key", str(4242))
        Database.set_meta("random_key", str(42))
        value = Database.get_meta_int("random_key", None)
        self.assertEqual(42, value)

    def test_del_meta(self):
        Database.connected = False
        Database.connect_to_database()

        Database.set_meta("random_key", "")
        self.assertTrue(Database.del_meta("random_key"))
        self.assertIsNone(Database.get_meta("random_key", None))

    def test_del_meta_non_exist(self):
        Database.connected = False
        Database.connect_to_database()

        self.assertFalse(Database.del_meta("random_key"))
        self.assertIsNone(Database.get_meta("random_key", None))

    def test_transaction_commit(self):
        Database.connected = False
        Database.connect_to_database()

        Database.begin()
        Database.set_meta("random_foobar", str(123), autocommit=False)
        Database.commit()

        self.assertEqual(123, Database.get_meta_int("random_foobar", None))

    def test_transaction_rollback(self):
        Database.connected = False
        Database.connect_to_database()

        Database.begin()
        Database.set_meta("random_foobar", str(123), autocommit=False)
        Database.rollback()

        self.assertEqual(42, Database.get_meta("random_foobar", 42))

    def test_dictify(self):
        Database.connected = False
        Database.connect_to_database()

        Database.set_meta("random_key", "random_value")
        Database.c.execute("SELECT * FROM metadata WHERE key = 'random_key'")
        dct = Database.dictify()

        self.assertDictEqual({"key": "random_key", "value": "random_value"}, dct)

    def test_dictify_all(self):
        Database.connected = False
        Database.connect_to_database()

        Database.c.execute("DELETE FROM metadata")
        Database.c.execute("INSERT INTO metadata (key, value) VALUES ('foo1', 'bar')")
        Database.c.execute("INSERT INTO metadata (key, value) VALUES ('foo2', 'bar')")
        Database.c.execute("SELECT * FROM metadata")
        lst = Database.dictify_all()

        self.assertIsInstance(lst, list)
        self.assertEqual(2, len(lst))

    def test_input_invalid_params(self):
        Database.connected = False
        Database.connect_to_database()

        with self.assertRaises(ValueError) as ex:
            Database.get_input()

        self.assertEqual("Invalid parameters to get_input", ex.exception.args[0])

    def test_do_write_rollback(self):
        Database.connected = False
        Database.connect_to_database()

        with patch("terry.database.Database.commit", side_effect=ValueError("Ops...")):
            with self.assertRaises(ValueError):
                Database.do_write(
                    True,
                    """
                    INSERT INTO metadata (key, value) 
                    VALUES (:key, :value)
                """,
                    {"key": "ciao", "value": "mondo"},
                )

        self.assertIsNone(Database.get_meta("ciao", None))
