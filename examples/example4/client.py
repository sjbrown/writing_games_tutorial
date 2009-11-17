import sys
import time
import network
from twisted.spread import pb
from twisted.internet.selectreactor import SelectReactor
from twisted.internet.main import installReactor
from twisted.cred import credentials
from events import *
from example1 import (EventManager,
                      Game,
                      Player,
                      KeyboardController,
                      CPUSpinnerController,
                      PygameView)

serverHost, serverPort = 'localhost', 8000
avatarID = None

#------------------------------------------------------------------------------
class NetworkServerView(pb.Root):
    """We SEND events to the server through this object"""
    STATE_PREPARING = 0
    STATE_CONNECTING = 1
    STATE_CONNECTED = 2
    STATE_DISCONNECTING = 3
    STATE_DISCONNECTED = 4

    #----------------------------------------------------------------------
    def __init__(self, evManager, sharedObjectRegistry):
            self.evManager = evManager
            self.evManager.RegisterListener( self )

            self.pbClientFactory = pb.PBClientFactory()
            self.state = NetworkServerView.STATE_PREPARING
            self.reactor = None
            self.server = None

            self.sharedObjs = sharedObjectRegistry

    #----------------------------------------------------------------------
    def AttemptConnection(self):
            print "attempting a connection to", serverHost, serverPort
            self.state = NetworkServerView.STATE_CONNECTING
            if self.reactor:
                    self.reactor.stop()
                    self.PumpReactor()
            else:
                    self.reactor = SelectReactor()
                    installReactor(self.reactor)
            connection = self.reactor.connectTCP(serverHost, serverPort,
                                                 self.pbClientFactory)
            # TODO: make this anonymous login()
            #deferred = self.pbClientFactory.login(credentials.Anonymous())
            userCred = credentials.UsernamePassword(avatarID, 'pass1')
            controller = NetworkServerController( self.evManager )
            deferred = self.pbClientFactory.login(userCred, client=controller)
            deferred.addCallback(self.Connected)
            deferred.addErrback(self.ConnectFailed)
            self.reactor.startRunning()

    #----------------------------------------------------------------------
    def Disconnect(self):
            print "disconnecting"
            if not self.reactor:
                    return
            print 'stopping the reactor'
            self.reactor.stop()
            self.PumpReactor()
            self.state = NetworkServerView.STATE_DISCONNECTING

    #----------------------------------------------------------------------
    def Connected(self, server):
            print "CONNECTED"
            self.server = server
            self.state = NetworkServerView.STATE_CONNECTED
            ev = ServerConnectEvent( server )
            self.evManager.Post( ev )

    #----------------------------------------------------------------------
    def ConnectFailed(self, server):
            print "CONNECTION FAILED"
            print server
            print 'quitting'
            self.evManager.Post( QuitEvent() )
            #self.state = NetworkServerView.STATE_PREPARING
            self.state = NetworkServerView.STATE_DISCONNECTED

    #----------------------------------------------------------------------
    def PumpReactor(self):
            self.reactor.runUntilCurrent()
            self.reactor.doIteration(0)

    #----------------------------------------------------------------------
    def Notify(self, event):
            NSV = NetworkServerView
            if isinstance( event, TickEvent ):
                    if self.state == NSV.STATE_PREPARING:
                            self.AttemptConnection()
                    elif self.state in [NSV.STATE_CONNECTED,
                                        NSV.STATE_DISCONNECTING,
                                        NSV.STATE_CONNECTING]:
                            self.PumpReactor()
                    return

            if isinstance( event, QuitEvent ):
                    self.Disconnect()
                    return

            ev = event
            if not isinstance( event, pb.Copyable ):
                    evName = event.__class__.__name__
                    copyableClsName = "Copyable"+evName
                    if not hasattr( network, copyableClsName ):
                            return
                    copyableClass = getattr( network, copyableClsName )
                    #NOTE, never even construct an instance of an event that
                    # is serverToClient, as a side effect is often adding a
                    # key to the registry with the local id().
                    if copyableClass not in network.clientToServerEvents:
                        return
                    #print 'creating instance of copyable class', copyableClsName
                    ev = copyableClass( event, self.sharedObjs )

            if ev.__class__ not in network.clientToServerEvents:
                    #print "CLIENT NOT SENDING: " +str(ev)
                    return
                    
            if self.server:
                    print " ====   Client sending", str(ev)
                    remoteCall = self.server.callRemote("EventOverNetwork", ev)
            else:
                    print " =--= Cannot send while disconnected:", str(ev)


#------------------------------------------------------------------------------
class NetworkServerController(pb.Referenceable):
    """We RECEIVE events from the server through this object"""
    def __init__(self, evManager):
        self.evManager = evManager
        self.evManager.RegisterListener( self )

    #----------------------------------------------------------------------
    def remote_ServerEvent(self, event):
        print " ====  GOT AN EVENT FROM SERVER:", str(event)
        self.evManager.Post( event )
        return 1

    #----------------------------------------------------------------------
    def Notify(self, event):
        pass
        #if isinstance( event, ServerConnectEvent ):
            ##tell the server that we're listening to it and
            ##it can access this object
            #defrd = event.server.callRemote("ClientConnect", self)
            #defrd.addErrback(self.ServerErrorHandler)

    #----------------------------------------------------------------------
    def ServerErrorHandler(self, *args):
        print '\n **** ERROR REPORT **** '
        print 'Server threw us an error.  Args:', args
        ev = network.ServerErrorEvent()
        self.evManager.Post(ev)
        print ' ^*** ERROR REPORT ***^ \n'


