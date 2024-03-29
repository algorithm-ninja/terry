#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright 2017-2018 - Edoardo Morassutto <edoardo.morassutto@gmail.com>
# Copyright 2018 - Luca Versari <veluca93@gmail.com>
# Copyright 2018 - Massimo Cairo <cairomassimo@gmail.com>
from datetime import datetime, timezone
import os.path
import subprocess

import unittest
import dateutil.parser
import ruamel.yaml
from werkzeug.exceptions import Forbidden, BadRequest, NotFound

from terry import crypto
from terry.config import Config
from terry.database import Database
from terry.handlers.admin_handler import AdminHandler
from terry.logger import Logger
from test.test_logger import TestLogger
from test.utils import Utils


class TestAdminHandler(unittest.TestCase):
    def setUp(self):
        Utils.prepare_test()
        self.admin_handler = AdminHandler()

        Database.set_meta("admin_token", "ADMIN-TOKEN")

        self.log_backup = Logger.LOG_LEVEL
        Logger.LOG_LEVEL = -9001  # enable the logs
        Logger.disable_console_logging = True  # .. but not to console

    def tearDown(self):
        Logger.LOG_LEVEL = self.log_backup

    def test_upload_pack_already_extracted(self):
        Database.set_meta("admin_token", "totally the real token")
        with self.assertRaises(Forbidden):
            self.admin_handler.upload_pack(
                file={"content": "foobar".encode(), "name": "pack.zip.enc"}
            )

    def test_upload_pack_already_uploaded(self):
        path = os.path.join(Utils.new_tmp_dir(), "pack.zip.enc")
        with open(path, "wb") as f:
            f.write(b"hola!")
        Config.encrypted_file = path
        Database.del_meta("admin_token")
        with self.assertRaises(Forbidden):
            self.admin_handler.upload_pack(
                file={"content": "foobar".encode(), "name": "pack.zip.enc"}
            )

    def test_upload_pack(self):
        Utils.setup_encrypted_file()
        upload_path = os.path.join(os.path.dirname(__file__), "../assets/pack.zip.enc")
        os.remove(Config.encrypted_file)

        with open(upload_path, "rb") as f:
            content = f.read()
        Database.del_meta("admin_token")

        self.admin_handler.upload_pack(
            file={"content": content, "name": "pack.zip.enc"}
        )
        self.assertTrue(os.path.exists(Config.encrypted_file))

    def test_upload_invalid_pack(self):
        enc_path = os.path.join(Utils.new_tmp_dir(), "pack.zip.enc")
        Config.encrypted_file = enc_path

        Database.del_meta("admin_token")
        with self.assertRaises(Forbidden):
            self.admin_handler.upload_pack(
                file={"content": b"totally not a pack", "name": "pack.zip.enc"}
            )
        self.assertFalse(os.path.exists(enc_path))

    def test_append_log_invalid_secret(self):
        Config.append_log_secret = "yep"
        with self.assertRaises(Forbidden):
            self.admin_handler.append_log(
                append_log_secret="nope",
                level="ERROR",
                category="TESTING",
                message="You shall not pass!",
            )

    def test_append_log_invalid_level(self):
        Config.append_log_secret = "yep"
        with self.assertRaises(BadRequest):
            self.admin_handler.append_log(
                append_log_secret="yep",
                level="BARABBA",
                category="TESTING",
                message="You shall not pass!",
            )

    def test_append_log(self):
        Config.append_log_secret = "yep"
        self.admin_handler.append_log(
            append_log_secret="yep",
            level="ERROR",
            category="TESTING",
            message="Message",
        )
        Logger.c.execute("SELECT * FROM logs WHERE category = 'TESTING'")
        row = Logger.c.fetchone()
        self.assertEqual("TESTING", row[1])
        self.assertEqual(Logger.ERROR, int(row[2]))
        self.assertEqual("Message", row[3])

    def test_log_invalid_token(self):
        with self.assertRaises(Forbidden) as ex:
            self.admin_handler.log(
                start_date=None,
                end_date=None,
                level=None,
                category=None,
                admin_token="invalid token",
                _ip=None,
            )

        self.assertIn("Invalid admin token", ex.exception.response.data.decode())

    def test_log_get_dates(self):
        TestLogger.load_logs()

        start_date = datetime.fromtimestamp(datetime.now().timestamp() - 10).isoformat()
        end_date = datetime.fromtimestamp(datetime.now().timestamp() + 10).isoformat()

        res = self.admin_handler.log(
            start_date=start_date,
            end_date=end_date,
            level="INFO",
            admin_token="ADMIN-TOKEN",
            _ip="1.2.3.4",
        )
        self.assertEqual(
            3, len(res["items"])
        )  # NOTE: there is also the LOGIN_ADMIN row

    def test_log_category(self):
        TestLogger.load_logs()

        start_date = datetime.fromtimestamp(datetime.now().timestamp() - 10).isoformat()
        end_date = datetime.fromtimestamp(datetime.now().timestamp() + 10).isoformat()

        res = self.admin_handler.log(
            start_date=start_date,
            end_date=end_date,
            level="DEBUG",
            admin_token="ADMIN-TOKEN",
            _ip="1.2.3.4",
            category="CATEGORY",
        )
        self.assertEqual(2, len(res["items"]))

    def test_log_invalid_level(self):
        with self.assertRaises(BadRequest):
            self.admin_handler.log(
                start_date=None,
                end_date=None,
                level="NOT-EXISTING-LEVEL",
                admin_token="ADMIN-TOKEN",
                _ip="1.2.3.4",
            )

    def test_log_invalid_date(self):
        with self.assertRaises(BadRequest):
            self.admin_handler.log(
                start_date="i'm not a date",
                end_date=None,
                level="ERROR",
                admin_token="ADMIN-TOKEN",
                _ip="1.2.3.4",
            )

    def test_start_invalid_token(self):
        with self.assertRaises(Forbidden) as ex:
            self.admin_handler.start(
                start_time="reset", admin_token="invalid token", _ip=None
            )

        self.assertIn("Invalid admin token", ex.exception.response.data.decode())

    def test_start_reset_already_started(self):
        Utils.start_contest()

        with self.assertRaises(Forbidden) as ex:
            self.admin_handler.start(
                start_time="reset", admin_token="ADMIN-TOKEN", _ip="1.2.3.4"
            )

        self.assertIn(
            "Contest has already been started", ex.exception.response.data.decode()
        )

    def test_start_now_already_started(self):
        Utils.start_contest()

        with self.assertRaises(Forbidden) as ex:
            self.admin_handler.start(
                start_time="now", admin_token="ADMIN-TOKEN", _ip="1.2.3.4"
            )

        self.assertIn(
            "Contest has already been started", ex.exception.response.data.decode()
        )

    def test_start_now(self):
        out = self.admin_handler.start("now", admin_token="ADMIN-TOKEN", _ip="1.2.3.4")

        start_time = dateutil.parser.parse(out["start_time"]).timestamp()
        self.assertTrue(start_time >= datetime.now(timezone.utc).timestamp() - 10)

        start_time_db = datetime.fromtimestamp(
            Database.get_meta_int("start_time", None), timezone.utc
        )
        self.assertEqual(start_time, start_time_db.timestamp())

    def test_start_now_but_started_in_future(self):
        Utils.start_contest(since=-100)
        out = self.admin_handler.start("now", admin_token="ADMIN-TOKEN", _ip="1.2.3.4")

        start_time = dateutil.parser.parse(out["start_time"]).timestamp()
        self.assertTrue(start_time >= datetime.now(timezone.utc).timestamp() - 10)

        start_time_db = datetime.fromtimestamp(
            Database.get_meta_int("start_time", None), timezone.utc
        )
        self.assertEqual(start_time, start_time_db.timestamp())

    def test_start_reset(self):
        Utils.start_contest(since=-100)
        out = self.admin_handler.start(
            "reset", admin_token="ADMIN-TOKEN", _ip="1.2.3.4"
        )

        self.assertIsNone(out["start_time"])
        self.assertIsNone(Database.get_meta_int("start_time", None))

    def test_start_scheduled(self):
        start_time_str = "2020-01-01T13:13:13.0Z"
        out = self.admin_handler.start(
            start_time_str, admin_token="ADMIN-TOKEN", _ip="1.2.3.4"
        )

        start_time = dateutil.parser.parse(out["start_time"])
        expected_start_time = dateutil.parser.parse(start_time_str)
        self.assertEqual(start_time, expected_start_time)

        start_time_db = datetime.fromtimestamp(
            Database.get_meta_float("start_time", None), timezone.utc
        )
        self.assertEqual(start_time, start_time_db)

    def test_set_extra_time_invalid_admin_token(self):
        with self.assertRaises(Forbidden) as ex:
            self.admin_handler.set_extra_time(
                admin_token="INVALID-TOKEN", extra_time=None, _ip=None
            )

        self.assertIn("Invalid admin token", ex.exception.response.data.decode())

    def test_set_extra_time_invalid_token(self):
        with self.assertRaises(Forbidden) as ex:
            self.admin_handler.set_extra_time(
                admin_token="ADMIN-TOKEN", extra_time=42, token="foobar", _ip=None
            )

        self.assertIn("No such user", ex.exception.response.data.decode())

    def test_set_extra_time_global(self):
        self.admin_handler.set_extra_time(
            admin_token="ADMIN-TOKEN", extra_time=42, _ip="1.2.3.4"
        )

        self.assertEqual(42, Database.get_meta_int("extra_time", None))

    def test_set_extra_time_user(self):
        Database.c.execute(
            "INSERT INTO users (token, name, surname, extra_time) VALUES ("
            "'user token', 'a', 'b', 0)"
        )

        self.admin_handler.set_extra_time(
            admin_token="ADMIN-TOKEN", extra_time=42, _ip="1.2.3.4", token="user token"
        )

        user = Database.get_user("user token")
        self.assertEqual(42, user["extra_time"])

    def test_status_invalid_token(self):
        with self.assertRaises(Forbidden) as ex:
            self.admin_handler.status(admin_token="invalid token", _ip=None)

        self.assertIn("Invalid admin token", ex.exception.response.data.decode())

    def test_status(self):
        Database.set_meta("start_time", 1234)
        res = self.admin_handler.status(admin_token="ADMIN-TOKEN", _ip="1.2.3.4")

        start_time = dateutil.parser.parse(res["start_time"])

        start_time_db = datetime.fromtimestamp(
            Database.get_meta_float("start_time", None), timezone.utc
        )
        self.assertEqual(start_time, start_time_db)
        self.assertEqual(0, Database.get_meta("extra_time", default=0))

    def test_user_list_invalid_token(self):
        with self.assertRaises(Forbidden) as ex:
            self.admin_handler.user_list(admin_token="invalid token", _ip=None)

        self.assertIn("Invalid admin token", ex.exception.response.data.decode())

    def test_user_list(self):
        Database.add_user("token", "Name", "Surname")
        Database.add_user("token2", "", "")
        Database.register_ip("token", "1.2.3.4")
        Database.register_ip("token", "1.2.3.5")

        res = self.admin_handler.user_list(admin_token="ADMIN-TOKEN", _ip=None)
        self.assertEqual(2, len(res["items"]))
        user1 = next(i for i in res["items"] if i["token"] == "token")
        user2 = next(i for i in res["items"] if i["token"] == "token2")

        self.assertEqual("token", user1["token"])
        self.assertEqual("Name", user1["name"])
        self.assertEqual("Surname", user1["surname"])
        self.assertEqual(2, len(user1["ip"]))

        self.assertEqual("token2", user2["token"])
        self.assertEqual(0, len(user2["ip"]))

    def test_pack_status_no_pack(self):
        Config.encrypted_file = "/cake/is/a/lie"
        status = self.admin_handler.pack_status()
        self.assertFalse(status["uploaded"])

    def test_pack_status(self):
        pack = Utils.new_tmp_file()
        Config.encrypted_file = pack
        encrypted = crypto.encode(b"fooobarr", b"#bellavita", b"foo: bar")
        with open(pack, "wb") as f:
            f.write(encrypted)
        status = self.admin_handler.pack_status()
        self.assertTrue(status["uploaded"])
        self.assertEqual(status["foo"], "bar")

    @unittest.skip
    def test_download_results(self):
        Config.storedir = Utils.new_tmp_dir()
        wd = os.getcwd()
        try:
            os.chdir(Config.storedir)
            with open("db.sqlite3_for_test", "w") as f:
                pass
            zip_location = self.admin_handler.download_results(
                admin_token="ADMIN-TOKEN", _ip="1.2.3.4"
            )["path"]
            with open(os.path.join(Config.storedir, zip_location)) as f:
                pass
        finally:
            os.chdir(wd)

    @unittest.skip
    def test_failed_download_results(self):
        Config.storedir = Utils.new_tmp_dir()
        wd = os.getcwd()
        try:
            os.chdir(Config.storedir)
            with self.assertRaises(subprocess.CalledProcessError) as ex:
                self.admin_handler.download_results(
                    admin_token="ADMIN-TOKEN", _ip="1.2.3.4"
                )
        finally:
            os.chdir(wd)

    def test_drop_contest_no_pack(self):
        Config.encrypted_file = "/not/exists"
        with self.assertRaises(NotFound):
            self.admin_handler.drop_contest("LALLA-BALALLA")

    def test_drop_contest_loaded_wrong_token(self):
        Utils.setup_encrypted_file()
        Database.set_meta("admin_token", "UHUHU-HUHU")
        with self.assertRaises(Forbidden):
            self.admin_handler.drop_contest("LALLA-BALALLA")

    def test_drop_contest_not_loaded_wrong_token(self):
        Utils.setup_encrypted_file()
        Database.del_meta("admin_token")
        with self.assertRaises(Forbidden):
            self.admin_handler.drop_contest("AAAAAA-CZKW-CCJS")

    def test_drop_contest_not_deletable(self):
        Utils.setup_encrypted_file()
        Database.del_meta("admin_token")
        with open(Config.encrypted_file, "wb") as f:
            yaml = ruamel.yaml.YAML(typ=["safe", "string"], pure=True)
            f.write(Utils.build_pack(yaml.dump_to_string({"deletable": False})))
        with self.assertRaises(Forbidden):
            self.admin_handler.drop_contest(Utils.ZIP_TOKEN)

    def test_drop_contest(self):
        Utils.setup_encrypted_file()
        Database.del_meta("admin_token")
        with open(Config.encrypted_file, "wb") as f:
            yaml = ruamel.yaml.YAML(typ=["safe", "string"], pure=True)
            f.write(Utils.build_pack(yaml.dump_to_string({"deletable": True})))
        self.admin_handler.drop_contest(Utils.ZIP_TOKEN)
        self.assertFalse(os.path.exists(Config.storedir))
        self.assertFalse(os.path.exists(Config.statementdir))
        self.assertFalse(os.path.exists(Config.contest_path))
        self.assertFalse(os.path.exists(Config.encrypted_file))
        self.assertFalse(os.path.exists(Config.decrypted_file))
        self.assertTrue(os.path.exists(Config.db))
