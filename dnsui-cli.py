#!/usr/bin/env python

import cmd
import re
import sys
import requests
import json
import getpass

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

#USAGE = '''Synopsis: A simple cli for dns-ui api.'''
#def parse_args():
#    parser = argparse.ArgumentParser(usage=USAGE)
#    parser.add_argument('--zone', '-z', type=str, dest='zone', help='Zone to interact with')
#    args = parser.parse_args()
#    return args


class dnsuiAPI():

    # Config file this
    baseurl = 'https://<url>/api/v2/zones/'

    add_tmpl = str('{ "actions": [ { "action": "%s","name": "%s","type": "A","ttl": "1H","comment": "","records": [{"content": "%s","enabled": true}]}],"comment": "%s@dns-ui-cli"}')
    del_tmpl = str('')

    validName = re.compile("^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]+[a-zA-Z0-9]))+$")

    validIpV4 = re.compile("^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")

    zones = []

    usr = ''
    pwd = ''

    SSL_VERIFY = False

    def __init__(self,usr,pwd):
       
        try:

            r = requests.get(self.baseurl, auth=(usr, pwd), verify=self.SSL_VERIFY)

            self.usr = usr
            self.pwd = pwd

            zones = r.json()

            for zone in zones:
                self.zones.append(zone['name'])

        except:
            print "Failed to get data from %s : %s" % (self.baseurl, sys.exc_info())
            raise

    def get_template(self):
        return self.template

    def add_record(self,zone,name,ipaddr):

        action = "add"

	valid = self.validName.match(name);

        if not valid:
	    return "Not a valid hostname '%s'" % name

        valid = self.validIpV4.match(ipaddr);

        if not valid:
            return "Not a valid ipaddress '%s'" % ipaddr

	data = self.add_tmpl % (action,name,ipaddr,self.usr)

	data = json.loads(data)

	if not zone.endswith('.'):
		zone = "{}.".format(zone)

	# start a session
	sess = requests.Session()
        sess.auth = (self.usr,self.pwd)

	# Add that record
	patch = sess.patch(url=self.baseurl+zone, data=json.dumps(data),verify=False)

	# If we failed due to existing name in zone, we try update, would like an other http error code here, perhaps patch dnsui
	if patch.status_code == 400:
            action = "update"
	    data = update_tmpl % (action,name,ipaddr,self.usr)
	    data = json.loads(data)
	    patch = sess.patch(url=self.baseurl+zone, data=json.dumps(data),verify=False)

	# Success ?
	if patch.status_code == 200:
	    return "SUCCESS {} {}.{} {}".format(action,name,zone,ipaddr)

	else:
            return "FAIL {} {}.{} {} => http-code: {} http-headers: {}".format(action,name,zone,ipaddr,patch.status_code,req.request.headers)


class dnsuiCMD(cmd.Cmd):
    """Simple command processor example."""

    zone = "?"
    intro = "Simple dnsui-cli"
    prompt = '[ZONE {}]: '.format(zone)

    dnsui = None

    def preloop(self):

        usr = raw_input("Username: ")
        pwd = getpass.getpass('Password: ')

        self.dnsui = dnsuiAPI(usr,pwd)

        if self.dnsui == None:
            print "Failes fetching zones from dns-ui, bailing out!"
            return True


    def emptyline(self):
        pass


    def do_add(self, record):

        if self.zone in self.dnsui.zones:

            temp = record.split()

            #print "%s %s %s" % (self.zone,temp[0],temp[1])
            print self.dnsui.add_record(self.zone,temp[0],temp[1])
            
        else:

            print 'Missing zone, you MUST set zone'
            self.help_zone()


    def do_zone(self, zone):

        if zone:
            self.zone = zone
            self.prompt = "[ZONE {}]: ".format(self.zone)
            print "using zone", self.zone
        else:
            self.help_zone()


    def complete_zone(self, text, line, begidx, endidx):

        if not text:
            completions = self.dnsui.zones[:]
        else:
            completions = [ f for f in self.dnsui.zones if f.startswith(text)]

        return completions

    def help_zone(self):

        print "\nSYNTAX: zone [zone]"
        print "\nZones:"
        for zone in self.dnsui.zones:
            print "\t{}".format(zone)
        print "\n Ex.\n\tzone int.comhem.com\n"

    def do_exit(self, line):
        return True

    def help_exit(self):
        print "exit"

    def do_EOF(self, line):
        return True
    
    def help_EOF(self):
        print "ctrl+d to exit"

if __name__ == '__main__':


    #if len(sys.argv) > 1:
    #    args = parse_args()
    #    if args.zone:
    #        zone = args.zone

    #    if zone !=None:
            #result = get_zone_data(BASEURL + "/zones/" + zone,usr,pwd)
    #        result = dnsuiCMD().onecmd(' '.join(sys.argv[1:]))

    #    if result != None:
    #        print result

    #else:
    #    dnsuiCMD().cmdloop()
