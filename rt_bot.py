# -*- coding: utf-8 -*-

# This file is part of rt_bot.
#
# Foobar is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Foobar is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Foobar.  If not, see <http://www.gnu.org/licenses/>.



from twisted.application import service
from twisted.python import log
from twisted.words.protocols.jabber.jid import JID
from wokkel.client import XMPPClient
from wokkel.muc import MUCClient
from base_bot import BaseMUCBot
import re
import ConfigParser

from rtkit.resource import RTResource
from rtkit.authenticators import BasicAuthenticator, CookieAuthenticator
from rtkit.errors import RTResourceError

from rtkit import set_logging
import urllib
import logging
#set_logging('debug')
logger = logging.getLogger('rtkit')


class NoResponse(Exception):
  pass


class RTBot(BaseMUCBot):
  def __init__(self, roomJID, nick, rt_url, rt_user, rt_pwd, roomPASSWORD):
    BaseMUCBot.__init__(self, roomJID, nick, roomPASSWORD)
    self.resource = RTResource(rt_url + 'REST/1.0/', rt_user, rt_pwd, CookieAuthenticator)
    self.rt_url = rt_url

  def handleGroupChat(self, room, user, message):
    if self.nick in message.body:
      if 'hi' in message.body or 'hello' in message.body:
        body = u"%s: greetings stranger arrr arrr!" % (user.nick)
        self.groupChat(self.roomJID, body)
      elif 'open' in message.body:
        queue = rt_default_queue

        m = re.search(r'open\s([^\s]+)', message.body)
        if m:
          queue = m.group(1)

        if queue == 'all':
          queue_query = ''
        else:
          queue_query = " AND QUEUE='" + queue + "'"

        query = "Owner = 'Nobody' AND ( Status = 'new' OR Status = 'open' )" + queue_query
        query = urllib.quote(query)
        prepend_string = 'Queue: ' + queue + '\n\n'

        try:
          ret = self.rtquery(query, prepend_string)
          self.groupChat(self.roomJID, ret)
        except NoResponse as e:
          self.groupChat(self.roomJID, e.message)

      elif 'search' in message.body:
        m = re.search(r'search\s([^\s]+)', message.body)
        if m:
          search = m.group(1)

          if len(search) >= 3:
            query = "Subject LIKE '" + search + "'"
            query = urllib.quote(query)

            try:
              ret = self.rtquery(query)
              self.groupChat(self.roomJID, ret)
            except NoResponse as e:
              self.groupChat(self.roomJID, e.message)
          else:
            self.groupChat(self.roomJID, 'Please enter at least 3 characters!')
        else:
          self.groupChat(self.roomJID, 'Nothing to search for!')

      elif 'ticket' in message.body:
        m = re.search(r'ticket\s([0-9]+)', message.body)
        if m:
          ticket_id = m.group(1)

          try:
            ret = self.rtticket(ticket_id)
            self.groupChat(self.roomJID, ret)
          except NoResponse as e:
            self.groupChat(self.roomJID, e.message)
        else:
          self.groupChat(self.roomJID, 'Nothing to search for!')

      elif 'help' in message.body:
        self.groupChat(self.roomJID, 'Usage:')
        self.groupChat(self.roomJID, 'open <queue name>  -  display all unassigned open and new tickets')
        self.groupChat(self.roomJID, '                                         queue name defaults to '+rt_default_queue)
        self.groupChat(self.roomJID, 'search <subject>        -  search for a subject')
        self.groupChat(self.roomJID, 'ticket <ticket-id>         -  display ticket information')

  def rtquery(self, query, prepend_text=''):
    ret = '\n'
    ret += prepend_text

    try:
      response = self.resource.get(path='search/ticket?query=' + query)

      if len(response.parsed) > 0:
        first = True

        for r in response.parsed:
          for t in r:
            if not first:
              ret += '\n'
            else:
              first = False

            logger.info(t)
            t_id = t[0]
            t_display = self.rt_url + 'Ticket/Display.html?id=' + t_id
            t_title = t[1]
            ret += 'Ticket#: ' + t_id + '\n'
            ret += 'URL: ' + t_display + '\n'
            ret += 'Title: ' + t_title + '\n'
      else:
        raise NoResponse('Nothing found!')
    except RTResourceError as e:
      logger.error(e.response.status_int)
      logger.error(e.response.status)
      logger.error(e.response.parsed)

    return unicode(ret, 'utf-8')

  def rtticket(self, ticket_id):
    ret = '\n'

    try:
      response = self.resource.get(path='ticket/' + ticket_id + '/show')

      if len(response.parsed) > 0:
        rsp_dict = {}

        for r in response.parsed:
          for t in r:
            rsp_dict[t[0]] = t[1]

        ret += 'Ticket#: ' + ticket_id + '\n'
        t_display = self.rt_url + 'Ticket/Display.html?id=' + ticket_id
        ret += 'URL: ' + t_display + '\n'
        ret += 'Title: ' + rsp_dict['Subject'] + '\n'
        ret += 'Queue: ' + rsp_dict['Queue'] + '\n'
        ret += 'Owner: ' + rsp_dict['Owner'] + '\n'
        ret += 'Creator: ' + rsp_dict['Creator'] + '\n'
        ret += 'Status: ' + rsp_dict['Status'] + '\n'
        ret += 'Requestors: ' + rsp_dict['Requestors'] + '\n'
        ret += 'Created: ' + rsp_dict['Created'] + '\n'
        ret += 'LastUpdated: ' + rsp_dict['LastUpdated'] + '\n'
        #ret += ': ' + rsp_dict[''] + '\n'

        if 'Resolved' in rsp_dict:
          ret += 'Resolved: ' + rsp_dict['Resolved'] + '\n'

      else:
        raise NoResponse('Nothing found!')
    except RTResourceError as e:
      logger.error(e.response.status_int)
      logger.error(e.response.status)
      logger.error(e.response.parsed)

    #return unicode(ret, 'utf-8')
    return ret


# Configuration parameters
config = ConfigParser.RawConfigParser()
config.read('bot.conf')

myJID = JID(config.get('Connection', 'my_jid'))
roomJID = JID(config.get('Connection', 'room_jid'))
roomPASSWORD = config.get('Connection', 'room_password')

my_nick = config.get('Connection', 'my_nick')
my_secret = config.get('Connection', 'my_secret')

rt_url = config.get('RT', 'url')
rt_user = config.get('RT', 'user')
rt_pwd = config.get('RT', 'pwd')
rt_default_queue = config.get('RT','default_queue')

LOG_TRAFFIC = False
#LOG_TRAFFIC = True

# Set up the Twisted application
application = service.Application("MUC Client")

client = XMPPClient(myJID, my_secret)
client.logTraffic = LOG_TRAFFIC
client.setServiceParent(application)

mucHandler = RTBot(roomJID, my_nick, rt_url, rt_user, rt_pwd, roomPASSWORD)
mucHandler.setHandlerParent(client)
