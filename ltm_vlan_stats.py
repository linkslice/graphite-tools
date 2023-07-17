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

def fetchOID(host, community, graphiteroot, vlan, verbose):

    if verbose:
        print('connecting to host: %s using community: %s' % ( host, community ), file=sys.stderr)

    statsTable = {
        'sysVlanStatPktsIn': '1.3.6.1.4.1.3375.2.1.2.13.6.2.1.2',
        'sysVlanStatBytesIn': '1.3.6.1.4.1.3375.2.1.2.13.6.2.1.3',
        'sysVlanStatPktsOut': '1.3.6.1.4.1.3375.2.1.2.13.6.2.1.4',
        'sysVlanStatBytesOut': '1.3.6.1.4.1.3375.2.1.2.13.6.2.1.5',
        'sysVlanStatMcastIn': '1.3.6.1.4.1.3375.2.1.2.13.6.2.1.6',
        'sysVlanStatMcastOut': '1.3.6.1.4.1.3375.2.1.2.13.6.2.1.7',
        'sysVlanStatErrorsIn': '1.3.6.1.4.1.3375.2.1.2.13.6.2.1.8',
        'sysVlanStatErrorsOut': '1.3.6.1.4.1.3375.2.1.2.13.6.2.1.9',
        'sysVlanStatDropsIn': '1.3.6.1.4.1.3375.2.1.2.13.6.2.1.10',
        'sysVlanStatDropsOut': '1.3.6.1.4.1.3375.2.1.2.13.6.2.1.11',
        'sysVlanStatCollisions': '1.3.6.1.4.1.3375.2.1.2.13.6.2.1.12'
        }
    snmp = netsnmp.Session(DestHost=host, Version=2, Community=community)
    
    # connect and fetch the list of virtual servers
    vlanList = '.1.3.6.1.4.1.3375.2.1.2.13.1.2.1.2'
    Var = netsnmp.Varbind(vlanList)
    Vars = netsnmp.VarList(Var)
    snmp.walk(Vars)
    currentTime = time.time()
    for vs in Vars:
        # vs.iid = the index of the vlan
        # vs.tag = leaf identifier e.g. 'ltmVirtualServName'
        # vs.val = name of virtual server
        # vs.type = snmp data type, e.g. counter, integer, etc
       
        # if we specified a list of vlans 
        # make sure we filter on those
        if vlan:
            if vs.val not in vlan:
                continue

        for type in statsTable:
            try:
                oid = '1.3.6.1.4.1.3375.2.1.2.13.1.2.1.1' + '.' + vs.iid
                head, tail = oid.rsplit('.', 1)
                vars = netsnmp.VarList(netsnmp.Varbind(head, tail))
                result = [x[0] for x in snmp.get(vars)]
                sysVlanVname = x

                oid = statsTable[type] + "." + vs.iid
                head, tail = oid.rsplit('.', 1)
                vars = netsnmp.VarList(netsnmp.Varbind(head, tail))
                result = [x[0] for x in snmp.get(vars)]
                result = float(x)
                if verbose:
                    print('%s %s = %s' % (sysVlanVname, type, result), file=sys.stderr)
                #currentTime = time.time()
                datapoint = '%s.%s.%s' % (graphiteroot, sysVlanVname, type)
                package.append((datapoint, (currentTime, result)))
            except Exception as uhoh:
                print("could not get oid: %s" % uhoh, file=sys.stderr)
                #sys.exit(1)

    return package, currentTime, result
    

def makePickle(datapoint, currentTime, data, verbose, debug):
    if debug:
        print('storing pickle in \'data.p\'', file=sys.stderr)
        fh = open('data.p', 'wb')
        pickle.dump(package, fh)
        sys.exit()
    shippingPackage = pickle.dumps(package, 1)
    return shippingPackage

def sendPickle(carbonServer, carbonPort, shippingPackage, verbose):
    packageSize = struct.pack('!L', len(shippingPackage))
    if verbose:
        print('connecting to carbon server: %s on port: %s' % ( carbonServer, carbonPort ), file=sys.stderr)
    try:
        s = socket.socket()
        s.connect((carbonServer, carbonPort))
        s.sendall(packageSize)
        s.sendall(shippingPackage)
        if verbose:
            print('sending pickle...', file=sys.stderr)
    except Exception as uhoh:
        print("Could not connect to carbon server: %s" % uhoh)
        sys.exit(1)

def main():
    parser = OptionParser()
    parser.add_option('-H', '--host', dest='host',
        help='Hostname/IP of the network device')
    parser.add_option('-c', '--community', dest='community',
        help='SNMP v2c community string to use')
    parser.add_option('-s', '--vlan', dest='vlan',
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
    package, currentTime, result = fetchOID(options.host, options.community, options.graphiteroot, options.vlan, options.verbose)
    shippingPackage = makePickle(package, currentTime, result, options.verbose, options.debug)
    sendPickle(options.carbonserver, options.carbonport, shippingPackage, options.verbose)


if __name__ == '__main__':
    main()
