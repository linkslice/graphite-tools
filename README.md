# graphite-tools
miscellaneous graphite tools


Most of these scripts should be fairly obvious based on the name. I'll document a few that are less so. The rest are typically run like so: ./script.py -H hostname -c snmpcommunity -G metricindex.hostname

check_graphite.py:
- fetch a datapoint from graphite and massage it into nagios format for monitoring tools that speak nagios (icinga, zenoss, and of course nagios.) Also does thresholding built in.

interface_stats.py:
- fetch the list of interfaces via snmp on a system and then fetch all the normal useful stats for those interfaces.

snmp_pickle.py:
- specify snmp oids and a matching label for each oid and it will fetch them all and dump them into graphite.


The haproxy bits are run the same wasy as every other script in this repo. Please see the links in the readme for my haproxy zenpack for configuring haproxy to return stats via snmp.
