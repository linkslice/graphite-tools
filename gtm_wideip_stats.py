#!/bin/env python

# Needs Net-SNMP Python bindings

from optparse import OptionParser
import sys
import os
import netsnmp
import pickle
import socket
import struct
import time

os.environ['MIBS'] = 'all' # install F5 mibs in net-snmp mibs directory
                           # usually /usr/share/snmp/mibs

package = ([])

def fetchOID(host, community, graphiteroot, virtualserver, verbose):
    if verbose:
        print >> sys.stderr, 'connecting to host: %s using community: %s' % ( host, community )

    statsTable = {
        'gtmWideipStatRequests': '1.3.6.1.4.1.3375.2.3.12.2.3.1.2',
        'gtmWideipStatResolutions': '1.3.6.1.4.1.3375.2.3.12.2.3.1.3',
        'gtmWideipStatPersisted': '1.3.6.1.4.1.3375.2.3.12.2.3.1.4',
        'gtmWideipStatPreferred': '1.3.6.1.4.1.3375.2.3.12.2.3.1.5',
        'gtmWideipStatFallback': '1.3.6.1.4.1.3375.2.3.12.2.3.1.6',
        'gtmWideipStatDropped': '1.3.6.1.4.1.3375.2.3.12.2.3.1.7',
        'gtmWideipStatExplicitIp': '1.3.6.1.4.1.3375.2.3.12.2.3.1.8',
        'gtmWideipStatReturnToDns': '1.3.6.1.4.1.3375.2.3.12.2.3.1.9'

        }
    snmp = netsnmp.Session(DestHost=host, Version=2, Community=community)
    
    # connect and fetch the list of virtual servers
    gtmWideipStatList = '.1.3.6.1.4.1.3375.2.3.12.2.3.1.1'
    Var = netsnmp.Varbind(gtmWideipStatList)
    Vars = netsnmp.VarList(Var)
    snmp.walk(Vars)
    currentTime = time.time()
    for vs in Vars:
        # vs.iid = the index of the virtualserver
        # vs.tag = leaf identifier e.g. 'ltmVirtualServName'
        # vs.val = name of virtual server
        # vs.type = snmp data type, e.g. counter, integer, etc
       
        # if we specified a list of virtualservers 
        # make sure we filter on those
        if virtualserver:
            if vs.val not in virtualserver:
                continue
        for type in statsTable:
            try:
                oid = statsTable[type] + "." + vs.iid
                head, tail = oid.rsplit('.', 1)
                vars = netsnmp.VarList(netsnmp.Varbind(head, tail))
                result = [x[0] for x in snmp.get(vars)]
                result = float(x)
                if verbose:
                    print >> sys.stderr, '%s %s = %s' % (vs.val, type, result)
                #currentTime = time.time()
                datapoint = '%s.%s.%s' % (graphiteroot, vs.val, type)
                package.append((datapoint, (currentTime, result)))
            except Exception as uhoh:
                print >> sys.stderr, "could not get oid: %s" % uhoh
                #sys.exit(1)

    return package, currentTime, result
    

def makePickle(datapoint, currentTime, data, verbose, debug):
    if debug:
        print >> sys.stderr, 'storing pickle in \'data.p\''
        fh = open('data.p', 'wb')
        pickle.dump(package, fh)
        sys.exit()
    shippingPackage = pickle.dumps(package, 1)
    return shippingPackage

def sendPickle(carbonServer, carbonPort, shippingPackage, verbose):
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
    parser.add_option('-s', '--virtualserver', dest='virtualserver',
        action='append',
        help='LTM virtual server(s) to fetch stats for. Can be used more than once or left out to just fetch all virtual servers.')
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
        help='do not submit to carbon. Output the pickle as file \'data.p\' in current directory')
    options, args = parser.parse_args()

    if not options.host or not options.community: 
        parser.print_help()
        sys.exit()

    #party time
    package, currentTime, result = fetchOID(options.host, options.community, options.graphiteroot, options.virtualserver, options.verbose)
    shippingPackage = makePickle(package, currentTime, result, options.verbose, options.debug)
    sendPickle(options.carbonserver, options.carbonport, shippingPackage, options.verbose)


if __name__ == '__main__':
    main()
