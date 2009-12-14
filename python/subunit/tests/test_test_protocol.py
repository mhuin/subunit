#
#  subunit: extensions to Python unittest to get test results from subprocesses.
#  Copyright (C) 2005  Robert Collins <robertc@robertcollins.net>
#
#  Licensed under either the Apache License, Version 2.0 or the BSD 3-clause
#  license at the users choice. A copy of both licenses are available in the
#  project source as Apache-2.0 and BSD. You may not use this file except in
#  compliance with one of these two licences.
#  
#  Unless required by applicable law or agreed to in writing, software
#  distributed under these licenses is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
#  license you chose for the specific language governing permissions and
#  limitations under that license.
#

import datetime
import unittest
from StringIO import StringIO
import os
import subunit
import sys

import subunit.iso8601 as iso8601


class MockTestProtocolServerClient(object):
    """A mock protocol server client to test callbacks.
    
    Note that this is deliberately not Python 2.7 complete, to allow
    testing compatibility - we need a TestResult that will not have new methods
    like addExpectedFailure.
    """

    def __init__(self):
        self.end_calls = []
        self.error_calls = []
        self.failure_calls = []
        self.skip_calls = []
        self.start_calls = []
        self.success_calls = []
        self.progress_calls = []
        self._time = None
        super(MockTestProtocolServerClient, self).__init__()

    def addError(self, test, error):
        self.error_calls.append((test, error))

    def addFailure(self, test, error):
        self.failure_calls.append((test, error))

    def addSkip(self, test, reason):
        self.skip_calls.append((test, reason))

    def addSuccess(self, test):
        self.success_calls.append(test)

    def stopTest(self, test):
        self.end_calls.append(test)

    def startTest(self, test):
        self.start_calls.append(test)

    def progress(self, offset, whence):
        self.progress_calls.append((offset, whence))

    def time(self, time):
        self._time = time


class MockExtendedTestProtocolServerClient(MockTestProtocolServerClient):
    """An extended TestResult for testing which implements tags() etc."""

    def __init__(self):
        MockTestProtocolServerClient.__init__(self)
        self.new_tags = set()
        self.gone_tags = set()

    def tags(self, new_tags, gone_tags):
        self.new_tags = new_tags
        self.gone_tags = gone_tags


class TestMockTestProtocolServer(unittest.TestCase):

    def test_start_test(self):
        protocol = MockTestProtocolServerClient()
        protocol.startTest(subunit.RemotedTestCase("test old mcdonald"))
        self.assertEqual(protocol.start_calls,
                         [subunit.RemotedTestCase("test old mcdonald")])
        self.assertEqual(protocol.end_calls, [])
        self.assertEqual(protocol.error_calls, [])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.success_calls, [])

    def test_add_error(self):
        protocol = MockTestProtocolServerClient()
        protocol.addError(subunit.RemotedTestCase("old mcdonald"),
                          subunit.RemoteError("omg it works"))
        self.assertEqual(protocol.start_calls, [])
        self.assertEqual(protocol.end_calls, [])
        self.assertEqual(protocol.error_calls, [(
                            subunit.RemotedTestCase("old mcdonald"),
                            subunit.RemoteError("omg it works"))])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.success_calls, [])

    def test_add_failure(self):
        protocol = MockTestProtocolServerClient()
        protocol.addFailure(subunit.RemotedTestCase("old mcdonald"),
                            subunit.RemoteError("omg it works"))
        self.assertEqual(protocol.start_calls, [])
        self.assertEqual(protocol.end_calls, [])
        self.assertEqual(protocol.error_calls, [])
        self.assertEqual(protocol.failure_calls, [
                            (subunit.RemotedTestCase("old mcdonald"),
                             subunit.RemoteError("omg it works"))])
        self.assertEqual(protocol.success_calls, [])

    def test_add_success(self):
        protocol = MockTestProtocolServerClient()
        protocol.addSuccess(subunit.RemotedTestCase("test old mcdonald"))
        self.assertEqual(protocol.start_calls, [])
        self.assertEqual(protocol.end_calls, [])
        self.assertEqual(protocol.error_calls, [])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.success_calls,
                         [subunit.RemotedTestCase("test old mcdonald")])

    def test_end_test(self):
        protocol = MockTestProtocolServerClient()
        protocol.stopTest(subunit.RemotedTestCase("test old mcdonald"))
        self.assertEqual(protocol.end_calls,
                         [subunit.RemotedTestCase("test old mcdonald")])
        self.assertEqual(protocol.error_calls, [])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.success_calls, [])
        self.assertEqual(protocol.start_calls, [])

    def test_progress(self):
        protocol = MockTestProtocolServerClient()
        protocol.progress(-1, subunit.PROGRESS_CUR)
        self.assertEqual(protocol.progress_calls, [(-1, subunit.PROGRESS_CUR)])


