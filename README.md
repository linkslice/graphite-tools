# graphite-tools
**note: checkout develop branch for python3 version. Bug reports and diffs welcome.

miscellaneous graphite tools


Most of these scripts should be fairly obvious based on the name. I'll document a few that are less so. The rest are typically run like so: ./script.py -H hostname -c snmpcommunity -G metricindex.hostname

check_graphite.py:
- fetch a datapoint from graphite and massage it into nagios format for monitoring tools that speak nagios (icinga, zenoss, and of course nagios.) Also does thresholding built in.

```
$ python check_graphite.py -H 10.10.10.12 -p 80 -u /render/\?width=586\&height=308\&_salt=1689629212.962\&target=carbon.agents.83fe1b18a7c4-a.metricsReceived -c20 -w14 -n -N DatapointName
CRITICAL - DatapointName|DatapointName=48.60528455284553;14;20;0;20;
```

interface_stats.py:
- fetch the list of interfaces via snmp on a system and then fetch all the normal useful stats for those interfaces.

snmp_pickle.py:
- specify snmp oids and a matching label for each oid and it will fetch them all and dump them into graphite.

codahale_metrics.py
- connect to codahale-style admin/metrics page and just feed all the things.

*The haproxy bits are run the same way as every other script in this repo. Please see the links in the readme for my haproxy zenpack for configuring haproxy to return stats via snmp. https://github.com/linkslice/ZenPacks.community.HAProxy
