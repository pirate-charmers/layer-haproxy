#!/usr/bin/python3

import amulet
# import requests
import unittest


class TestCharm(unittest.TestCase):
    def setUp(self):
        self.d = amulet.Deployment(series='xenial')

        self.d.add('haproxy')
        self.d.expose('haproxy')

        self.d.setup(timeout=900)
        self.d.sentry.wait()

        self.unit = self.d.sentry['haproxy'][0]

    def test_service(self):
        pass
        # test we can access over http
        # page = requests.get('http://{}'.format(self.unit.info['public-address']))
        # self.assertEqual(page.status_code, 200)
        # Now you can use self.d.sentry[SERVICE][UNIT] to address each of the units and perform
        # more in-depth steps. Each self.d.sentry[SERVICE][UNIT] has the following methods:
        # - .info - An array of the information of that unit from Juju
        # - .file(PATH) - Get the details of a file on that unit
        # - .file_contents(PATH) - Get plain text output of PATH file from that unit
        # - .directory(PATH) - Get details of directory
        # - .directory_contents(PATH) - List files and folders in PATH on that unit
        # - .relation(relation, service:rel) - Get relation data from return service


if __name__ == '__main__':
    unittest.main()
