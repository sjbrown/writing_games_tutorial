#! /usr/bin/env python
'''
Example server
'''

from twisted.spread import pb
from example import EventManager, Game
from events import *
import network
from pprint import pprint

#------------------------------------------------------------------------------
class NoTickEventManager(EventManager):
    '''This subclass of EventManager doesn't wait for a Tick event before
    it starts consuming its event queue.  The server module doesn't have
    a CPUSpinnerController, so Ticks will not get generated.
    '''
    def __init__(self):
        EventManager.__init__(self)
        self._lock = False
    def Post(self, event):
        EventManager.Post(self,event)
        if not self._lock:
            self._lock = True
            self.ConsumeEventQueue()
            self._lock = False



#------------------------------------------------------------------------------
class NetworkClientController(pb.Root):
    """We RECEIVE events from the CLIENT through this object"""
    def __init__(self, evManager):
        self.evManager = evManager
        self.evManager.RegisterListener( self )

    #----------------------------------------------------------------------
    def remote_ClientConnect(self, netClient):
        print "\nremote_CLIENT CONNECT"
        ev = ClientConnectEvent( netClient )
        self.evManager.Post( ev )
        return 1

    #----------------------------------------------------------------------
    def remote_GetObjectState(self, objectID):
        #print "request for object state", objectID
        if not sharedObjectRegistry.has_key( objectID ):
            print "No key on the server"
            return [0,0]
        obj = sharedObjectRegistry[objectID]
        print 'getting state for object', obj
        print 'my registry is '
        pprint(sharedObjectRegistry)
        objDict = obj.getStateToCopy( sharedObjectRegistry )

        return [objectID, objDict]
    
    #----------------------------------------------------------------------
    def remote_EventOverNetwork(self, event):
        #print "Server just got an EVENT" + str(event)
        self.evManager.Post( event )
        return 1

    #----------------------------------------------------------------------
    def Notify(self, event):
        pass


#------------------------------------------------------------------------------
class TextLogView(object):
    def __init__(self, evManager):
        self.evManager = evManager
        self.evManager.RegisterListener( self )

    #----------------------------------------------------------------------
    def Notify(self, event):
        if event.__class__ in [TickEvent, SecondEvent]:
            return

        print 'TEXTLOG <',
        
        if isinstance( event, CharactorPlaceEvent ):
            print event.name, " at ", event.charactor.sector

        elif isinstance( event, CharactorMoveEvent ):
            print event.name, " to ", event.charactor.sector
        else:
            print 'event:', event


#------------------------------------------------------------------------------
class NetworkClientView(object):
    """We SEND events to the CLIENT through this object"""
    def __init__(self, evManager):
        self.evManager = evManager
        self.evManager.RegisterListener( self )

        self.clients = []


    #----------------------------------------------------------------------
    def EventThatShouldBeSent(self, event):
        if isinstance( event, ClientConnectEvent ):
            self.clients.append( event.client )

        ev = event

        #don't send events that aren't Copyable
        if not isinstance( ev, pb.Copyable ):
            evName = ev.__class__.__name__
            copyableClsName = "Copyable"+evName
            if not hasattr( network, copyableClsName ):
                return None
            copyableClass = getattr( network, copyableClsName )
            ev = copyableClass( ev, sharedObjectRegistry )

        if ev.__class__ not in network.serverToClientEvents:
            print "SERVER NOT SENDING: " +str(ev)
            return None

        return ev

    #----------------------------------------------------------------------
    def Notify(self, event):
        #NOTE: this is very "chatty".  We could restrict 
        #      the number of clients notified in the future
        ev = self.EventThatShouldBeSent(event)
        if not ev:
            return

        for client in self.clients:
            print "\n====server===sending: ", str(ev), 'to', client
            remoteCall = client.callRemote("ServerEvent", ev)



evManager = None
sharedObjectRegistry = None
#------------------------------------------------------------------------------
def main():
    global evManager, sharedObjectRegistry
    from twisted.internet import reactor
    evManager = NoTickEventManager()
    sharedObjectRegistry = {}

    log = TextLogView( evManager )
    clientController = NetworkClientController( evManager )
    clientView = NetworkClientView( evManager )
    game = Game( evManager )
    sharedObjectRegistry[id(game)] = game

    reactor.listenTCP( 8000, pb.PBServerFactory(clientController) )

    reactor.run()

if __name__ == "__main__":
    print 'starting server...'
    main()
