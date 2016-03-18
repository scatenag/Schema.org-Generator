#!/usr/bin/python3
"""
Application Server Controller of the |Model View Controller| |external_link|

Contains the classes for the

- Controller - Controls the flow of requests

- EZContext - Information from the request

- EZQuit - Stops the server


While under construction, `Schemas` can be stored on the browser using Local Storage

A valid Schema will be generated.
It can be validated on Google Developers |Structured Data Testing Tool| |external_link|
"""
# Refer to the Readme.txt file for © copyright information
from wsgiref import handlers, simple_server
from sys import argv
from urllib.error import URLError
from threading import Thread
from datetime import datetime
from model.schema import Hierarchy
from view.schema_view import SchemaView


# Controller class - WSGI
class Controller(handlers.CGIHandler):
    """
    The Controller class manages the flow of requests for Generating Schemas
    """

    # Class variable to maintain the 'restart' state
    Restart = False

    def __init__(self, port):
        """
        Constructor
        Get the Model tier: Hierarchy (from file or construct it from the Internet)
        Get the View tier: SchemaView
        Start the http demon
        """
        super().__init__()
        self.hierarchy = Hierarchy()    # the model
        self.view = SchemaView()        # the view

        # Initialize the server deamon
        self._httpd = simple_server.make_server('', port, self.run_this)
        print("Serving on port {0}...".format(port))

        # Start the server
        self._httpd.serve_forever()

    def _do_return(self, start_response, rc):
        """
        Returns the response to the client

        :type rc: list or str
        """
        start_response(self.status, self.headers)
        # rc can be a list or text
        if isinstance(rc, list):
            return rc  # favicon.ico

        # Use the default UTF-8 encoding
        return [rc.encode()]

    # This closes the server so the socket is liberated
    def server_close(self):
        """
        Class method closes the http demon
        """
        self._httpd.server_close()

    def run_this(self, environ, start_response):
        """
        Class method passed to the http demon

        Here is where all GET and POST get treated

        Here is where the Model is invoked

        Here is where the View is invoked

        :param environ: A |mapping| |external_link| object representing the string environment concerning the request

        :param start_response: Callable. Used to begin the HTTP response

        :return: Requested page.

        .. |mapping| raw:: html

            <a href="https://docs.python.org/3.5/glossary.html#term-mapping" target="_blank">mapping</a>
        """
        try:
            # Default status
            self.status = '200 OK'

            # Default header
            self.headers = [('Content-type', 'text/plain; charset=utf-8')]

            # Create a context from the environment
            ctx = EZContext(environ)

            # Get the path info - This is to redirect the flow
            # This is not in the ctx
            path_info = environ['PATH_INFO']
            if path_info in ['/quit', '/restart']:
                # Configure Apache to filter out these requests
                # localhost:port/quit or /restart can then be used
                if '/restart' == path_info:
                    self.Restart = True

                # The http demon will not stop from a call in this thread
                # Another thread is needed to stop the server
                q = EZQuit(self._httpd)
                q.start()

                # Returns a string to the browser
                # Path info starts with "/"
                rc = '{0}: {1}'.format(path_info[1:], datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            elif '.ico' in path_info or '.png' in path_info:
                # This code should be eliminated when used as a module with Apache
                with open('view{0}'.format(path_info), 'rb') as f:
                    txt = f.read()
                self.headers = [('Content-type', 'image/png'), ('Content-length', str(len(txt)))]
                rc = [txt]
            elif '/schema.js' == path_info:
                # This code should be eliminated when used as a module with Apache
                with open('view/schema.js') as f:
                    rc = f.read()
            else:
                # Return html
                self.headers = [('Content-type', 'text/html; charset=utf-8')]
                if '/' == path_info or '' == path_info:
                    # Returns the whole hierarchy - Similar to http://schema.org/docs/full.html
                    rc = self.view.get_index(self.hierarchy.hierarchy)
                elif '/SaveSchema' == path_info:
                    # The Schema has been saved in Local Storage
                    # Return a nice message
                    rc = self.view.get_saved_output()
                elif '/GenerateSchema' == path_info:
                    # Put it all together
                    # Output the Scheme the user has constructed
                    # Output a link to the Google Structured Data Testing Tool
                    rc = self.view.generate_schema_output(ctx.get('path'), ctx)
                elif ctx.get('next_element'):  # If the Action is POST
                    # AJAX call for the next level down from the top level Scheme the user is constructing
                    schema = self.hierarchy.get_schema(ctx.get('next_element'))
                    # The id of the container div - use for next level
                    rc = self.view.ajax_properties(schema, ctx.get('id'))
                else:  # Otherwise the action is GET - This is what happens first
                    # 1. Get the Hierarchy
                    # 2. next_element (or not) - get the AJAX properties of the next_element
                    # 3. GenerateSchema - Output the schema so it can be used by the user
                    try:
                        schema = self.hierarchy.get_schema(path_info[1:])  # Path info starts with "/"
                        rc = self.view.show_schema_properties(schema)
                    except URLError:
                        self.status = '300 Error'
                        self.headers = [('Content-type', 'text/plain; charset=utf-8')]
                        rc = 'Schema "{0}" not found'.format(path_info[1:])
        except Exception as err:
            # If something unexpected happens, return a reasonable message
            self.status = '300 Error'
            self.headers = [('Content-type', 'text/plain; charset=utf-8')]
            rc = err.args[0]

        # Finally, return the info to the browser
        return self._do_return(start_response, rc)

    # Unused CGIHandler abstract method
    def get_stdin(self):
        pass

    # Unused CGIHandler abstract method
    def _flush(self):
        pass

    # Unused CGIHandler abstract method
    def get_stderr(self):
        pass

    # Unused CGIHandler abstract method
    def add_cgi_vars(self):
        pass

    # Unused CGIHandler abstract method
    def _write(self, data):
        pass


class EZContext:
    """
    Class containing the information of the current request

    The information can be accessed through the get() method
    """

    def __init__(self, environ):
        self._QUERY_STRING = {}
        try:
            if 'GET' == environ['REQUEST_METHOD']:
                # If method == GET, but body, raise an error
                i = environ['CONTENT_LENGTH'].strip()
                if i:
                    if 0 < int(i):
                        raise (BaseException('Invalid method'))
                query_string = environ['QUERY_STRING']
            else:
                # If method == POST, but QUERY_STRING, raise an error
                if 0 < len(environ['QUERY_STRING']):
                    raise (BaseException('Invalid method'))

                # Get info from wsgi.input, in b'' convert into str
                body_size = int(environ['CONTENT_LENGTH'])
                query_string = environ['wsgi.input'].read(body_size).decode()

            qs = query_string.split('&')
            for q in qs:
                k, v = q.split('=')
                # Ignore empty values
                if len(v):
                    self._QUERY_STRING[k] = v
        except BaseException as rc:
            # There is no query_string
            self._QUERY_STRING = {}
            if str(rc) == 'Invalid method':
                raise (BaseException('Invalid method'))

    def get(self, key):
        """
        Class method to obtain the key from the:

         * QUERY_STRING: if it's a GET request

         * wsgi.input: if it's a POST request

         For security reasons, GET and POST methods cannot be used interchangeably.

        :param key:

        :return: value or empty string if key not found
        """
        try:
            return self._QUERY_STRING[key]
        except KeyError:
            return ''  # key not found

    @property
    def get_keys(self):
        """
        Class method to obtain **all** the keys

        :return: all keys
        """
        return self._QUERY_STRING.keys


class EZQuit(Thread):
    """
    Shuts down the http demon

    Nothing more, nothing less

    Must be an independent thread
    """

    def __init__(self, httpd):
        """
        Initialize the super class.
        """
        Thread.__init__(self)
        self._httpd = httpd

    def run(self):
        self._httpd.shutdown()


if __name__ == "__main__":
    from os import chdir

    print('Schema Controller - main')

    # Change the base dir to where this __file__ is located
    # Needed for testing
    FILE_NAME = 'controller.py'
    if __file__ != FILE_NAME:
        BASE_DIR = __file__[:__file__.index(FILE_NAME)]
        chdir(BASE_DIR)

    try:
        listen_port = 8000
        if len(argv) > 1:
            listen_port = int(argv[1])

        # This will setup the server and start the serve_forever() loop
        # This will block the script until the serve_forever() loop is interrupted
        # Either by localhost:8000/restart or localhost:8000/quit
        ez = Controller(listen_port)
        while ez.Restart:
            # This will close the server. If it's a restart, this will liberate the socket
            ez.server_close()
            ez = Controller(listen_port)
    except KeyboardInterrupt:
        # Silence KeyboardInterrupt exception
        pass
    except Exception as e:
        print(e)