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

def fetchOID(host, community, secLevel, secName, version, authProtocol, authPassword, privProtocol, privPassword, index, graphiteroot, verbose, debug):
    if verbose:
        print >> sys.stderr, 'connecting to host: %s using community: %s' % ( host, community )

    ifTable = {
        'ifHCInOctets': '.1.3.6.1.2.1.31.1.1.1.6',
        'ifHCOutOctets': '1.3.6.1.2.1.31.1.1.1.10',
        'ifHCInUcastPkts': '1.3.6.1.2.1.31.1.1.1.7',
        'ifHCOutUcastPkts': '1.3.6.1.2.1.31.1.1.1.11',
        'ifInErrors': '1.3.6.1.2.1.2.2.1.14',
        'ifOutErrors': '1.3.6.1.2.1.2.2.1.20'
        #'ifDescr': '.1.3.6.1.2.1.2.2.1.2'
        }
    if version == 1:
        snmp = netsnmp.Session(DestHost=host, Version=1, Community=community)
    elif version == 2:
        snmp = netsnmp.Session(DestHost=host, Version=2, Community=community)
    elif version == 3:
        snmp = netsnmp.Session(DestHost=host, Version=3, SecLevel=secLevel, AuthProto=authProtocol, AuthPass=authPassword,
                               PrivProto=privProtocol, PrivPass=privPassword, SecName=secName)
    else:
        print 'unknown version %s' % version
        
    currentTime = time.time()
    if not index:
        #interfaceList = '.1.3.6.1.2.1.2.2.1.1'
        interfaceList = '.1.3.6.1.2.1.2.2.1.2'
        Var = netsnmp.Varbind(interfaceList)
        Vars = netsnmp.VarList(Var)
        snmp.walk(Vars)
        for vs in Vars:
            #import pdb;pdb.set_trace()
            for type in ifTable:
                try:
                    vars = netsnmp.VarList(netsnmp.Varbind(ifTable[type], vs.iid))
                    result = [x[0] for x in snmp.get(vars)]
                    result = float(x)
                    if verbose:
                        print >> sys.stderr, '%s = %s' % (type, result)
                    currentTime = time.time()
                    datapoint = '%s.%s.%s' % (graphiteroot, vs.val, type)
                    package.append((datapoint, (currentTime, result)))
                except Exception as uhoh:
                    print >> sys.stderr, "could not get oid: %s" % uhoh
                    sys.exit(1)

    else:
        for type in ifTable:
            try:
                vars = netsnmp.VarList(netsnmp.Varbind(ifTable[type], index))
                result = [x[0] for x in snmp.get(vars)]
                result = float(x)
                if verbose:
                    print >> sys.stderr, '%s = %s' % (type, result)
                datapoint = '%s.%s' % (graphiteroot, type)
                package.append((datapoint, (currentTime, result)))
            except Exception as uhoh:
                print >> sys.stderr, "could not get oid: %s" % uhoh
                sys.exit(1)
    return package, currentTime, result


def makePickle(datapoint, currentTime, data, verbose, debug):
    if debug:
        print >> sys.stderr, 'storing pickle in \'data.p\''
        fh = open('data.p', 'wb')
        pickle.dump(package, fh)
    shippingPackage = pickle.dumps(package, 1)
    return shippingPackage

def sendPickle(carbonServer, carbonPort, shippingPackage, verbose, debug):
    packageSize = struct.pack('!L', len(shippingPackage))
    if verbose:
        print >> sys.stderr, 'connecting to carbon server: %s on port: %s' % ( carbonServer, carbonPort )
    try:
        s = socket.socket()
        s.connect((carbonServer, carbonPort))
        s.sendall(packageSize)
        s.sendall(shippingPackage)
        if verbose:
            print >> sys.stderr, 'sending pickle...'
    except Exception as uhoh:
        print "Could not connect to carbon server: %s" % uhoh
        sys.exit(1)

def main():
    parser = OptionParser()
    parser.add_option('-H', '--host', dest='host',
        help='Hostname/IP of the network device')
    parser.add_option('-c', '--community', dest='community',
        help='SNMP v2c community string to use')
    parser.add_option('-V', '--snmp-version', dest='snmpVersion',
        default='2',
        type='int',
        help='1, 2 or 3')
    parser.add_option('-l', '--security-level', dest='secLevel',
        help='noAuthNoPriv|authNoPriv|authPriv')
    parser.add_option('-u', '--sercurity-name', dest='secName',
        help='SNMPv3 sercurityName')
    parser.add_option('-a', '--auth-protocol', dest='authProtocol',
        help='MD5 or SHA')
    parser.add_option('-A', '--auth-password', dest='authPassword',
        help='SNMPv3 authentication pass phrase')
    parser.add_option('-x', '--priv-protocol', dest='privProtocol',
        help='DES or AES')
    parser.add_option('-X', '--priv-password', dest='privPassword',
        help='SNMPv3 privacy pass phrase')
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


    package, currentTime, result = fetchOID(options.host, options.community, options.secLevel, options.secName, options.snmpVersion, options.authProtocol,
                                            options.authPassword, options.privProtocol, options.privPassword, options.index,
                                            options.graphiteroot, options.verbose, options.debug)
    shippingPackage = makePickle(package, currentTime, result, options.verbose, options.debug)
    sendPickle(options.carbonserver, options.carbonport, shippingPackage, options.verbose, options.debug)


if __name__ == '__main__':
    main()