class TestTestImports(unittest.TestCase):

    def test_imports(self):
        from subunit import DiscardStream
        from subunit import TestProtocolServer
        from subunit import RemotedTestCase
        from subunit import RemoteError
        from subunit import ExecTestCase
        from subunit import IsolatedTestCase
        from subunit import TestProtocolClient
        from subunit import ProtocolTestCase


class TestDiscardStream(unittest.TestCase):

    def test_write(self):
        subunit.DiscardStream().write("content")


class TestProtocolServerForward(unittest.TestCase):

    def test_story(self):
        client = unittest.TestResult()
        out = StringIO()
        protocol = subunit.TestProtocolServer(client, forward_stream=out)
        pipe = StringIO("test old mcdonald\n"
                        "success old mcdonald\n")
        protocol.readFrom(pipe)
        mcdonald = subunit.RemotedTestCase("old mcdonald")
        self.assertEqual(client.testsRun, 1)
        self.assertEqual(pipe.getvalue(), out.getvalue())

    def test_not_command(self):
        client = unittest.TestResult()
        out = StringIO()
        protocol = subunit.TestProtocolServer(client,
            stream=subunit.DiscardStream(), forward_stream=out)
        pipe = StringIO("success old mcdonald\n")
        protocol.readFrom(pipe)
        self.assertEqual(client.testsRun, 0)
        self.assertEqual("", out.getvalue())
        

class TestTestProtocolServerPipe(unittest.TestCase):

    def test_story(self):
        client = unittest.TestResult()
        protocol = subunit.TestProtocolServer(client)
        pipe = StringIO("test old mcdonald\n"
                        "success old mcdonald\n"
                        "test bing crosby\n"
                        "failure bing crosby [\n"
                        "foo.c:53:ERROR invalid state\n"
                        "]\n"
                        "test an error\n"
                        "error an error\n")
        protocol.readFrom(pipe)
        mcdonald = subunit.RemotedTestCase("old mcdonald")
        bing = subunit.RemotedTestCase("bing crosby")
        an_error = subunit.RemotedTestCase("an error")
        self.assertEqual(client.errors,
                         [(an_error, 'RemoteException: \n\n')])
        self.assertEqual(
            client.failures,
            [(bing, "RemoteException: foo.c:53:ERROR invalid state\n\n")])
        self.assertEqual(client.testsRun, 3)


class TestTestProtocolServerStartTest(unittest.TestCase):

    def setUp(self):
        self.client = MockTestProtocolServerClient()
        self.protocol = subunit.TestProtocolServer(self.client)

    def test_start_test(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.assertEqual(self.client.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])

    def test_start_testing(self):
        self.protocol.lineReceived("testing old mcdonald\n")
        self.assertEqual(self.client.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])

    def test_start_test_colon(self):
        self.protocol.lineReceived("test: old mcdonald\n")
        self.assertEqual(self.client.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])

    def test_start_testing_colon(self):
        self.protocol.lineReceived("testing: old mcdonald\n")
        self.assertEqual(self.client.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])


