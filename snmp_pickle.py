#!/bin/env python

# Needs Net-SNMP Python bindings

from optparse import OptionParser
import sys
import netsnmp
import pickle
import socket
import struct
import time

package = ([])

def fetchOID(host, community, oid, name):
    if options.verbose:
        print >> sys.stderr, 'connecting to host: %s using community: %s' % ( host, community )
    snmp = netsnmp.Session(DestHost=host, Version=2, Community=community)
    count = 0
    while count < len(oid):
        try:
            head, tail = oid[count].rsplit('.', 1)
            vars = netsnmp.VarList(netsnmp.Varbind(head, tail))
            result = [x[0] for x in snmp.get(vars)]
            result = float(x)
            if options.verbose:
                print >> sys.stderr, '%s = %s' % (oid[count], result)
            currentTime = time.time()
            datapoint = '%s.%s' % (options.graphiteroot, name[count])
            package.append((datapoint, (currentTime, result)))
            count += 1
        except Exception as uhoh:
            print >> sys.stderr, "could not get oid: %s" % uhoh
            sys.exit(1)
    makePickle(package, currentTime, result)
    

def makePickle(datapoint, currentTime, data):
    if options.debug:
        print >> sys.stderr, 'storing pickle in \'data.p\''
        fh = open('data.p', 'wb')
        pickle.dump(package, fh)
    shippingPackage = pickle.dumps(package, 1)
    sendPickle(options.carbonserver, options.carbonport, shippingPackage)

def sendPickle(carbonServer, carbonPort, shippingPackage):
    packageSize = struct.pack('!L', len(shippingPackage))
    if options.verbose:
        print >> sys.stderr, 'connecting to carbon server: %s on port: %s' % ( carbonServer, carbonPort )
    try:
        s = socket.socket()
        s.connect((carbonServer, carbonPort))
        s.sendall(packageSize)
        s.sendall(shippingPackage)
        if options.verbose:
            print >> sys.stderr, 'sending pickle...'
    except Exception as uhoh:
        print "Could not connect to carbon server: %s" % uhoh
        sys.exit(1)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-H', '--host', dest='host',
        help='Hostname/IP of the web server')
    parser.add_option('-c', '--community', dest='community',
        help='SNMP v2c community string to use')
    parser.add_option('-O', '--oid', dest='oid',
        action='append',
        help='OID to get, Can be used more than once. Must use -N to name them.')
    parser.add_option('-N', '--name', dest='name',
        action='append',
        help='oid name to use when submitting to graphite. Can be used more than once.')
    parser.add_option('-G', '--graphite-root', dest='graphiteroot',
        help='root of the tree to use in Graphite')
    parser.add_option('-S', '--carbon-server', dest='carbonserver',
        default='127.0.0.1',
        help='set the server to send the pickle to. Default: 127.0.0.1')
    parser.add_option('-p', '--carbon-port', dest='carbonport',
        default='2004',
        type='int',
        help='carbon port. Default: 2004')
    parser.add_option('-v', '--verbose', dest='verbose',
        action='store_true',
        help='enable verbose output')
    parser.add_option('-d', '--debug', dest='debug',
        action='store_true',
        help='enable debug mode. Currently just writes a pickle to current directory')
    options, args = parser.parse_args()

    #if len(args) == 0:
    #    parser.print_help()
    #    sys.exit()

    if len(options.oid) != len(options.name):
        print >> sys.stderr, "Critical: you must 'name' each 'oid'"
        sys.exit(1)

    fetchOID(options.host, options.community, options.oid, options.name)



