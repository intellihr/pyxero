import json
from xml.dom.minidom import parseString

from six.moves.urllib.parse import parse_qs


class XeroException(Exception):
    def __init__(self, response, msg=None):
        self.response = response
        super(XeroException, self).__init__(msg)


class XeroNotVerified(Exception):
    # Credentials haven't been verified
    pass


class XeroBadRequest(XeroException):
    # HTTP 400: Bad Request
    def __init__(self, response):
        if response.headers['content-type'].startswith('application/json'):
            data = json.loads(response.text)

            msg = "%s: %s" % (data['Type'], data['Message'])

            self.errors = [err['Message']
                           for elem in data.get('Elements', [])
                           for err in elem.get('ValidationErrors', [])
                           ]

            if 'Type' in data and data['Type'] == 'ValidationException':
                if 'Message' in data and data['Message'] != 'A validation exception occurred':
                    self.errors.append(data['Message'])

                for key in data:
                    value = data[key]
                    if type(value).__name__ == 'list':
                        for item in value:
                            for err in item.get('ValidationErrors', []):
                                for message in err:
                                    validation_error = err[message]
                                    self.errors.append(validation_error)

                            for employee_field_key in item:
                                if employee_field_key == 'ValidationErrors':
                                    continue

                                employee_field = item[employee_field_key]

                                if type(employee_field).__name__ == 'dict':
                                    for err in employee_field.get('ValidationErrors', []):
                                        for message in err:
                                            validation_error = err[message]
                                            self.errors.append(validation_error)

                                if type(employee_field).__name__ == 'list':
                                    for attribute in employee_field:
                                        for err in attribute.get('ValidationErrors', []):
                                            for message in err:
                                                validation_error = err[message]
                                                self.errors.append(validation_error)

            super(XeroBadRequest, self).__init__(response, msg=msg)

        elif response.headers['content-type'].startswith('text/html'):
            print('Totally not an oauth problem')
            print(response.text)
            print(response.request.body)
            payload = parse_qs(response.text)
            self.errors = [payload['oauth_problem'][0]]
            self.problem = self.errors[0]
            super(XeroBadRequest, self).__init__(response, payload['oauth_problem_advice'][0])

        else:
            # Extract the messages from the text.
            # parseString takes byte content, not unicode.
            dom = parseString(response.text.encode(response.encoding))
            messages = dom.getElementsByTagName('Message')

            msg = messages[0].childNodes[0].data
            self.errors = [
                m.childNodes[0].data for m in messages[1:]
            ]
            self.problem = self.errors[0]
            super(XeroBadRequest, self).__init__(response, msg)


class XeroUnauthorized(XeroException):
    # HTTP 401: Unauthorized
    def __init__(self, response):
        payload = parse_qs(response.text)
        self.errors = [payload['oauth_problem'][0]]
        self.problem = self.errors[0]
        super(XeroUnauthorized, self).__init__(response, payload['oauth_problem_advice'][0])


class XeroForbidden(XeroException):
    # HTTP 403: Forbidden
    def __init__(self, response):
        super(XeroForbidden, self).__init__(response, response.text)


class XeroNotFound(XeroException):
    # HTTP 404: Not Found
    def __init__(self, response):
        super(XeroNotFound, self).__init__(response, response.text)

class XeroUnsupportedMediaType(XeroException):
    # HTTP 415: UnsupportedMediaType
    def __init__(self, response):
        super(XeroUnsupportedMediaType, self).__init__(response, response.text)

class XeroInternalError(XeroException):
    # HTTP 500: Internal Error
    def __init__(self, response):
        super(XeroInternalError, self).__init__(response, response.text)


class XeroNotImplemented(XeroException):
    # HTTP 501
    def __init__(self, response):
        # Extract the useful error message from the text.
        # parseString takes byte content, not unicode.
        dom = parseString(response.text.encode(response.encoding))
        messages = dom.getElementsByTagName('Message')

        msg = messages[0].childNodes[0].data
        super(XeroNotImplemented, self).__init__(response, msg)


class XeroRateLimitExceeded(XeroException):
    # HTTP 503 - Rate limit exceeded
    def __init__(self, response, payload):
        try:
            self.errors = [payload['oauth_problem'][0]]
        except KeyError:
            return super(XeroRateLimitExceeded, self).__init__(response, response.text)
        self.problem = self.errors[0]
        super(XeroRateLimitExceeded, self).__init__(response, payload['oauth_problem_advice'][0])


class XeroNotAvailable(XeroException):
    # HTTP 503 - Not available
    def __init__(self, response):
        super(XeroNotAvailable, self).__init__(response, response.text)


class XeroExceptionUnknown(XeroException):
    # Any other exception.
    pass
