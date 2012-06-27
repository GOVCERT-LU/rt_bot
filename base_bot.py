# Georges Toth (c) 2012

from twisted.application import service
from twisted.python import log
from twisted.words.protocols.jabber.jid import JID
from wokkel.client import XMPPClient
from wokkel.muc import MUCClient



class BaseMUCBot(MUCClient):
  def __init__(self, roomJID, nick, roomPassword):
    MUCClient.__init__(self)
    self.roomJID = roomJID
    self.nick = nick
    self.roomPassword = roomPassword

  def connectionInitialized(self):
    """
    Once authorized, join the room.

    If the join action causes a new room to be created, the room will be
    locked until configured. Here we will just accept the default
    configuration by submitting an empty form using L{configure}, which
    usually results in a public non-persistent room.

    Alternatively, you would use L{getConfiguration} to retrieve the
    configuration form, and then submit the filled in form with the
    required settings using L{configure}, possibly after presenting it to
    an end-user.
    """
    def joinedRoom(room):
      if room.locked:
        # Just accept the default configuration. 
        return self.configure(room.roomJID, {})

    MUCClient.connectionInitialized(self)

    d = self.join(self.roomJID, self.nick, password=self.roomPassword)
    d.addCallback(joinedRoom)
    d.addCallback(lambda _: log.msg("Joined room"))
    d.addErrback(log.err, "Join failed")

  def receivedGroupChat(self, room, user, message):
    self.handleGroupChat(room, user, message)

  def handleGroupChat(self, room, user, message):
    pass
