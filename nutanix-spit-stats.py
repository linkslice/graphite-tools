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

os.environ['MIBS'] = 'all' # install mibs in net-snmp mibs directory
                           # usually /usr/share/snmp/mibs

package = ([])

def fetchOID(host, username, seclevel,
             authProto, authPass, privPass, privProto,
             graphiteroot, spit, verbose):
    if verbose:
        print('connecting to host: %s using username: %s' % ( host, username ), file=sys.stderr)

    statsTable = {
        'spitTotalCapacity': '1.3.6.1.4.1.41263.7.1.4',
        'spitUsedCapacity': '1.3.6.1.4.1.41263.7.1.5',
        'spitIOPerSecond': '1.3.6.1.4.1.41263.7.1.6',
        'spitAvgLatencyUsecs': '1.3.6.1.4.1.41263.7.1.7'
        }
    snmp = netsnmp.Session(DestHost=host, Version=3, SecLevel=seclevel, AuthProto=authProto, AuthPass=authPass, PrivProto=privProto, PrivPass=privPass, SecName=username)
    
    # connect and fetch the list of virtual servers
    nutanixSpitList = '.1.3.6.1.4.1.41263.7.1.1'
    Var = netsnmp.Varbind(nutanixSpitList)
    Vars = netsnmp.VarList(Var)
    snmp.walk(Vars)
    currentTime = time.time()
    for disk in Vars:
        # vs.iid = the index of the virtualserver
        # vs.tag = leaf identifier e.g. 'ltmVirtualServName'
        # vs.val = name of virtual server
        # vs.type = snmp data type, e.g. counter, integer, etc
       
        # if we specified a list of virtualservers 
        # make sure we filter on those
        if spit:
            if disk.val not in spit:
                continue
        # lets first grab the storagepool name
        spitStoragePoolOid = '1.3.6.1.4.1.41263.7.1.3' + "." + disk.iid
        head, tail = spitStoragePoolOid.rsplit('.', 1)
        vars = netsnmp.VarList(netsnmp.Varbind(head, tail))
        result = [x[0] for x in snmp.get(vars)]
        spitStoragePoolName = x
        for type in statsTable:
            try:
                oid = statsTable[type] + "." + disk.iid
                head, tail = oid.rsplit('.', 1)
                vars = netsnmp.VarList(netsnmp.Varbind(head, tail))
                result = [x[0] for x in snmp.get(vars)]
                result = float(x)
                if verbose:
                    print('%s %s = %s' % (disk.val, type, result), file=sys.stderr)
                #currentTime = time.time()
                datapoint = '%s.%s.%s' % (graphiteroot, spitStoragePoolName, type)
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
    parser.add_option('-u', '--username', dest='username',
        help='SNMPv3 username')
    parser.add_option('-s', '--spit', dest='spit',
        action='append',
        help='Disk Stat table')
    parser.add_option('-l', '--seclevel', dest='seclevel',
        help='SNMPv3 security level. e.g. authPriv, authNoPriv, noAuthNoPriv')
    parser.add_option('-a', '--authProto', dest='authProto',
        help='SNMPv3 auth protocol. e.g. MD5 or SHA')
    parser.add_option('-A', '--authpass', dest='authPass',
        help='SNMPv3 auth password')
    parser.add_option('-x', '--privproto', dest='privProto',
        help='SNMPv3 priv protocol. e.g. AES or DES')
    parser.add_option('-X', '--privpass', dest='privPass',
        help='SNMPv3 priv password')
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

    if not options.host or not options.username: 
        parser.print_help()
        sys.exit()

    #party time
    package, currentTime, result = fetchOID(options.host, options.username, options.seclevel, 
                                            options.authProto, options.authPass, options.privPass, options.privProto,
                                            options.graphiteroot, options.spit, options.verbose)
    shippingPackage = makePickle(package, currentTime, result, options.verbose, options.debug)
    sendPickle(options.carbonserver, options.carbonport, shippingPackage, options.verbose)


if __name__ == '__main__':
    main()
