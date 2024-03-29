#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright 2017-2019 - Edoardo Morassutto <edoardo.morassutto@gmail.com>
# Copyright 2018 - William Di Luigi <williamdiluigi@gmail.com>
import _io
from datetime import datetime, timezone
import json
import unittest
from unittest.mock import patch

from gevent.pywsgi import Environ
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import Forbidden, BadRequest
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from terry.config import Config
from terry.database import Database
from terry.handlers.base_handler import BaseHandler
from terry.logger import Logger
from terry.validators import Validators
from test.utils import Utils


class TestBaseHandler(unittest.TestCase):
    def setUp(self):
        Utils.prepare_test()
        self.handler = BaseHandler()

        self.log_backup = Logger.LOG_LEVEL
        Logger.LOG_LEVEL = -9001  # enable the logs
        Logger.disable_console_logging = True  # .. but not to console

    def tearDown(self):
        Logger.LOG_LEVEL = self.log_backup

    def test_raise_exc(self):
        with self.assertRaises(Forbidden) as ex:
            self.handler.raise_exc(Forbidden, "EX_CODE", "Ex message")

        response = ex.exception.response
        self.assertEqual("application/json", response.mimetype)
        data = json.loads(response.data.decode())
        self.assertEqual("EX_CODE", data["code"])
        self.assertEqual("Ex message", data["message"])

    class DummyHandler(BaseHandler):
        def dummy_endpoint(self, param: int = 123):
            return {"incremented": param + 1}

        def required(self, param):
            self.raise_exc(Forbidden, "NOBUONO", "nononono")

        def myip(self, _ip):
            return _ip

        def file(self, file):
            return file["name"]

        @Validators.validate_input_id
        @Validators.validate_output_id
        def with_decorators(self, input, output):
            pass

    @patch("terry.handlers.base_handler.BaseHandler._call", return_value={"foo": "bar"})
    def test_handle(self, call_mock):
        handler = TestBaseHandler.DummyHandler()
        response = handler.handle("dummy_endpoint", 42, 123)
        endpoint = handler.dummy_endpoint

        call_mock.assert_called_once_with(endpoint, 42, 123)
        self.assertEqual(200, response.status_code)
        self.assertEqual("application/json", response.mimetype)
        self.assertDictEqual({"foo": "bar"}, json.loads(response.data.decode()))

    @patch("terry.handlers.base_handler.BaseHandler._call", return_value=None)
    def test_handle_no_content(self, call_mock):
        handler = TestBaseHandler.DummyHandler()
        response = handler.handle("dummy_endpoint", 42, 123)
        self.assertEqual(204, response.status_code)

    @patch("terry.handlers.base_handler.BaseHandler._call", side_effect=Forbidden())
    def test_handle_exceptions(self, call_mock):
        handler = TestBaseHandler.DummyHandler()
        response = handler.handle("dummy_endpoint", 42, 123)
        self.assertIsInstance(response, Forbidden)

    def test_parse_body(self):
        request = Request({})
        request.form = {"foo": "bar"}

        body = self.handler.parse_body(request)
        self.assertEqual("bar", body["foo"])

    def test_end_time(self):
        Database.set_meta("start_time", 1000)
        Database.set_meta("contest_duration", 150)
        Database.set_meta("extra_time", 20)

        self.assertEqual(BaseHandler.get_end_time(20), 1190)
        self.assertEqual(BaseHandler.get_end_time(0), 1170)

    def test_end_time_not_started(self):
        self.assertIsNone(BaseHandler.get_end_time(0))

    def test_window_end_time(self):
        Database.set_meta("start_time", 1000)
        Database.set_meta("contest_duration", 150)
        Database.set_meta("window_duration", 100)
        Database.set_meta("extra_time", 20)

        self.assertEqual(BaseHandler.get_window_end_time(10, 20), 1130)
        self.assertEqual(BaseHandler.get_window_end_time(0, 0), 1100)

    def test_window_end_time_no_window(self):
        Database.set_meta("start_time", 1000)
        Database.set_meta("contest_duration", 150)
        # Database.set_meta("window_duration", nope)
        Database.set_meta("extra_time", 20)

        self.assertEqual(BaseHandler.get_window_end_time(20, 42), None)

    def test_format_dates(self):
        dct = {
            "date": 12345678,
            "nondate": 12345678,
            "we": {"need": {"to": {"go": {"deeper": 1010101010}}}},
        }
        formatted = BaseHandler.format_dates(dct, fields=["date", "deeper"])
        self.assertEqual(
            datetime.fromtimestamp(12345678, timezone.utc).isoformat(),
            formatted["date"],
        )
        self.assertEqual(12345678, formatted["nondate"])
        self.assertEqual(
            datetime.fromtimestamp(1010101010, timezone.utc).isoformat(),
            formatted["we"]["need"]["to"]["go"]["deeper"],
        )

    @patch("terry.handlers.base_handler.BaseHandler.get_ip", return_value="1.2.3.4")
    @patch("terry.handlers.base_handler.BaseHandler._get_file_content", return_value=42)
    @patch("terry.handlers.base_handler.BaseHandler._get_file_name", return_value=42)
    def test_call(self, name_mock, content_mock, ip_mock):
        handler = TestBaseHandler.DummyHandler()
        env = Environ({"wsgi.input": None})
        request = Request(env)
        request.form = {"param": 42}

        res = handler._call(handler.dummy_endpoint, {}, request)
        self.assertEqual(43, res["incremented"])

        Logger.c.execute("SELECT * FROM logs WHERE category = 'HTTP'")
        row = Logger.c.fetchone()
        self.assertIn("1.2.3.4", row[3])
        self.assertIn("dummy_endpoint", row[3])

    @patch("terry.handlers.base_handler.BaseHandler.get_ip", return_value=42)
    @patch("terry.handlers.base_handler.BaseHandler._get_file_content", return_value=42)
    @patch("terry.handlers.base_handler.BaseHandler._get_file_name", return_value=42)
    def test_call_default(self, name_mock, content_mock, ip_mock):
        handler = TestBaseHandler.DummyHandler()
        env = Environ({"wsgi.input": None})
        request = Request(env)

        res = handler._call(handler.dummy_endpoint, {}, request)
        self.assertEqual(124, res["incremented"])

    @patch("terry.handlers.base_handler.BaseHandler.get_ip", return_value=42)
    @patch("terry.handlers.base_handler.BaseHandler._get_file_content", return_value=42)
    @patch("terry.handlers.base_handler.BaseHandler._get_file_name", return_value=42)
    def test_call_cast_parameter(self, name_mock, content_mock, ip_mock):
        handler = TestBaseHandler.DummyHandler()
        env = Environ({"wsgi.input": None})
        request = Request(env)
        request.form = {"param": "42"}

        res = handler._call(handler.dummy_endpoint, {}, request)
        self.assertEqual(43, res["incremented"])

    @patch("terry.handlers.base_handler.BaseHandler.get_ip", return_value=42)
    @patch("terry.handlers.base_handler.BaseHandler._get_file_content", return_value=42)
    @patch("terry.handlers.base_handler.BaseHandler._get_file_name", return_value=42)
    def test_call_fail_cast_parameter(self, name_mock, content_mock, ip_mock):
        handler = TestBaseHandler.DummyHandler()
        env = Environ({"wsgi.input": None})
        request = Request(env)
        request.form = {"param": "nope"}

        with self.assertRaises(BadRequest):
            handler._call(handler.dummy_endpoint, {}, request)

    @patch("terry.handlers.base_handler.BaseHandler.get_ip", return_value=42)
    @patch("terry.handlers.base_handler.BaseHandler._get_file_content", return_value=42)
    @patch("terry.handlers.base_handler.BaseHandler._get_file_name", return_value=42)
    def test_call_route_args(self, name_mock, content_mock, ip_mock):
        handler = TestBaseHandler.DummyHandler()
        env = Environ({"wsgi.input": None})
        request = Request(env)

        res = handler._call(handler.dummy_endpoint, {"param": "42"}, request)
        self.assertEqual(43, res["incremented"])

    @patch("terry.handlers.base_handler.BaseHandler.get_ip", return_value=42)
    @patch("terry.handlers.base_handler.BaseHandler._get_file_content", return_value=42)
    @patch("terry.handlers.base_handler.BaseHandler._get_file_name", return_value=42)
    def test_call_required_args(self, name_mock, content_mock, ip_mock):
        handler = TestBaseHandler.DummyHandler()
        env = Environ({"wsgi.input": None})
        request = Request(env)

        with self.assertRaises(BadRequest) as ex:
            handler._call(handler.required, {}, request)

        response = ex.exception.response
        self.assertIn("MISSING_PARAMETER", response.data.decode())
        self.assertIn("param", response.data.decode())

    @patch("terry.handlers.base_handler.BaseHandler.get_ip", return_value=42)
    @patch("terry.handlers.base_handler.BaseHandler._get_file_content", return_value=42)
    @patch("terry.handlers.base_handler.BaseHandler._get_file_name", return_value=42)
    def test_call_with_error(self, name_mock, content_mock, ip_mock):
        handler = TestBaseHandler.DummyHandler()
        env = Environ({"wsgi.input": None})
        request = Request(env)

        with self.assertRaises(Forbidden) as ex:
            handler._call(handler.required, {"param": 42}, request)

        response = ex.exception.response
        self.assertIn("NOBUONO", response.data.decode())
        self.assertIn("nononono", response.data.decode())

    @patch("terry.handlers.base_handler.BaseHandler.get_ip", return_value="1.2.3.4")
    @patch("terry.handlers.base_handler.BaseHandler._get_file_content", return_value=42)
    @patch("terry.handlers.base_handler.BaseHandler._get_file_name", return_value=42)
    def test_call_general_attrs(self, name_mock, content_mock, ip_mock):
        handler = TestBaseHandler.DummyHandler()
        env = Environ({"wsgi.input": None})
        request = Request(env)

        res = handler._call(handler.myip, {}, request)
        self.assertEqual("1.2.3.4", res)

    def test_call_file(self):
        handler = TestBaseHandler.DummyHandler()
        env = Environ({"wsgi.input": None})
        request = Request(env)
        request.files = {"file": FileStorage(filename="foo")}

        res = handler._call(handler.file, {}, request)
        self.assertEqual("foo", res)

    def test_call_with_decorators(self):
        handler = TestBaseHandler.DummyHandler()
        env = Environ({"wsgi.input": None})
        request = Request(env)
        Database.add_user("token", "", "")
        Database.add_task("poldo", "", "", 1, 1)
        Database.add_input("inputid", "token", "poldo", 1, "", 42)
        Database.add_output("outputid", "inputid", "", 42, "")

        handler._call(
            handler.with_decorators,
            {"input_id": "inputid", "output_id": "outputid"},
            request,
        )

    def test_get_file_name(self):
        request = Request(Environ())
        request.files = {"file": FileStorage(filename="foo")}

        self.assertEqual("foo", BaseHandler._get_file_name(request))

    def test_get_file_name_no_file(self):
        request = Request(Environ())
        request.files = {}

        self.assertIsNone(BaseHandler._get_file_name(request))

    def test_get_file_content(self):
        request = Request(Environ())
        stream = _io.BytesIO("hello world".encode())
        request.files = {"file": FileStorage(stream=stream, filename="foo")}

        self.assertEqual("hello world", BaseHandler._get_file_content(request).decode())

    def test_get_file_content_no_file(self):
        request = Request(Environ())
        request.files = {}

        self.assertIsNone(BaseHandler._get_file_content(request))

    def test_get_ip_no_proxies(self):
        Config.num_proxies = 0
        request = Request(Environ(REMOTE_ADDR="1.2.3.4"))

        ip = BaseHandler.get_ip(request)
        self.assertEqual("1.2.3.4", ip)

    def test_get_ip_3_proxies(self):
        Config.num_proxies = 3
        headers = {"X-Forwarded-For": "1.2.3.4, 5.6.7.8, 8.8.8.8"}
        env = EnvironBuilder(headers=headers).get_environ()
        env["REMOTE_ADDR"] = "6.6.6.6"
        request = Request(env)

        ip = BaseHandler.get_ip(request)
        self.assertEqual("1.2.3.4", ip)
