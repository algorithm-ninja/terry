#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright 2017-2019 - Edoardo Morassutto <edoardo.morassutto@gmail.com>
# Copyright 2017 - Luca Versari <veluca93@gmail.com>
# Copyright 2018 - William Di Luigi <williamdiluigi@gmail.com>

import json
from datetime import datetime, timezone
from typing import NoReturn, Optional

from werkzeug.exceptions import HTTPException, BadRequest
from werkzeug.wrappers import Response

from ..handler_params import HandlerParams
from ..config import Config
from ..database import Database
from ..logger import Logger


class BaseHandler:
    @staticmethod
    def raise_exc(ecls, code, message) -> NoReturn:
        """
        Raise an HTTPException with a code and a message sent in a json like
         {
             "code": code
             "message": message
         }
        :param cls: HTTPException of the error, for example NotFound, BadRequest, NotAuthorized
        :param code: A brief message for the exception, like MISSING_PARAMETER
        :param message: A longer description of the error
        :return: Nothing, raise the provided exception with the correct response
        """
        response = Response()
        response.mimetype = "application/json"
        response.status_code = ecls.code
        response.data = json.dumps({"code": code, "message": message})
        Logger.warning(ecls.__name__.upper(), code + ": " + message)
        raise ecls(response=response)

    def handle(self, endpoint, route_args, request):
        """
        Handle a request in the derived handler. The request is routed to the correct method using *endpoint*
        :param endpoint: A string with the name of the class method to call with (route_args, request) as parameters,
        this method should return a Response or call self.raise_exc. *NOTE*: the method MUST be implemented in the
        derived class
        :param route_args: The route parameters, the parameters extracted from the matching route in the URL
        :param request: The Request object, request.args contains the query parameters of the request
        :return: Return a Response if the request is successful, an HTTPException if an error occurred
        """
        try:
            data = BaseHandler._call(
                self.__getattribute__(endpoint), route_args, request
            )
            response = Response()
            if data is not None:
                response.status_code = 200
                response.mimetype = "application/json"
                response.data = json.dumps(data)
            else:
                response.status_code = 204
            return response
        except HTTPException as e:
            return e

    def parse_body(self, request):
        """
        Parse the body part of the request in JSON
        :param request: The request to be parsed
        :return: A dict with the content of the body
        """
        return request.form

    @staticmethod
    def get_end_time(user_extra_time: Optional[int]):
        """
        Compute the end time for a user
        :param user_extra_time: Extra time specific for the user in seconds
        :return: The timestamp at which the contest will be finished for this user
        """
        start = Database.get_meta_float("start_time", None)
        if start is None:
            return None
        contest_duration = Database.get_meta_int("contest_duration", 0)
        contest_extra_time = Database.get_meta_int("extra_time", 0)
        if user_extra_time is None:
            user_extra_time = 0

        return start + contest_duration + contest_extra_time + user_extra_time

    @staticmethod
    def get_window_end_time(user_extra_time: Optional[int], start_delay: Optional[int]):
        """
        Compute the end time for a window started after `start_delay` and with `extra_time` delay for the user.
        Note that this time may exceed the contest end time, additional checks are required.
        :param user_extra_time: Extra time specific for the user in seconds
        :param start_delay: The time (in seconds) after the start of the contest of when the window started
        :return: The timestamp at which the window ends. If the contest has no window None is returned.
        """
        if start_delay is None:
            return None
        start = Database.get_meta_float("start_time", None)
        if start is None:
            return None
        window_duration = Database.get_meta_int("window_duration", None)
        if window_duration is None:
            return None
        if user_extra_time is None:
            user_extra_time = 0
        return start + user_extra_time + start_delay + window_duration

    @staticmethod
    def format_dates(dct, fields=["date"]):
        """
        Given a dict, format all the *fields* fields from int to iso format. The original dict is modified
        :param dct: dict to format
        :param fields: list of the names of the fields to format
        :return: The modified dict
        """
        for k, v in dct.items():
            if isinstance(v, dict):
                dct[k] = BaseHandler.format_dates(v, fields)
            elif isinstance(v, list):
                for item in v:
                    BaseHandler.format_dates(item, fields)
            elif k in fields and v is not None:
                dct[k] = datetime.fromtimestamp(v, timezone.utc).isoformat()
        return dct

    @staticmethod
    def _call(method, route_args, request):
        """
        This function is MAGIC!
        It takes a method, reads it's parameters and automagically fetch from the request the values. Type-annotation
        is also supported for a simple type validation.
        The values are fetched, in order, from:
        - route_args
        - request.form
        - general_attrs
        - default values
        If a parameter is required but not sent a BadRequest (MISSING_PARAMETERS) error is thrown, if a parameter cannot
        be converted to the annotated type a BadRequest (FORMAT_ERROR) is thrown.
        :param method: Method to be called
        :param route_args: Arguments of the route
        :param request: Request object
        :return: The return value of method
        """
        kwargs = {}
        params = HandlerParams.get_handler_params(method)
        general_attrs = {
            "_request": request,
            "_route_args": route_args,
            "_file": {
                "content": BaseHandler._get_file_content(request),
                "name": BaseHandler._get_file_name(request),
            },
            "_ip": BaseHandler.get_ip(request),
        }

        missing_parameters = []

        for name, data in params.items():
            if name in route_args and name[0] != "_":
                kwargs[name] = route_args[name]
            elif name in request.form and name[0] != "_":
                kwargs[name] = request.form[name]
            elif name in general_attrs:
                kwargs[name] = general_attrs[name]
            elif name == "file" and general_attrs["_file"]["name"] is not None:
                kwargs[name] = general_attrs["_file"]
            elif data["required"]:
                missing_parameters.append(name)

        if len(missing_parameters) > 0:
            BaseHandler.raise_exc(
                BadRequest,
                "MISSING_PARAMETERS",
                "The missing parameters are: " + ", ".join(missing_parameters),
            )

        for key, value in kwargs.items():
            type = params[key]["type"]
            if type is None:
                continue
            try:
                kwargs[key] = type(value)
            except ValueError:
                BaseHandler.raise_exc(
                    BadRequest,
                    "FORMAT_ERROR",
                    "The parameter %s cannot be converted to %s" % (key, type.__name__),
                )
        Logger.debug(
            "HTTP",
            "Received request from %s for endpoint %s%s"
            % (
                general_attrs["_ip"],
                method.__name__,
                ", with parameters "
                + ", ".join(
                    "=".join((kv[0], str(kv[1])))
                    for kv in kwargs.items()
                    if not kv[0].startswith("_") and not kv[0] == "file"
                )
                if len(kwargs) > 0
                else "",
            ),
        )
        return method(**kwargs)

    @staticmethod
    def _get_file_name(request):
        """
        Extract the name of the file from the multipart body
        :param request: The Request object
        :return: The filename in the request
        """
        if "file" not in request.files:
            return None
        return request.files["file"].filename

    @staticmethod
    def _get_file_content(request):
        """
        Extract the content of the file from the multipart of the body
        :param request: The Request object
        :return: A *bytes* with the content of the file
        """
        if "file" not in request.files:
            return None
        return request.files["file"].stream.read()

    @staticmethod
    def get_ip(request):
        """
        Return the real IP of the client
        :param request: The Request object
        :return: A string with the IP of the client
        """
        num_proxies = Config.num_proxies
        if num_proxies == 0 or len(request.access_route) < num_proxies:
            return request.remote_addr
        return request.access_route[-num_proxies]
