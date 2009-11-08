
from example1 import *
from twisted.spread import pb

# A list of ALL possible events that a server can send to a client
serverToClientEvents = []
# A list of ALL possible events that a client can send to a server
clientToServerEvents = []

#------------------------------------------------------------------------------
#Mix-In Helper Functions
#------------------------------------------------------------------------------
def MixInClass( origClass, addClass ):
	if addClass not in origClass.__bases__:
		origClass.__bases__ += (addClass,)

#------------------------------------------------------------------------------
def MixInCopyClasses( someClass ):
	MixInClass( someClass, pb.Copyable )
	MixInClass( someClass, pb.RemoteCopy )




#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# For each event class, if it is sendable over the network, we have 
# to Mix In the "copy classes", or make a replacement event class that is 
# copyable

#------------------------------------------------------------------------------
# TickEvent
# Direction: don't send.
#The Tick event happens hundreds of times per second.  If we think we need
#to send it over the network, we should REALLY re-evaluate our design

#------------------------------------------------------------------------------
# QuitEvent
# Direction: Client to Server only
MixInCopyClasses( QuitEvent )
pb.setUnjellyableForClass(QuitEvent, QuitEvent)
clientToServerEvents.append( QuitEvent )

#------------------------------------------------------------------------------
# GameStartRequest
# Direction: Client to Server only
MixInCopyClasses( GameStartRequest )
pb.setUnjellyableForClass(GameStartRequest, GameStartRequest)
clientToServerEvents.append( GameStartRequest )



#------------------------------------------------------------------------------
# ServerConnectEvent
# Direction: don't send.
# we don't need to send this over the network.

#------------------------------------------------------------------------------
# ClientConnectEvent
# Direction: don't send.
# we don't need to send this over the network.

#------------------------------------------------------------------------------
class ServerErrorEvent(object):
	def __init__(self):
		self.name = "Server Err Event"

#------------------------------------------------------------------------------
class ClientErrorEvent(object):
	def __init__(self):
		self.name = "Client Err Event"

#------------------------------------------------------------------------------
# GameStartedEvent
# Direction: Server to Client only
class CopyableGameStartedEvent(pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry):
		self.name = "Copyable Game Started Event"
		self.gameID = id(event.game)
		registry[self.gameID] = event.game
		#TODO: put this in a Player Join Event or something
		for p in event.game.players:
			registry[id(p)] = p

pb.setUnjellyableForClass(CopyableGameStartedEvent, CopyableGameStartedEvent)
serverToClientEvents.append( CopyableGameStartedEvent )

#------------------------------------------------------------------------------
# MapBuiltEvent
# Direction: Server to Client only
class CopyableMapBuiltEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable Map Finished Building Event"
		self.mapID = id( event.map )
		registry[self.mapID] = event.map

pb.setUnjellyableForClass(CopyableMapBuiltEvent, CopyableMapBuiltEvent)
serverToClientEvents.append( CopyableMapBuiltEvent )

#------------------------------------------------------------------------------
# CharactorMoveEvent
# Direction: Server to Client only
class CopyableCharactorMoveEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable " + event.name
		self.charactorID = id( event.charactor )
		registry[self.charactorID] = event.charactor

pb.setUnjellyableForClass(CopyableCharactorMoveEvent, CopyableCharactorMoveEvent)
serverToClientEvents.append( CopyableCharactorMoveEvent )

#------------------------------------------------------------------------------
# CharactorPlaceEvent
# Direction: Server to Client only
class CopyableCharactorPlaceEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable " + event.name
		self.charactorID = id( event.charactor )
		registry[self.charactorID] = event.charactor

pb.setUnjellyableForClass(CopyableCharactorPlaceEvent, CopyableCharactorPlaceEvent)
serverToClientEvents.append( CopyableCharactorPlaceEvent )


#------------------------------------------------------------------------------
# PlayerJoinRequest
# Direction: Client to Server only
MixInCopyClasses( PlayerJoinRequest )
pb.setUnjellyableForClass(PlayerJoinRequest, PlayerJoinRequest)
clientToServerEvents.append( PlayerJoinRequest )