class TestTestProtocolServerPassThrough(unittest.TestCase):

    def setUp(self):
        self.stdout = StringIO()
        self.test = subunit.RemotedTestCase("old mcdonald")
        self.client = MockTestProtocolServerClient()
        self.protocol = subunit.TestProtocolServer(self.client, self.stdout)

    def keywords_before_test(self):
        self.protocol.lineReceived("failure a\n")
        self.protocol.lineReceived("failure: a\n")
        self.protocol.lineReceived("error a\n")
        self.protocol.lineReceived("error: a\n")
        self.protocol.lineReceived("success a\n")
        self.protocol.lineReceived("success: a\n")
        self.protocol.lineReceived("successful a\n")
        self.protocol.lineReceived("successful: a\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.stdout.getvalue(), "failure a\n"
                                                 "failure: a\n"
                                                 "error a\n"
                                                 "error: a\n"
                                                 "success a\n"
                                                 "success: a\n"
                                                 "successful a\n"
                                                 "successful: a\n"
                                                 "]\n")

    def test_keywords_before_test(self):
        self.keywords_before_test()
        self.assertEqual(self.client.start_calls, [])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [])

    def test_keywords_after_error(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("error old mcdonald\n")
        self.keywords_before_test()
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls,
                         [(self.test, subunit.RemoteError(""))])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [])

    def test_keywords_after_failure(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("failure old mcdonald\n")
        self.keywords_before_test()
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls,
                         [(self.test, subunit.RemoteError())])
        self.assertEqual(self.client.success_calls, [])

    def test_keywords_after_success(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("success old mcdonald\n")
        self.keywords_before_test()
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [self.test])

    def test_keywords_after_test(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("failure a\n")
        self.protocol.lineReceived("failure: a\n")
        self.protocol.lineReceived("error a\n")
        self.protocol.lineReceived("error: a\n")
        self.protocol.lineReceived("success a\n")
        self.protocol.lineReceived("success: a\n")
        self.protocol.lineReceived("successful a\n")
        self.protocol.lineReceived("successful: a\n")
        self.protocol.lineReceived("]\n")
        self.protocol.lineReceived("failure old mcdonald\n")
        self.assertEqual(self.stdout.getvalue(), "test old mcdonald\n"
                                                 "failure a\n"
                                                 "failure: a\n"
                                                 "error a\n"
                                                 "error: a\n"
                                                 "success a\n"
                                                 "success: a\n"
                                                 "successful a\n"
                                                 "successful: a\n"
                                                 "]\n")
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.failure_calls,
                         [(self.test, subunit.RemoteError())])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.success_calls, [])

    def test_keywords_during_failure(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("failure: old mcdonald [\n")
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("failure a\n")
        self.protocol.lineReceived("failure: a\n")
        self.protocol.lineReceived("error a\n")
        self.protocol.lineReceived("error: a\n")
        self.protocol.lineReceived("success a\n")
        self.protocol.lineReceived("success: a\n")
        self.protocol.lineReceived("successful a\n")
        self.protocol.lineReceived("successful: a\n")
        self.protocol.lineReceived(" ]\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.stdout.getvalue(), "")
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.failure_calls,
                         [(self.test, subunit.RemoteError("test old mcdonald\n"
                                                  "failure a\n"
                                                  "failure: a\n"
                                                  "error a\n"
                                                  "error: a\n"
                                                  "success a\n"
                                                  "success: a\n"
                                                  "successful a\n"
                                                  "successful: a\n"
                                                  "]\n"))])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.success_calls, [])

    def test_stdout_passthrough(self):
        """Lines received which cannot be interpreted as any protocol action
        should be passed through to sys.stdout.
        """
        bytes = "randombytes\n"
        self.protocol.lineReceived(bytes)
        self.assertEqual(self.stdout.getvalue(), bytes)


class TestTestProtocolServerLostConnection(unittest.TestCase):

    def setUp(self):
        self.client = MockTestProtocolServerClient()
        self.protocol = subunit.TestProtocolServer(self.client)
        self.test = subunit.RemotedTestCase("old mcdonald")

    def test_lost_connection_no_input(self):
        self.protocol.lostConnection()
        self.assertEqual(self.client.start_calls, [])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [])

    def test_lost_connection_after_start(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lostConnection()
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [
            (self.test, subunit.RemoteError("lost connection during "
                                            "test 'old mcdonald'"))])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [])

    def test_lost_connected_after_error(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("error old mcdonald\n")
        self.protocol.lostConnection()
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [
            (self.test, subunit.RemoteError(""))])
        self.assertEqual(self.client.success_calls, [])

    def test_lost_connection_during_error(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("error old mcdonald [\n")
        self.protocol.lostConnection()
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [
            (self.test, subunit.RemoteError("lost connection during error "
                                            "report of test 'old mcdonald'"))])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [])

    def test_lost_connected_after_failure(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("failure old mcdonald\n")
        self.protocol.lostConnection()
        test = subunit.RemotedTestCase("old mcdonald")
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls,
                         [(self.test, subunit.RemoteError())])
        self.assertEqual(self.client.success_calls, [])

    def test_lost_connection_during_failure(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("failure old mcdonald [\n")
        self.protocol.lostConnection()
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls,
                         [(self.test,
                           subunit.RemoteError("lost connection during "
                                               "failure report"
                                               " of test 'old mcdonald'"))])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [])

    def test_lost_connection_after_success(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("success old mcdonald\n")
        self.protocol.lostConnection()
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [self.test])

    def test_lost_connection_during_skip(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("skip old mcdonald [\n")
        self.protocol.lostConnection()
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [
            (self.test, subunit.RemoteError("lost connection during skip "
                                            "report of test 'old mcdonald'"))])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [])

    def test_lost_connection_during_xfail(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("xfail old mcdonald [\n")
        self.protocol.lostConnection()
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [
            (self.test, subunit.RemoteError("lost connection during xfail "
                                            "report of test 'old mcdonald'"))])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [])

    def test_lost_connection_during_success(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("success old mcdonald [\n")
        self.protocol.lostConnection()
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [
            (self.test, subunit.RemoteError("lost connection during success "
                                            "report of test 'old mcdonald'"))])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [])


