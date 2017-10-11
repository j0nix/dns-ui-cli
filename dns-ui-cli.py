#!/usr/bin/env python
# https://github.com/j0nix , yum install python2-requests PyYAML python-cmd2
import cmd
import getpass
import json
import os
import re
import sys

import requests
import yaml
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


# Read config-files class
class ReadConfig:
    def __init__(self):
        pass

    dnsuiconfigfile = os.path.expanduser("~/.dns-ui-cli.yml")
    dnsuiconf = None

    def dnsui(self):

        try:
            with open(self.dnsuiconfigfile, 'r') as ymlfile:
                self.dnsuiconf = yaml.load(ymlfile)

        except IOError:
            print "No configfile, use defaults"
        except:
            print "Unexpected error reading config file:", sys.exc_info()[0]
        finally:
            return self.dnsuiconf


# Class to interact with dns-ui API.. and some
class DnsUiApi:
    # Default API endpoint data, can be changed in configfile
    url = 'https://localhost'
    api = '/api/v2/zones/'

    # Action Templates
    add_tmpl = str('{ "action": "%s","name": "%s", "type": "A","ttl": "1H",'
                   '"comment": "%s","records": [ { "content": "%s", "enabled": true }]}')
    delete_tmpl = str('{"action": "delete","name": "%s","type": "A"}')
    actions_tmpl = str('{ "actions": [%s],"comment": "%s"}')

    # Validation regexp
    validName = re.compile("^([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]+[a-zA-Z0-9])+$")
    validIpV4 = re.compile(
        "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")

    # Store zones
    zones = []
    # Temporary store commits
    commits = []

    SSL_VERIFY = False

    COLORS = {
        'grey': '\033[1;30m', 'red': '\033[1;31m',
        'green': '\033[1;32m', 'yellow': '\033[1;33m',
        'brown': '\033[0;33m', 'blue': '\033[1;34m',
        'magenta': '\033[1;35m', 'cyan': '\033[1;36m',
        'white': '\033[1;37m', 'default': '\033[0m'
    }

    def __init__(self, usr, pwd, configobj=None):

        # If we had that configfile, parse data from dns-ui section
        if configobj:

            uicfg = configobj.dnsui()

            # Parse and set values if present  
            try:
                if uicfg['dns-ui']['url']:
                    self.url = uicfg['dns-ui']['url']
            except KeyError:
                pass

            try:
                if uicfg['dns-ui']['api']:
                    self.api = uicfg['dns-ui']['api']
            except KeyError:
                pass

            try:
                if uicfg['dns-ui']['ssl-verify']:
                    self.SSL_VERIFY = uicfg['dns-ui']['ssl-verify']
            except KeyError:
                pass

        # Set baseurl
        self.baseurl = "{}{}".format(self.url, self.api)

        print "* dns-ui@{}, ssl-verify={}".format(self.baseurl, self.SSL_VERIFY)

        myzones = None

        try:
            # Get zones that you have access to
            myzones = requests.get(self.baseurl, auth=(usr, pwd), verify=self.SSL_VERIFY)
            zones = myzones.json()
            for zone in zones:
                self.zones.append(zone['name'])

            # Save usr/pwd
            self.usr = usr
            self.pwd = pwd

        except requests.exceptions.ConnectionError:
            print "CONNECTION ERROR: Failed connect to '{}'".format(self.baseurl)
            exit(1)
        except ValueError:

            try:
                if myzones.status_code == 401:
                    print "UNAUTHORIZED ACCESS to {}".format(self.baseurl)
                else:
                    print "Failed to get data from %s [%s, %s] " % (
                        self.baseurl, myzones.status_code, myzones.content)
            finally:
                exit(1)

    # Needs patching upstream
    def changelog(self, zone, patch):

        try:

            change_id = patch.json()['changes_id']

            changelog = requests.get(
                self.baseurl + zone + "/changes/" + change_id,
                auth=(self.usr, self.pwd),
                verify=self.SSL_VERIFY
            )

            if changelog.status_code == 200:

                changes = changelog.json()

                msg = "\n\tDELETED: {}, ADDED: {}\n\n".format(changes['deleted'], changes['added'])

                for change in changes['changes']:

                    try:
                        msg = "{}\t{}DELETE {} {}{} <= ADD {} {}{}\n".format(
                            msg,
                            self.COLORS['red'],
                            change['before']['name'],
                            change['before']['rrs'][0]['content'],
                            self.COLORS['green'],
                            change['after']['name'],
                            change['after']['rrs'][0]['content'],
                            self.COLORS['default']
                        )
                    except KeyError:

                        try:
                            msg = "{}\t{}ADD    {} {}{}\n".format(
                                msg,
                                self.COLORS['green'],
                                change['after']['name'],
                                change['after']['rrs'][0]['content'],
                                self.COLORS['default']
                            )
                        except KeyError:

                            try:
                                msg = "{}\t{}DELETE {} {}{}\n".format(
                                    msg,
                                    self.COLORS['red'],
                                    change['before']['name'],
                                    change['before']['rrs'][0]['content'],
                                    self.COLORS['default']
                                )
                            except KeyError:
                                msg = "{}\t{}[KeyError exception] {}{}\n".format(msg, self.COLORS['grey'], str(change),
                                                                                 self.COLORS['default'])

                return msg

            else:
                return "FAIL fetching changelog {}/changes/{} => [reply]: {} [http-code]: {} [http-headers]: {}".format(
                    zone,
                    change_id,
                    changelog.content,
                    changelog.status_code,
                    changelog.request.headers
                )
        except:
            raise

    # Commit your actions, include zone and commit comment
    def commit(self, zone, comment):

        if not comment:
            return "COMMIT REQUEST DENIED, you must add a comment when commit"

        if zone in self.zones:
            # Prepare that json data 
            data = self.actions_tmpl % (",".join(self.commits), comment)
            data = json.loads(data)

            # zone needs to end wirh a dot
            if not zone.endswith('.'):
                zone = "{}.".format(zone)

            # start a session
            sess = requests.Session()
            sess.auth = (self.usr, self.pwd)

            # Commit actions
            patch = sess.patch(url=self.baseurl + zone, data=json.dumps(data), verify=False)

            # Success ?
            if patch.status_code == 200:

                if patch.content != 'null':

                    try:
                        print self.changelog(zone, patch)
                    except:
                        pass

                # truncate commits
                del self.commits[:]

                return "SUCCESS updating {}".format(zone)
            else:
                return "FAIL {} [data]: {} [reply]: {} [http-code]: {} [http-headers]: {}".format(zone,
                                                                                                  json.dumps(data),
                                                                                                  patch.txt,
                                                                                                  patch.status_code,
                                                                                                  patch.request.headers
                                                                                                  )
        else:
            print "Invalid zone: {}".format(zone)

    def list_commits(self):

        for i in range(len(self.commits)):
            c = json.loads(self.commits[i])
            try:
                print "[{}] {} {} {}".format(i, c['action'], c['name'], c['records'][0]['content'])
            except KeyError:
                print "[{}] {} {}".format(i, c['action'], c['name'])

    def remove_commits(self, index):

        try:
            x = int(index)
            del self.commits[x]
            return "Removed index {} from commit queue".format(index)
        except:
            return "Failed remove index {} from commit queue".format(index)

    def add_record(self, name, ipaddr):

        valid = self.validName.match(name)

        if not valid:
            return "Not a valid hostname '%s'" % name

        valid = self.validIpV4.match(ipaddr)

        if not valid:
            return "Not a valid ipaddress '%s'" % ipaddr

        action = self.add_tmpl % ("add", name, self.usr, ipaddr)
        self.commits.append(action)

        return "Added {} {} to commit queue".format(name, ipaddr)

    def update_record(self, name, ipaddr):

        valid = self.validName.match(name)

        if not valid:
            return "Not a valid hostname '%s'" % name

        valid = self.validIpV4.match(ipaddr)

        if not valid:
            return "Not a valid ipaddress '%s'" % ipaddr

        action = self.add_tmpl % ("update", name, self.usr, ipaddr)
        self.commits.append(action)

        return "Added {} {} to commit queue".format(name, ipaddr)

    def delete_record(self, name):

        valid = self.validName.match(name)

        if not valid:
            return "Not a valid hostname '%s'" % name

        action = self.delete_tmpl % name
        self.commits.append(action)

        return "Added delete {} to commit queue".format(name)


