#!/bin/env python

import sys
import json
from httplib import HTTPConnection
from optparse import OptionParser


def fetchMetrics(host, port, url):
    connection = HTTPConnection(host, port)
    connection.request("GET", url)

    response = connection.getresponse()
    if response.status == 200:
        try:
            data = response.read()
        except Exception as uhoh:
            print "unknown error, possible empty response?: %s" % uhoh
    elif response.status == 401:
        print "Invalid username or password."
        sys.exit(1)
    elif response.status == 404:
        print "Web service not found."
        sys.exit(1)
    else:
        print "Web service error (%d): %s" % (response.status, response.reason)
        sys.exit(1)
    return data

def processResponse(body, nulls):
    data = json.loads(body)
    if not data[0]['datapoints'] and nulls:
        return 0
    else:
        for metric, timestamp in data[0]['datapoints']:
            return metric

def parse(range):
    invert = False
    if range.startswith('@'):
        range = range.strip('@')
        invert = True
    if ':' in range:
        start, end = range.split(':')
    else:
        start, end = '', range
    if start == '~':
        start = float('-inf')
    else:
        start = parse_atom(start, 0)
        end = parse_atom(end, float('inf'))
        return start, end, invert

def parse_atom(atom, default):
    if atom is '':
        return default
    if '.' in atom:
        return float(atom)
    return int(atom)

def makeNagios(metric, warning, critical):
    severity = "OK"
    code = 0
    min = ''
    max = ''
    if warning:
        wstart, wend, winvert = parse(warning)
        if winvert:
            if metric > wstart or metric < wend:
                severity = "WARNING"
                code = 1
        else:
            if metric > wend or metric < wstart:
                severity = "WARNING"
                code = 1
        min = wstart
        max = wend
    else: warning = ''
    if critical:
        cstart, cend, cinvert = parse(critical)
        if cinvert:
            if metric > cstart or metric < cend:
                severity = "CRITICAL"
                code = 2
        else:
            if metric > cend or metric < cstart:
                severity = "CRITICAL"
                code = 2
        min = cstart
        max = cend
    else: critical = ''

    print "%s|%s=%s;%s;%s;%s;%s; " % (severity, dataPointName, metric, warning, critical, min, max )
    sys.exit(code)



def main():
    parser = OptionParser()
    parser.add_option('-H', '--host', dest='host',
        help='Short hostname of the graphite server')
    parser.add_option('-p', '--port', dest='port',
        type='int', default=80,
        help='Port to connect to on the web server')
    parser.add_option('-u', '--url', dest='url',
        help='URL to retrieve data from')
    parser.add_option('-N', '--dataPointName', dest='datapointname',
        help='name of data point to return')
    parser.add_option('-n', '--none', dest='nulls',
        action='store_true', default=False,
        help='set null values to zero')
    parser.add_option('-c', '--critical', dest='critical',
        default=False,
        help='set range for critical threshold. [@][start:][end]')
    parser.add_option('-w', '--warning', dest='warning',
        default=False,
        help='set range for warning threshold. [@][start:][end]')
    options, args = parser.parse_args()

    if not options.host:
        print >> sys.stderr, "You must specify the host."
        sys.exit(1)
    elif not options.url:
        print >> sys.stderr, "You must specify the url."
        sys.exit(1)

    global dataPointName
    dataPointName = options.datapointname

    url = options.url + '&format=json&maxDataPoints=1'

    data = fetchMetrics(options.host, options.port, url)
    metrics = processResponse(data, options.nulls)
    makeNagios(metrics, options.warning, options.critical)

if __name__ == '__main__':
    main()
