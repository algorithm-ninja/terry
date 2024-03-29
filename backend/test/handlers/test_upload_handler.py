#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright 2017-2018 - Edoardo Morassutto <edoardo.morassutto@gmail.com>
# Copyright 2017 - Massimo Cairo <cairomassimo@gmail.com>
import os
import unittest
from unittest.mock import patch
from hashlib import sha256

from werkzeug.exceptions import Forbidden, BadRequest, InternalServerError

from terry.config import Config
from terry.database import Database
from terry.handlers.upload_handler import UploadHandler
from terry.contest_manager import ContestManager
from terry.logger import Logger
from test.utils import Utils


class TestInfoHandler(unittest.TestCase):
    def setUp(self):
        Utils.prepare_test()
        self.handler = UploadHandler()

        self.log_backup = Logger.LOG_LEVEL
        Logger.LOG_LEVEL = 9001  # disable the logs

    def tearDown(self):
        Logger.LOG_LEVEL = self.log_backup

    @patch(
        "terry.contest_manager.ContestManager.evaluate_output",
        return_value=b'{"validation":42}',
    )
    @patch("terry.database.Database.gen_id", return_value="outputid")
    def test_upload_output(self, gen_mock, eval_mock):
        Utils.start_contest()
        self._insert_data()

        res = self.handler.upload_output(
            input_id="inputid",
            _ip="1.1.1.1",
            file={"content": "foobar".encode(), "name": "output.txt"},
        )
        self.assertEqual("outputid", res["id"])
        self.assertIn("output.txt", res["path"])
        self.assertEqual(42, res["validation"])
        self.assertEqual("inputid", res["input"])
        self.assertEqual(6, res["size"])
        path = os.path.join(Config.storedir, res["path"])
        with open(path, "r") as file:
            self.assertEqual("foobar", file.read())

    def test_upload_output_invalid_input(self):
        Utils.start_contest()
        with self.assertRaises(Forbidden) as ex:
            self.handler.upload_output(
                input_id="invalid input",
                _ip="1.1.1.1",
                _file_content="foo",
                _file_name="bar",
            )

        self.assertIn("No such input", ex.exception.response.data.decode())

    @patch("terry.database.Database.gen_id")
    def test_upload_output_invalid_file_name(self, gen_mock):
        Utils.start_contest()
        self._insert_data()

        with self.assertRaises(BadRequest):
            self.handler.upload_output(
                input_id="inputid",
                _ip="1.1.1.1",
                file={"content": "foobar".encode(), "name": ".."},
            )

    @patch(
        "terry.contest_manager.ContestManager.evaluate_output",
        side_effect=RuntimeError(),
    )
    @patch("terry.database.Database.gen_id", return_value="outputid")
    def test_upload_output_check_failed(self, gen_mock, eval_mock):
        Utils.start_contest()
        self._insert_data()

        with self.assertRaises(InternalServerError):
            self.handler.upload_output(
                input_id="inputid",
                _ip="1.1.1.1",
                file={"content": "foobar".encode(), "name": "output.txt"},
            )

    @patch("terry.database.Database.gen_id", return_value="sourceid")
    def test_upload_source(self, gen_mock):
        Utils.start_contest()
        self._insert_data()

        res = self.handler.upload_source(
            input_id="inputid",
            _ip="1.1.1.1",
            file={"content": "foobar".encode(), "name": "source.txt"},
        )
        self.assertEqual("sourceid", res["id"])
        self.assertIn("source.txt", res["path"])
        self.assertEqual("inputid", res["input"])
        self.assertEqual(6, res["size"])
        alerts = res["validation"]["alerts"]
        self.assertEqual(1, len(alerts))
        self.assertEqual("success", alerts[0]["severity"])
        message = alerts[0]["message"]
        self.assertTrue(isinstance(message, str) and len(message) > 0)
        path = os.path.join(Config.storedir, res["path"])
        with open(path, "r") as file:
            self.assertEqual("foobar", file.read())

    @patch("terry.database.Database.gen_id", return_value="sourceid")
    def test_upload_source_with_exe(self, gen_mock):
        Utils.start_contest()
        self._insert_data()
        executable = b"\x4D\x5Adeadbaba"

        res = self.handler.upload_source(
            input_id="inputid",
            _ip="1.1.1.1",
            file={"content": executable, "name": "lol.exe"},
        )
        alerts = res["validation"]["alerts"]
        self.assertEqual(1, len(alerts))
        self.assertIn("executable", alerts[0]["message"])
        self.assertEqual("warning", alerts[0]["severity"])

    def test_upload_source_invalid_input(self):
        Utils.start_contest()
        with self.assertRaises(Forbidden) as ex:
            self.handler.upload_source(
                input_id="invalid input",
                _ip="1.1.1.1",
                _file_content="foo",
                _file_name="bar",
            )

        self.assertIn("No such input", ex.exception.response.data.decode())

    @patch("terry.database.Database.gen_id")
    def test_upload_source_invalid_file_name(self, gen_mock):
        Utils.start_contest()
        self._insert_data()

        with self.assertRaises(BadRequest):
            self.handler.upload_source(
                input_id="inputid",
                _ip="1.1.1.1",
                file={"content": "foobar".encode(), "name": ".."},
            )

    @patch("terry.database.Database.gen_id", return_value="sourceid")
    def test_upload_source_template_file(self, gen_mock):
        Utils.start_contest()
        self._insert_data()

        old_statement_hashes = ContestManager.statement_file_hashes
        ContestManager.statement_file_hashes.add(sha256(b"file contents").digest())

        res = self.handler.upload_source(
            input_id="inputid",
            _ip="1.1.1.1",
            file={"content": b"file contents", "name": "source.cpp"},
        )

        expected = {'severity': 'warning', 'message': 'You have submitted a template file! Please send the source code.'}
        self.assertTrue(expected in res['validation']['alerts'])

        ContestManager.statement_file_hashes = old_statement_hashes


    def _insert_data(self):
        Database.add_user("token", "", "")
        Database.add_task("poldo", "", "", 42, 1)
        Database.add_user_task("token", "poldo")
        Database.add_input("inputid", "token", "poldo", 1, "/path", 42)
