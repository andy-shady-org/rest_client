# coding: utf-8
"""
Author: Andy Wilson
Email:  andy@shady.org

| Description: Python REST Client
| Function: To facilitate connections to HTTPS REST API using API token
"""

import six
import json
import logging
import requests
import requests.auth
import requests.adapters
import requests.packages
from requests.packages import urllib3
import requests.exceptions
import timeit
from .errors import ClientError


if six.PY3:
    long = int
    unicode = str
    basestring = str

try:
    #############################################################################
    # Disable "InsecureRequestWarning: Unverified HTTPS request is being made."
    # noinspection PyUnresolvedReferences,PyUnresolvedReferences
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    #############################################################################
except (ImportError, AttributeError):
    InsecureRequestWarning = None

try:
    from urllib import quote
except (ImportError, AttributeError):
    from urllib.parse import quote


class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r


class Client(object):
    """
    Connection class that simplifies and unifies all access to HTTPS API.
    """
    def __init__(self, server, api_token, port=443, ssl_check=False, verbose=False, simulation=False):
        """
        Standard constructor.

        :param server: server hostname or IP from which to craft endpoint
        :param api_token: API token
        :param port: Server Port
        :param ssl_check: whether to perform SSL validation or not
        :param verbose: enable debugging (1 for INFO, 2 for DEBUG)
        :param simulation: enable simulation of call for testing
        """
        self.session = requests.Session()
        self._reply = None
        self._error = None
        self._error_code = None
        self._record = None
        self._params = None

        logging.basicConfig(level=logging.ERROR)
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.ERROR)
        self.debug = verbose if verbose else 0
        if self.debug is True:
            self.logger.setLevel(logging.WARNING)
            self.logger.warning('Setting level to WARNING')
        if self.debug == 2:
            self.logger.setLevel(logging.INFO)
            self.logger.info('Setting level to INFO')
        elif self.debug > 2:
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug('Setting level to DEBUG')

        self.server = server
        self.token = api_token
        self.use_ssl = True if ssl_check is True else False
        self.simulation = simulation

        # set up HTTP/S session
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=5, pool_connections=5, pool_maxsize=10)
        self.session.mount('https://', adapter)
        self.headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

        self.session.verify = False
        if self.use_ssl is True:
            self.session.verify = True

        # prepare the URL
        self.url = 'https://{0}:{1}'.format(server, port)
        self.session.auth = BearerAuth(self.token)
        self.logger.debug('Infoblox Load Complete, loglevel set to %s', logging.getLevelName(self.logger.getEffectiveLevel()))

    def __del__(self):
        """
        Class destructor.
        The destructor mainly takes care of "gracefully" terminating the session towards HTTP Server.
        """
        if self.session:
            self.session.close()
            self.session = None

    def __getattr__(self, item):
        """
        Overload of getattr method to handle HTTP method calls
        This would result in HTTP URL crafted '/devices/4?src=123&dst=321':

        .. code-block:: python
            client.get('/devices' '4', src='123', dst='321')

        This would result in HTTP URL crafted '/devices/4' and a payload body:

        .. code-block:: python
            client.post('/devices' '4', payload=dict(src='123', dst='321'))

        :param item: a self method
        :return: a wrapped query function or None
        """
        opname = item.split('_')

        def func(*args, **kwargs):
            fragments = None
            if isinstance(args, (list, tuple)):
                fragments = [x for x in opname[1:] if x]
                fragments.extend([x for x in args if x])
            elif isinstance(args, str):
                fragments = [args]

            if not fragments:
                return self.query('', opname[0], **kwargs)

            return self.query('/'.join(fragments), opname[0], **kwargs)

        if opname[0] in ['get', 'post', 'put', 'delete', 'patch']:
            return func
        return None

    def timeit(self, method, *args, **kwargs):
        """
        Method for testing timing of request

        :param method:
        :return: cnt
        :rtype: float|int
        """
        tic = timeit.default_timer()
        m = getattr(self, method)
        res = m(*args, **kwargs)
        self.logger.debug(res)
        toc = timeit.default_timer()
        cnt = toc - tic  # elapsed time in seconds
        return cnt

    @property
    def error_msg(self):
        """ Method for storing and returning error messages """
        return self._error

    @property
    def error_code(self):
        return self._error_code

    @property
    def reply_msg(self):
        """ Method for storing and returning reply messages """
        return self._reply

    def _login(self):
        if not self.session:
            self.session = requests.Session()
        self.session.auth = BearerAuth(self.token)

    def _parse_error(self, response):
        self.logger.debug('Parsing error response and raising exception')
        self._error = response.text
        self._error_code = response.status_code
        raise ClientError(self.__class__.__name__, self.error_code, self.error_msg)

    def _parse_response(self, response):
        if 200 <= response.status_code <= 299:
            reply = dict(status_code=response.status_code, data=response.json())
            return reply
        else:
            self.logger.debug('Response is not good, parsing error...')
            return self._parse_error(response)

    def query(self, resource, method='get', payload='', **kwargs):
        """
        Wrapper method to join all the REST stuff in a single place.

        .. note::
            self._reply holds the response of a successful API call.
            self._error holds the error message of a failed API call.

        :param resource: string containing the endpoint name. Eg. ``/v3/some-call/get_them_all``
        :type resource: str
        :param method: string containing either 'get', 'post', 'put' or 'delete'. Defaults to 'get'.
        :type method: str
        :param payload: Python dictionary that gets send as a json string.
        :type payload: dict
        :return: Result dictionary on success; False on error.
        :rtype: dict
        """
        method = method.strip().lower()
        resource = resource.strip()
        self._error = None

        http_verbs = ['get', 'post', 'put', 'delete', 'patch']
        if method not in http_verbs:
            method = 'get'

        if kwargs and method not in ['post', 'put', 'patch']:
            query = '&'.join({quote(x) + '=' + quote(str(kwargs.get(x))) for x in kwargs})
            self.logger.debug('Query: %s', query)
            resource = resource + '?' + query
        elif kwargs and method in ['post', 'put', 'patch'] and not payload:
            payload = kwargs

        if resource:
            resource = resource.strip() if resource.strip()[0] != '/' else resource.strip()[1:]
            url = self.url + ('/' if resource[0] != '?' else '') + resource
        else:
            url = self.url

        self.logger.info('Final URL: %s, Method: %s', url, method)
        if payload and payload is not None:
            self.logger.debug('Payload: %s', payload)

        if self.simulation:
            return dict(status_code=200, data=payload, ok=1)

        attempts = 0
        while attempts < 2:
            try:
                if method == 'get':
                    self._reply = self.session.get(url, verify=self.use_ssl, timeout=(10.0, 120))
                elif method == 'post':
                    self._reply = self.session.post(url, verify=self.use_ssl, data=json.dumps(payload), headers=self.headers, timeout=(10.0, 30))
                elif method == 'put':
                    self._reply = self.session.put(url, verify=self.use_ssl, data=json.dumps(payload), headers=self.headers, timeout=(10.0, 30))
                elif method == 'patch':
                    self._reply = self.session.patch(url, verify=self.use_ssl, data=json.dumps(payload), headers=self.headers, timeout=(10.0, 30))
                elif method == 'delete':
                    self._reply = self.session.delete(url, verify=self.use_ssl, timeout=(10.0, 30))
            except (requests.ConnectionError, requests.exceptions.SSLError, requests.exceptions.Timeout, requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout) as e:
                error = "HTTP Server Error: {0} - {1}".format(e, url)
                if e.response and e.response.status_code:
                    raise ClientError(self.__class__.__name__, e.response.status_code, error)
                else:
                    raise ClientError(self.__class__.__name__, 503, error)
            except requests.exceptions.HTTPError as exp:
                if exp.response.status_code == 403 and attempts < 5:
                    attempts += 1  # Try again because session timed out
            break  # Do not try again

        reauth = 0
        while reauth <= 2:
            if 401 == self._reply.status_code and 'login' not in resource.split('/')[-1]:
                self.logger.debug('Attempting Re-Auth: %s attempt', reauth)
                self._login()
                reauth += 1
                return self.query(resource, method, payload, **kwargs)
            break
        # Validate response
        if self._reply:
            return self._parse_response(self._reply)
        else:
            self._error = "HTTP Server Error: %s" % self._reply.text
            self._error_code = self._reply.status_code
            raise ClientError(self.__class__.__name__, self.error_code, self.error_msg)