class TestTestProtocolServerAddError(unittest.TestCase):

    def setUp(self):
        self.client = MockTestProtocolServerClient()
        self.protocol = subunit.TestProtocolServer(self.client)
        self.protocol.lineReceived("test mcdonalds farm\n")
        self.test = subunit.RemotedTestCase("mcdonalds farm")

    def simple_error_keyword(self, keyword):
        self.protocol.lineReceived("%s mcdonalds farm\n" % keyword)
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [
            (self.test, subunit.RemoteError(""))])
        self.assertEqual(self.client.failure_calls, [])

    def test_simple_error(self):
        self.simple_error_keyword("error")

    def test_simple_error_colon(self):
        self.simple_error_keyword("error:")

    def test_error_empty_message(self):
        self.protocol.lineReceived("error mcdonalds farm [\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [
            (self.test, subunit.RemoteError(""))])
        self.assertEqual(self.client.failure_calls, [])

    def error_quoted_bracket(self, keyword):
        self.protocol.lineReceived("%s mcdonalds farm [\n" % keyword)
        self.protocol.lineReceived(" ]\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [
            (self.test, subunit.RemoteError("]\n"))])
        self.assertEqual(self.client.failure_calls, [])

    def test_error_quoted_bracket(self):
        self.error_quoted_bracket("error")

    def test_error_colon_quoted_bracket(self):
        self.error_quoted_bracket("error:")


class TestTestProtocolServerAddFailure(unittest.TestCase):

    def setUp(self):
        self.client = MockTestProtocolServerClient()
        self.protocol = subunit.TestProtocolServer(self.client)
        self.protocol.lineReceived("test mcdonalds farm\n")
        self.test = subunit.RemotedTestCase("mcdonalds farm")

    def simple_failure_keyword(self, keyword):
        self.protocol.lineReceived("%s mcdonalds farm\n" % keyword)
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls,
                         [(self.test, subunit.RemoteError())])

    def test_simple_failure(self):
        self.simple_failure_keyword("failure")

    def test_simple_failure_colon(self):
        self.simple_failure_keyword("failure:")

    def test_failure_empty_message(self):
        self.protocol.lineReceived("failure mcdonalds farm [\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls,
                         [(self.test, subunit.RemoteError())])

    def failure_quoted_bracket(self, keyword):
        self.protocol.lineReceived("%s mcdonalds farm [\n" % keyword)
        self.protocol.lineReceived(" ]\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls,
                         [(self.test, subunit.RemoteError("]\n"))])

    def test_failure_quoted_bracket(self):
        self.failure_quoted_bracket("failure")

    def test_failure_colon_quoted_bracket(self):
        self.failure_quoted_bracket("failure:")