# noinspection PyUnusedLocal,PyUnusedLocal,PyUnusedLocal,PyUnusedLocal,PyUnusedLocal,PyUnusedLocal,PyUnusedLocal
class DnsUiCmd(cmd.Cmd):
    zone = "<None>"
    intro = "::Simple dnsui-cli by j0nix::"
    prompt = '[ZONE {}]: '.format(zone)
    dnsui = None

    def preloop(self):

        config = None

        try:
            config = ReadConfig()
            usr = config.dnsui()['cli-user']
            print "A user is set in configfile, login with username {}".format(usr)

        except:
            cfg = None
            usr = raw_input("Username: ")

        pwd = getpass.getpass('Password: ')

        self.dnsui = DnsUiApi(usr, pwd, config)

        if self.dnsui is None:
            print "Failed initiate communication with dns-ui, bailing out!"
            exit(1)

        if len(self.dnsui.zones) == 0:
            print "You don't have access to any zones!"

    def do_add(self, record):

        if self.zone in self.dnsui.zones:
            temp = record.split()
            print self.dnsui.add_record(temp[0], temp[1])
        else:
            print 'Missing zone, you MUST set zone'
            self.help_zone()

    @staticmethod
    def help_add():
        print "TODO"

    def do_update(self, record):

        if self.zone in self.dnsui.zones:
            temp = record.split()
            print self.dnsui.update_record(temp[0], temp[1])
        else:
            print 'Missing zone, you MUST set zone'
            self.help_zone()

    @staticmethod
    def help_update():
        print "TODO"

    def do_delete(self, name):

        if self.zone in self.dnsui.zones:
            print self.dnsui.delete_record(name)
        else:
            print 'Missing zone, you MUST set zone'
            self.help_zone()

    @staticmethod
    def help_delete():
        print "TODO"

    def do_commit(self, comment):

        if self.zone in self.dnsui.zones:
            if len(self.dnsui.commits) > 0:
                print self.dnsui.commit(self.zone, comment)
            else:
                print "nothing to commit?"
        else:
            print 'Missing zone, you MUST set zone'
            self.help_zone()

    @staticmethod
    def help_commit():
        print "TODO"

    def do_list(self, line):
        self.dnsui.list_commits()

    @staticmethod
    def help_list():
        print "TODO"

    def do_remove(self, index):
        print self.dnsui.remove_commits(index)

    @staticmethod
    def help_remove():
        print "TODO"

    def do_zone(self, zone):

        if zone:
            self.zone = zone
            self.prompt = "[ZONE {}]: ".format(self.zone)
            print "using zone", self.zone
        else:
            self.help_zone()

    def help_zone(self):

        print "\nSYNTAX: zone [zone]"
        print "\nZones:"
        for zone in self.dnsui.zones:
            print "\t{}".format(zone)
        print "\n Ex.\n\tzone int.comhem.com\n"

    def complete_zone(self, text, line, begidx, endidx):

        if not text:
            completions = self.dnsui.zones[:]
        else:
            completions = [f for f in self.dnsui.zones if f.startswith(text)]

        return completions

    @staticmethod
    def do_EOF(line):
        return True

    @staticmethod
    def help_EOF():
        print "This adds support to ctrl+d for exit"

    @staticmethod
    def do_exit(line):
        return True

    @staticmethod
    def help_exit():
        print "exit"

    def emptyline(self):
        pass


if __name__ == '__main__':
    DnsUiCmd().cmdloop()