#------------------------------------------------------------------------------
# PlayerJoinEvent
# Direction: Server to Client only
class CopyablePlayerJoinEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry):
		self.name = "Copyable " + event.name
		self.playerID = id(event.player)
		registry[self.playerID] = event.player
pb.setUnjellyableForClass(CopyablePlayerJoinEvent, CopyablePlayerJoinEvent)
serverToClientEvents.append( CopyablePlayerJoinEvent )

#------------------------------------------------------------------------------
# CharactorPlaceRequest
# Direction: Client to Server only
class CopyableCharactorPlaceRequest( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable " + event.name
		self.playerID = None
		self.charactorID = None
		self.sectorID = None
		for key,val in registry.iteritems():
			if val is event.player:
				print 'making char place request'
				print 'self.playerid', key
				self.playerID = key
			if val is event.charactor:
				self.charactorID = key
			if val is event.sector:
				self.sectorID = key
		if None in ( self.playerID, self.charactorID, self.sectorID):
			print "SOMETHING REALLY WRONG"
			print self.playerID, event.player
			print self.charactorID, event.charactor
			print self.sectorID, event.sector
pb.setUnjellyableForClass(CopyableCharactorPlaceRequest, CopyableCharactorPlaceRequest)
clientToServerEvents.append( CopyableCharactorPlaceRequest )

#------------------------------------------------------------------------------
# CharactorMoveRequest
# Direction: Client to Server only
class CopyableCharactorMoveRequest( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable " + event.name
		self.direction = event.direction
		self.playerID = None
		self.charactorID = None
		for key,val in registry.iteritems():
			if val is event.player:
				self.playerID = key
			if val is event.charactor:
				self.charactorID = key
		if None in ( self.playerID, self.charactorID):
			print "SOMETHING REALLY WRONG"
			print self.playerID, event.player
			print self.charactorID, event.charactor
pb.setUnjellyableForClass(CopyableCharactorMoveRequest, CopyableCharactorMoveRequest)
clientToServerEvents.append( CopyableCharactorMoveRequest )

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# For any objects that we need to send in our events, we have to give them
# getStateToCopy() and setCopyableState() methods so that we can send a 
# network-friendly representation of them over the network.

#------------------------------------------------------------------------------
class CopyableMap:
	def getStateToCopy(self, registry):
		sectorIDList = []
		for sect in self.sectors:
			sID = id(sect)
			sectorIDList.append( sID )
			registry[sID] = sect

		return {'ninegrid':1, 'sectorIDList':sectorIDList}


	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = 1

		if self.state != Map.STATE_BUILT:
			self.Build()

		for i, sectID in enumerate(stateDict['sectorIDList']):
			registry[sectID] = self.sectors[i]

		return [success, neededObjIDs]

MixInClass( Map, CopyableMap )

#------------------------------------------------------------------------------
class CopyableGame:
	def getStateToCopy(self, registry):
		d = self.__dict__.copy()
		del d['evManager']

		mID = id( self.map )
		d['map'] = mID
		registry[mID] = self.map

		playerIDList = []
		for player in self.players:
			pID = id( player )
			playerIDList.append( pID )
			registry[pID] = player
		d['players'] = playerIDList

		return d

	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = 1

		if not registry.has_key( stateDict['map'] ):
			registry[stateDict['map']] = Map( self.evManager )
			neededObjIDs.append( stateDict['map'] )
			success = 0
		else:
			self.map = registry[stateDict['map']]

		self.players = []
		for pID in stateDict['players']:
			if not registry.has_key( pID ):
				registry[pID] = Player( self.evManager )
				neededObjIDs.append( pID )
				success = 0
			else:
				self.players.append( registry[pID] )

		return [success, neededObjIDs]

MixInClass( Game, CopyableGame )

#------------------------------------------------------------------------------
class CopyablePlayer:
	def getStateToCopy(self, registry):
		d = self.__dict__.copy()
		del d['evManager']

		gID = id( self.game )
		d['game'] = gID
		registry[gID] = self.game

		charactorIDList = []
		for charactor in self.charactors:
			cID = id( charactor )
			charactorIDList.append( cID )
			registry[cID] = charactor
		d['charactors'] = charactorIDList

		return d

	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = 1

		self.name = stateDict['name']

		if not registry.has_key( stateDict['game'] ):
			print "Something is very wrong.should already be a game"
		else:
			self.game = registry[stateDict['game']]

		self.charactors = []
		for cID in stateDict['charactors']:
			if not registry.has_key( cID ):
				registry[cID] = Charactor( self.evManager )
				neededObjIDs.append( cID )
				success = 0
			else:
				self.charactors.append( registry[cID] )

		return [success, neededObjIDs]

MixInClass( Player, CopyablePlayer )

#------------------------------------------------------------------------------
class CopyableCharactor:
	def getStateToCopy(self, registry):
		d = self.__dict__.copy()
		del d['evManager']

		if self.sector is None:
			sID = None
		else:
			sID = id( self.sector )
		d['sector'] = sID
		registry[sID] = self.sector

		return d

	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = 1
		if stateDict['sector'] == None:
			self.sector = None
		elif not registry.has_key( stateDict['sector'] ):
			registry[stateDict['sector']] = Sector(self.evManager)
			neededObjIDs.append( stateDict['sector'] )
			success = 0
		else:
			self.sector = registry[stateDict['sector']]

		return [success, neededObjIDs]
		

MixInClass( Charactor, CopyableCharactor )

#------------------------------------------------------------------------------
# Copyable Sector is not necessary in this simple example because the sectors
# all get copied over in CopyableMap
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
class CopyableSector:
	def getStateToCopy(self, registry):
		return {}
		#d = self.__dict__.copy()
		#del d['evManager']
		#d['neighbors'][DIRECTION_UP] = id(d['neighbors'][DIRECTION_UP])
		#d['neighbors'][DIRECTION_DOWN] = id(d['neighbors'][DIRECTION_DOWN])
		#d['neighbors'][DIRECTION_LEFT] = id(d['neighbors'][DIRECTION_LEFT])
		#d['neighbors'][DIRECTION_RIGHT] = id(d['neighbors'][DIRECTION_RIGHT])
		return d

	def setCopyableState(self, stateDict, registry):
		return [1, []]
		#neededObjIDs = []
		#success = 1
		#if not registry.has_key( stateDict['neighbors'][DIRECTION_UP]):
			#neededObjIDs.append( stateDict['neighbors'][DIRECTION_UP] )
			#success = 0
		#else:
			#self.neighbors[DIRECTION_UP] = registry[stateDict['neighbors'][DIRECTION_UP]]
		#if not registry.has_key( stateDict['neighbors'][DIRECTION_DOWN]):
			#neededObjIDs.append( stateDict['neighbors'][DIRECTION_DOWN] )
			#success = 0
		#else:
			#self.neighbors[DIRECTION_DOWN] = registry[stateDict['neighbors'][DIRECTION_DOWN]]
		#if not registry.has_key( stateDict['neighbors'][DIRECTION_LEFT]):
			#neededObjIDs.append( stateDict['neighbors'][DIRECTION_LEFT] )
			#success = 0
		#else:
			#self.neighbors[DIRECTION_LEFT] = registry[stateDict['neighbors'][DIRECTION_LEFT]]
		#if not registry.has_key( stateDict['neighbors'][DIRECTION_RIGHT]):
			#neededObjIDs.append( stateDict['neighbors'][DIRECTION_RIGHT] )
			#success = 0
		#else:
			#self.neighbors[DIRECTION_RIGHT] = registry[stateDict['neighbors'][DIRECTION_RIGHT]]

		#return [success, neededObjIDs]

MixInClass( Sector, CopyableSector )