class TestTestProtocolServerAddxFail(unittest.TestCase):
    """Tests for the xfail keyword.

    In Python this can thunk through to Success due to stdlib limitations (see
    README).
    """

    def capture_expected_failure(self, test, err):
        self._calls.append((test, err))

    def setup_python26(self):
        """Setup a test object ready to be xfailed and thunk to success."""
        self.client = MockTestProtocolServerClient()
        self.setup_protocol()

    def setup_python27(self):
        """Setup a test object ready to be xfailed and thunk to success."""
        self.client = MockTestProtocolServerClient()
        self.client.addExpectedFailure = self.capture_expected_failure
        self._calls = []
        self.setup_protocol()

    def setup_protocol(self):
        """Setup the protocol based on self.client."""
        self.protocol = subunit.TestProtocolServer(self.client)
        self.protocol.lineReceived("test mcdonalds farm\n")
        self.test = self.client.start_calls[-1]

    def simple_xfail_keyword(self, keyword, as_success):
        self.protocol.lineReceived("%s mcdonalds farm\n" % keyword)
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, [])
        self.check_success_or_xfail(as_success)

    def check_success_or_xfail(self, as_success):
        if as_success:
            self.assertEqual(self.client.success_calls, [self.test])
        else:
            self.assertEqual(1, len(self._calls))
            self.assertEqual(self.test, self._calls[0][0])

    def test_simple_xfail(self):
        self.setup_python26()
        self.simple_xfail_keyword("xfail", True)
        self.setup_python27()
        self.simple_xfail_keyword("xfail",  False)

    def test_simple_xfail_colon(self):
        self.setup_python26()
        self.simple_xfail_keyword("xfail:", True)
        self.setup_python27()
        self.simple_xfail_keyword("xfail:", False)

    def test_xfail_empty_message(self):
        self.setup_python26()
        self.empty_message(True)
        self.setup_python27()
        self.empty_message(False)

    def empty_message(self, as_success):
        self.protocol.lineReceived("xfail mcdonalds farm [\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, [])
        self.check_success_or_xfail(as_success)

    def xfail_quoted_bracket(self, keyword, as_success):
        # This tests it is accepted, but cannot test it is used today, because
        # of not having a way to expose it in Python so far.
        self.protocol.lineReceived("%s mcdonalds farm [\n" % keyword)
        self.protocol.lineReceived(" ]\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, [])
        self.check_success_or_xfail(as_success)

    def test_xfail_quoted_bracket(self):
        self.setup_python26()
        self.xfail_quoted_bracket("xfail", True)
        self.setup_python27()
        self.xfail_quoted_bracket("xfail", False)

    def test_xfail_colon_quoted_bracket(self):
        self.setup_python26()
        self.xfail_quoted_bracket("xfail:", True)
        self.setup_python27()
        self.xfail_quoted_bracket("xfail:", False)


class TestTestProtocolServerAddSkip(unittest.TestCase):
    """Tests for the skip keyword.

    In Python this meets the testtools extended TestResult contract.
    (See https://launchpad.net/testtools).
    """

    def setUp(self):
        """Setup a test object ready to be skipped."""
        self.client = MockTestProtocolServerClient()
        self.protocol = subunit.TestProtocolServer(self.client)
        self.protocol.lineReceived("test mcdonalds farm\n")
        self.test = self.client.start_calls[-1]

    def simple_skip_keyword(self, keyword):
        self.protocol.lineReceived("%s mcdonalds farm\n" % keyword)
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [])
        self.assertEqual(self.client.skip_calls,
            [(self.test, 'No reason given')])

    def test_simple_skip(self):
        self.simple_skip_keyword("skip")

    def test_simple_skip_colon(self):
        self.simple_skip_keyword("skip:")

    def test_skip_empty_message(self):
        self.protocol.lineReceived("skip mcdonalds farm [\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [])
        self.assertEqual(self.client.skip_calls,
            [(self.test, "No reason given")])

    def skip_quoted_bracket(self, keyword):
        # This tests it is accepted, but cannot test it is used today, because
        # of not having a way to expose it in Python so far.
        self.protocol.lineReceived("%s mcdonalds farm [\n" % keyword)
        self.protocol.lineReceived(" ]\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [])
        self.assertEqual(self.client.skip_calls,
            [(self.test, "]\n")])

    def test_skip_quoted_bracket(self):
        self.skip_quoted_bracket("skip")

    def test_skip_colon_quoted_bracket(self):
        self.skip_quoted_bracket("skip:")


class TestTestProtocolServerAddSuccess(unittest.TestCase):

    def setUp(self):
        self.client = MockTestProtocolServerClient()
        self.protocol = subunit.TestProtocolServer(self.client)
        self.protocol.lineReceived("test mcdonalds farm\n")
        self.test = subunit.RemotedTestCase("mcdonalds farm")

    def simple_success_keyword(self, keyword):
        self.protocol.lineReceived("%s mcdonalds farm\n" % keyword)
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.success_calls, [self.test])

    def test_simple_success(self):
        self.simple_success_keyword("failure")

    def test_simple_success_colon(self):
        self.simple_success_keyword("failure:")

    def test_simple_success(self):
        self.simple_success_keyword("successful")

    def test_simple_success_colon(self):
        self.simple_success_keyword("successful:")

    def test_success_empty_message(self):
        self.protocol.lineReceived("success mcdonalds farm [\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [self.test])

    def success_quoted_bracket(self, keyword):
        # This tests it is accepted, but cannot test it is used today, because
        # of not having a way to expose it in Python so far.
        self.protocol.lineReceived("%s mcdonalds farm [\n" % keyword)
        self.protocol.lineReceived(" ]\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [self.test])

    def test_success_quoted_bracket(self):
        self.success_quoted_bracket("success")

    def test_success_colon_quoted_bracket(self):
        self.success_quoted_bracket("success:")


class TestTestProtocolServerProgress(unittest.TestCase):
    """Test receipt of progress: directives."""

    def test_progress_accepted_stdlib(self):
        # With a stdlib TestResult, progress events are swallowed.
        self.result = unittest.TestResult()
        self.stream = StringIO()
        self.protocol = subunit.TestProtocolServer(self.result,
            stream=self.stream)
        self.protocol.lineReceived("progress: 23")
        self.protocol.lineReceived("progress: -2")
        self.protocol.lineReceived("progress: +4")
        self.assertEqual("", self.stream.getvalue())

    def test_progress_accepted_extended(self):
        # With a progress capable TestResult, progress events are emitted.
        self.result = MockTestProtocolServerClient()
        self.stream = StringIO()
        self.protocol = subunit.TestProtocolServer(self.result,
            stream=self.stream)
        self.protocol.lineReceived("progress: 23")
        self.protocol.lineReceived("progress: push")
        self.protocol.lineReceived("progress: -2")
        self.protocol.lineReceived("progress: pop")
        self.protocol.lineReceived("progress: +4")
        self.assertEqual("", self.stream.getvalue())
        self.assertEqual(
            [(23, subunit.PROGRESS_SET), (None, subunit.PROGRESS_PUSH),
             (-2, subunit.PROGRESS_CUR), (None, subunit.PROGRESS_POP),
             (4, subunit.PROGRESS_CUR)],
            self.result.progress_calls)


class TestTestProtocolServerStreamTags(unittest.TestCase):
    """Test managing tags on the protocol level."""

    def setUp(self):
        self.client = MockExtendedTestProtocolServerClient()
        self.protocol = subunit.TestProtocolServer(self.client)

    def test_initial_tags(self):
        self.protocol.lineReceived("tags: foo bar:baz  quux\n")
        self.assertEqual(set(["foo", "bar:baz", "quux"]),
            self.client.new_tags)
        self.assertEqual(set(), self.client.gone_tags)

    def test_minus_removes_tags(self):
        self.protocol.lineReceived("tags: foo bar\n")
        self.assertEqual(set(["foo", "bar"]),
            self.client.new_tags)
        self.assertEqual(set(), self.client.gone_tags)
        self.protocol.lineReceived("tags: -bar quux\n")
        self.assertEqual(set(["quux"]), self.client.new_tags)
        self.assertEqual(set(["bar"]), self.client.gone_tags)

    def test_tags_do_not_get_set_on_test(self):
        self.protocol.lineReceived("test mcdonalds farm\n")
        test = self.client.start_calls[-1]
        self.assertEqual(None, getattr(test, 'tags', None))

    def test_tags_do_not_get_set_on_global_tags(self):
        self.protocol.lineReceived("tags: foo bar\n")
        self.protocol.lineReceived("test mcdonalds farm\n")
        test = self.client.start_calls[-1]
        self.assertEqual(None, getattr(test, 'tags', None))

    def test_tags_get_set_on_test_tags(self):
        self.protocol.lineReceived("test mcdonalds farm\n")
        test = self.client.start_calls[-1]
        self.protocol.lineReceived("tags: foo bar\n")
        self.protocol.lineReceived("success mcdonalds farm\n")
        self.assertEqual(None, getattr(test, 'tags', None))


class TestTestProtocolServerStreamTime(unittest.TestCase):
    """Test managing time information at the protocol level."""

    def test_time_accepted_stdlib(self):
        self.result = unittest.TestResult()
        self.stream = StringIO()
        self.protocol = subunit.TestProtocolServer(self.result,
            stream=self.stream)
        self.protocol.lineReceived("time: 2001-12-12 12:59:59Z\n")
        self.assertEqual("", self.stream.getvalue())

    def test_time_accepted_extended(self):
        self.result = MockTestProtocolServerClient()
        self.stream = StringIO()
        self.protocol = subunit.TestProtocolServer(self.result,
            stream=self.stream)
        self.protocol.lineReceived("time: 2001-12-12 12:59:59Z\n")
        self.assertEqual("", self.stream.getvalue())
        self.assertEqual(datetime.datetime(2001, 12, 12, 12, 59, 59, 0,
            iso8601.Utc()), self.result._time)


class TestRemotedTestCase(unittest.TestCase):

    def test_simple(self):
        test = subunit.RemotedTestCase("A test description")
        self.assertRaises(NotImplementedError, test.setUp)
        self.assertRaises(NotImplementedError, test.tearDown)
        self.assertEqual("A test description",
                         test.shortDescription())
        self.assertEqual("A test description",
                         test.id())
        self.assertEqual("A test description (subunit.RemotedTestCase)", "%s" % test)
        self.assertEqual("<subunit.RemotedTestCase description="
                         "'A test description'>", "%r" % test)
        result = unittest.TestResult()
        test.run(result)
        self.assertEqual([(test, "RemoteException: "
                                 "Cannot run RemotedTestCases.\n\n")],
                         result.errors)
        self.assertEqual(1, result.testsRun)
        another_test = subunit.RemotedTestCase("A test description")
        self.assertEqual(test, another_test)
        different_test = subunit.RemotedTestCase("ofo")
        self.assertNotEqual(test, different_test)
        self.assertNotEqual(another_test, different_test)


class TestRemoteError(unittest.TestCase):

    def test_eq(self):
        error = subunit.RemoteError("Something went wrong")
        another_error = subunit.RemoteError("Something went wrong")
        different_error = subunit.RemoteError("boo!")
        self.assertEqual(error, another_error)
        self.assertNotEqual(error, different_error)
        self.assertNotEqual(different_error, another_error)

    def test_empty_constructor(self):
        self.assertEqual(subunit.RemoteError(), subunit.RemoteError(""))


class TestExecTestCase(unittest.TestCase):

    class SampleExecTestCase(subunit.ExecTestCase):

        def test_sample_method(self):
            """sample-script.py"""
            # the sample script runs three tests, one each
            # that fails, errors and succeeds

        def test_sample_method_args(self):
            """sample-script.py foo"""
            # sample that will run just one test.

    def test_construct(self):
        test = self.SampleExecTestCase("test_sample_method")
        self.assertEqual(test.script,
                         subunit.join_dir(__file__, 'sample-script.py'))

    def test_args(self):
        result = unittest.TestResult()
        test = self.SampleExecTestCase("test_sample_method_args")
        test.run(result)
        self.assertEqual(1, result.testsRun)

    def test_run(self):
        runner = MockTestProtocolServerClient()
        test = self.SampleExecTestCase("test_sample_method")
        test.run(runner)
        mcdonald = subunit.RemotedTestCase("old mcdonald")
        bing = subunit.RemotedTestCase("bing crosby")
        an_error = subunit.RemotedTestCase("an error")
        self.assertEqual(runner.error_calls,
                         [(an_error, subunit.RemoteError())])
        self.assertEqual(runner.failure_calls,
                         [(bing,
                           subunit.RemoteError(
                            "foo.c:53:ERROR invalid state\n"))])
        self.assertEqual(runner.start_calls, [mcdonald, bing, an_error])
        self.assertEqual(runner.end_calls, [mcdonald, bing, an_error])

    def test_debug(self):
        test = self.SampleExecTestCase("test_sample_method")
        test.debug()

    def test_count_test_cases(self):
        """TODO run the child process and count responses to determine the count."""

    def test_join_dir(self):
        sibling = subunit.join_dir(__file__, 'foo')
        expected = '%s/foo' % (os.path.split(__file__)[0],)
        self.assertEqual(sibling, expected)


class DoExecTestCase(subunit.ExecTestCase):

    def test_working_script(self):
        """sample-two-script.py"""


class TestIsolatedTestCase(unittest.TestCase):

    class SampleIsolatedTestCase(subunit.IsolatedTestCase):

        SETUP = False
        TEARDOWN = False
        TEST = False

        def setUp(self):
            TestIsolatedTestCase.SampleIsolatedTestCase.SETUP = True

        def tearDown(self):
            TestIsolatedTestCase.SampleIsolatedTestCase.TEARDOWN = True

        def test_sets_global_state(self):
            TestIsolatedTestCase.SampleIsolatedTestCase.TEST = True


    def test_construct(self):
        test = self.SampleIsolatedTestCase("test_sets_global_state")

    def test_run(self):
        result = unittest.TestResult()
        test = self.SampleIsolatedTestCase("test_sets_global_state")
        test.run(result)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(self.SampleIsolatedTestCase.SETUP, False)
        self.assertEqual(self.SampleIsolatedTestCase.TEARDOWN, False)
        self.assertEqual(self.SampleIsolatedTestCase.TEST, False)

    def test_debug(self):
        pass
        #test = self.SampleExecTestCase("test_sample_method")
        #test.debug()


class TestIsolatedTestSuite(unittest.TestCase):

    class SampleTestToIsolate(unittest.TestCase):

        SETUP = False
        TEARDOWN = False
        TEST = False

        def setUp(self):
            TestIsolatedTestSuite.SampleTestToIsolate.SETUP = True

        def tearDown(self):
            TestIsolatedTestSuite.SampleTestToIsolate.TEARDOWN = True

        def test_sets_global_state(self):
            TestIsolatedTestSuite.SampleTestToIsolate.TEST = True


    def test_construct(self):
        suite = subunit.IsolatedTestSuite()

    def test_run(self):
        result = unittest.TestResult()
        suite = subunit.IsolatedTestSuite()
        sub_suite = unittest.TestSuite()
        sub_suite.addTest(self.SampleTestToIsolate("test_sets_global_state"))
        sub_suite.addTest(self.SampleTestToIsolate("test_sets_global_state"))
        suite.addTest(sub_suite)
        suite.addTest(self.SampleTestToIsolate("test_sets_global_state"))
        suite.run(result)
        self.assertEqual(result.testsRun, 3)
        self.assertEqual(self.SampleTestToIsolate.SETUP, False)
        self.assertEqual(self.SampleTestToIsolate.TEARDOWN, False)
        self.assertEqual(self.SampleTestToIsolate.TEST, False)


class TestTestProtocolClient(unittest.TestCase):

    def setUp(self):
        self.io = StringIO()
        self.protocol = subunit.TestProtocolClient(self.io)
        self.test = TestTestProtocolClient("test_start_test")

    def test_start_test(self):
        """Test startTest on a TestProtocolClient."""
        self.protocol.startTest(self.test)
        self.assertEqual(self.io.getvalue(), "test: %s\n" % self.test.id())

    def test_stop_test(self):
        # stopTest doesn't output anything.
        self.protocol.stopTest(self.test)
        self.assertEqual(self.io.getvalue(), "")

    def test_add_success(self):
        """Test addSuccess on a TestProtocolClient."""
        self.protocol.addSuccess(self.test)
        self.assertEqual(
            self.io.getvalue(), "successful: %s\n" % self.test.id())

    def test_add_failure(self):
        """Test addFailure on a TestProtocolClient."""
        self.protocol.addFailure(
            self.test, subunit.RemoteError("boo qux"))
        self.assertEqual(
            self.io.getvalue(),
            'failure: %s [\nRemoteException: boo qux\n]\n' % self.test.id())

    def test_add_error(self):
        """Test stopTest on a TestProtocolClient."""
        self.protocol.addError(
            self.test, subunit.RemoteError("phwoar crikey"))
        self.assertEqual(
            self.io.getvalue(),
            'error: %s [\n'
            "RemoteException: phwoar crikey\n"
            "]\n" % self.test.id())

    def test_add_skip(self):
        """Test addSkip on a TestProtocolClient."""
        self.protocol.addSkip(
            self.test, "Has it really?")
        self.assertEqual(
            self.io.getvalue(),
            'skip: %s [\nHas it really?\n]\n' % self.test.id())

    def test_progress_set(self):
        self.protocol.progress(23, subunit.PROGRESS_SET)
        self.assertEqual(self.io.getvalue(), 'progress: 23\n')

    def test_progress_neg_cur(self):
        self.protocol.progress(-23, subunit.PROGRESS_CUR)
        self.assertEqual(self.io.getvalue(), 'progress: -23\n')

    def test_progress_pos_cur(self):
        self.protocol.progress(23, subunit.PROGRESS_CUR)
        self.assertEqual(self.io.getvalue(), 'progress: +23\n')

    def test_progress_pop(self):
        self.protocol.progress(1234, subunit.PROGRESS_POP)
        self.assertEqual(self.io.getvalue(), 'progress: pop\n')

    def test_progress_push(self):
        self.protocol.progress(1234, subunit.PROGRESS_PUSH)
        self.assertEqual(self.io.getvalue(), 'progress: push\n')

    def test_time(self):
        # Calling time() outputs a time signal immediately.
        self.protocol.time(
            datetime.datetime(2009,10,11,12,13,14,15, iso8601.Utc()))
        self.assertEqual(
            "time: 2009-10-11 12:13:14.000015Z\n",
            self.io.getvalue())


def test_suite():
    loader = subunit.tests.TestUtil.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result