#------------------------------------------------------------------------------
class PhonyEventManager(EventManager):
    """this object is responsible for coordinating most communication
    between the Model, View, and Controller."""
    #----------------------------------------------------------------------
    def Post( self, event ):
        pass

#------------------------------------------------------------------------------
class PhonyModel:
    '''This isn't the authouritative model.  That one exists on the
    server.  This is a model to store local state and to interact with
    the local EventManager.
    '''

    #----------------------------------------------------------------------
    def __init__(self, evManager, sharedObjectRegistry):
            self.sharedObjs = sharedObjectRegistry
            self.game = None
            self.server = None
            self.phonyEvManager = PhonyEventManager()
            self.realEvManager = evManager
            self.neededObjects = []
            self.waitingObjectStack = []

            self.realEvManager.RegisterListener( self )

    #----------------------------------------------------------------------
    def GameSyncReturned(self, response):
            gameID, gameDict = response
            print "GameSyncReturned : ", gameID
            self.sharedObjs[gameID] = self.game
            # StateReturned returns a deferred, pass it on to keep the
            # chain going.
            return self.StateReturned( response )

    #----------------------------------------------------------------------
    def StateReturned(self, response):
            """this is a callback that is called in response to
            invoking GetObjectState on the server"""

            #print "looking for ", response
            objID, objDict = response
            if objID == 0:
                    print "GOT ZERO -- TODO: better error handler here"
                    return None
            obj = self.sharedObjs[objID]

            success, neededObjIDs =\
                             obj.setCopyableState(objDict, self.sharedObjs)
            if success:
                    #we successfully set the state and no further objects
                    #are needed to complete the current object
                    if objID in self.neededObjects:
                            self.neededObjects.remove(objID)

            else:
                    #to complete the current object, we need to grab the
                    #state from some more objects on the server.  The IDs
                    #for those needed objects were passed back 
                    #in neededObjIDs
                    for neededObjID in neededObjIDs:
                            if neededObjID not in self.neededObjects:
                                    self.neededObjects.append(neededObjID)
                    print "failed.  still need ", self.neededObjects
    
            self.waitingObjectStack.append( (obj, objDict) )

            retval = self.GetAllNeededObjects()
            if retval:
                    # retval is a Deferred - returning it causes a chain
                    # to be formed.  The original deferred must wait for
                    # this new one to return before it calls its next
                    # callback
                    return retval
    
    #----------------------------------------------------------------------
    def GetAllNeededObjects(self):
            if len(self.neededObjects) == 0:
                    # this is the recursion-ending condition.  If there are
                    # no more objects needed to be grabbed from the server
                    # then we can try to setCopyableState on them again and
                    # we should now have all the needed objects, ensuring
                    # that setCopyableState succeeds
                    return self.ConsumeWaitingObjectStack()

            # still in the recursion step.  Try to get the object state for
            # the objectID on the top of the stack.  Note that the 
            # recursion is done via a deferred, which may be confusing
            nextID = self.neededObjects[-1]
            print "next one to grab: ", nextID
            remoteResponse = self.server.callRemote("GetObjectState",nextID)
            remoteResponse.addCallback(self.StateReturned)
            remoteResponse.addErrback(self.ServerErrorHandler, 'allNeededObjs')
            return remoteResponse

    #----------------------------------------------------------------------
    def ConsumeWaitingObjectStack(self):
        # All the needed objects should be present now.  Just the
        # matter of setting the state on the waiting objects remains.
        while self.waitingObjectStack:
            obj, objDict = self.waitingObjectStack.pop()
            success, neededObjIDs =\
                                 obj.setCopyableState(objDict, self.sharedObjs)
            if not success:
                print "WEIRD!!!!!!!!!!!!!!!!!!"

    #----------------------------------------------------------------------
    def Notify(self, event):
        if isinstance( event, ServerConnectEvent ):
            self.server = event.server
            #when we connect to the server, we should get the
            #entire game state.  this also applies to RE-connecting
            if not self.game:
                self.game = Game( self.phonyEvManager )
                gameID = id(self.game)
                self.sharedObjs[gameID] = self.game
            remoteResponse = self.server.callRemote("GetGameSync")
            remoteResponse.addCallback(self.GameSyncReturned)
            remoteResponse.addCallback(self.GameSyncCallback, gameID)
            remoteResponse.addErrback(self.ServerErrorHandler, 'ServerConnect')


        elif isinstance( event, network.CopyableGameStartedEvent ):
            gameID = event.gameID
            if not self.game:
                self.game = Game( self.phonyEvManager )
            self.sharedObjs[gameID] = self.game
            ev = GameStartedEvent( self.game )
            self.realEvManager.Post( ev )

        elif isinstance( event, network.ServerErrorEvent ):
            from pprint import pprint
            print 'Client state at the time of server error:'
            pprint(self.sharedObjs)

        if isinstance( event, network.CopyableMapBuiltEvent ):
            mapID = event.mapID
            if not self.sharedObjs.has_key(mapID):
                self.sharedObjs[mapID] = self.game.map
            remoteResponse = self.server.callRemote("GetObjectState", mapID)
            remoteResponse.addCallback(self.StateReturned)
            remoteResponse.addCallback(self.MapBuiltCallback, mapID)
            remoteResponse.addErrback(self.ServerErrorHandler, 'MapBuilt')

        if isinstance( event, network.CopyablePlayerJoinEvent ):
            playerID = event.playerID
            if not self.sharedObjs.has_key(playerID):
                player = Player( self.phonyEvManager )
                self.sharedObjs[playerID] = player
            remoteResponse = self.server.callRemote("GetObjectState", playerID)
            remoteResponse.addCallback(self.StateReturned)
            remoteResponse.addCallback(self.PlayerJoinCallback, playerID)
            remoteResponse.addErrback(self.ServerErrorHandler, 'PlayerJoin')

        if isinstance( event, network.CopyableCharactorPlaceEvent ):
            charactorID = event.charactorID
            if not self.sharedObjs.has_key(charactorID):
                charactor = self.game.players[0].charactors[0]
                self.sharedObjs[charactorID] = charactor
            remoteResponse = self.server.callRemote("GetObjectState", charactorID)
            remoteResponse.addCallback(self.StateReturned)
            remoteResponse.addCallback(self.CharactorPlaceCallback, charactorID)
            remoteResponse.addErrback(self.ServerErrorHandler, 'CharPlace')

        if isinstance( event, network.CopyableCharactorMoveEvent ):
            charactorID = event.charactorID
            if not self.sharedObjs.has_key(charactorID):
                charactor = self.game.players[0].charactors[0]
                self.sharedObjs[charactorID] = charactor
            remoteResponse = self.server.callRemote("GetObjectState", charactorID)
            remoteResponse.addCallback(self.StateReturned)
            remoteResponse.addCallback(self.CharactorMoveCallback, charactorID)
            remoteResponse.addErrback(self.ServerErrorHandler, 'CharMove')

    #----------------------------------------------------------------------
    def CharactorPlaceCallback(self, deferredResult, charactorID):
        charactor = self.sharedObjs[charactorID]
        ev = CharactorPlaceEvent( charactor )
        self.realEvManager.Post( ev )
    #----------------------------------------------------------------------
    def MapBuiltCallback(self, deferredResult, mapID):
        gameMap = self.sharedObjs[mapID]
        ev = MapBuiltEvent( gameMap )
        self.realEvManager.Post( ev )
    #----------------------------------------------------------------------
    def CharactorMoveCallback(self, deferredResult, charactorID):
        charactor = self.sharedObjs[charactorID]
        ev = CharactorMoveEvent( charactor )
        self.realEvManager.Post( ev )
    #----------------------------------------------------------------------
    def GameSyncCallback(self, deferredResult, gameID):
        game = self.sharedObjs[gameID]
        ev = GameSyncEvent( game )
        self.realEvManager.Post( ev )
    #----------------------------------------------------------------------
    def PlayerJoinCallback(self, deferredResult, playerID):
        player = self.sharedObjs[playerID]
        self.game.AddPlayer( player )
        ev = PlayerJoinEvent( player )
        self.realEvManager.Post( ev )
    #----------------------------------------------------------------------
    def ServerErrorHandler(self, failure, *args):
        print '\n **** ERROR REPORT **** '
        print 'Server threw PhonyModel an error.  failure:', failure
        print 'failure traceback:', failure.getTraceback()
        print 'Server threw PhonyModel an error.  Args:', args
        ev = network.ServerErrorEvent()
        self.realEvManager.Post(ev)
        print ' ^*** ERROR REPORT ***^ \n'


#class DebugDict(dict):
    #def __setitem__(self, *args):
        #print ''
        #print '        set item', args
        #return dict.__setitem__(self, *args)

#------------------------------------------------------------------------------
def main():
    global avatarID
    if len(sys.argv) > 1:
        avatarID = sys.argv[1]
    else:
        print 'You should provide a username on the command line'
        print 'Defaulting to username "user1"'
        time.sleep(1)
        avatarID = 'user1'
        
    evManager = EventManager()
    sharedObjectRegistry = {}
    #sharedObjectRegistry = DebugDict()
    keybd = KeyboardController( evManager, playerName=avatarID )
    spinner = CPUSpinnerController( evManager )
    pygameView = PygameView( evManager )

    phonyModel = PhonyModel( evManager, sharedObjectRegistry  )

    serverView = NetworkServerView( evManager, sharedObjectRegistry )
    
    try:
        spinner.Run()
    except Exception, ex:
        print 'got exception (%s)' % ex, 'killing reactor'
        import logging
        logging.basicConfig()
        logging.exception(ex)
        serverView.Disconnect()


if __name__ == "__main__":
    main()
