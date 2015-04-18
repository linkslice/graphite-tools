#!/bin/env python

import optparse

parser = optparse.OptionParser()
parser.add_option('-t', '--test', action='append')

options, args = parser.parse_args()
for i, opt in enumerate(options.test):
    print 'option %s: %s' % (i, opt)


