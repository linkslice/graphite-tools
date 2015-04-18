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

def fetchOID(host, community, index):
    if options.verbose:
        print >> sys.stderr, 'connecting to host: %s using community: %s' % ( host, community )

    ifTable = {
        'ifHCInOctets': '.1.3.6.1.2.1.31.1.1.1.6',
        'ifHCOutOctets': '1.3.6.1.2.1.31.1.1.1.10',
        'ifHCInUcastPkts': '1.3.6.1.2.1.31.1.1.1.7',
        'ifHCOutUcastPkts': '1.3.6.1.2.1.31.1.1.1.11',
        'ifInErrors': '1.3.6.1.2.1.2.2.1.14',
        'ifOutErrors': '1.3.6.1.2.1.2.2.1.20'
        }
    snmp = netsnmp.Session(DestHost=host, Version=2, Community=community)

    

    for type in ifTable:
            #print type, ifTable[type]
        try:
            #head, tail = ifTable[type].rsplit('.', 1)
            #vars = netsnmp.VarList(netsnmp.Varbind(head, tail))
            vars = netsnmp.VarList(netsnmp.Varbind(ifTable[type], index))
            result = [x[0] for x in snmp.get(vars)]
            result = float(x)
            if options.verbose:
                print >> sys.stderr, '%s = %s' % (ifTable[type], result)
            currentTime = time.time()
            datapoint = '%s.%s' % (options.graphiteroot, type)
            package.append((datapoint, (currentTime, result)))
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
        help='Hostname/IP of the network device')
    parser.add_option('-c', '--community', dest='community',
        help='SNMP v2c community string to use')
    parser.add_option('-i', '--index', dest='index',
        type='int',
        help='Snmp Index to fetch stats for')
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


    fetchOID(options.host, options.community, options.index)



