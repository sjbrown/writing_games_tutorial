import pygame
from twisted.internet.selectreactor import SelectReactor
from twisted.spread import pb
from twisted.internet.main import installReactor
import pygame_test
import time

FRAMES_PER_SECOND = 4

class ReactorController(SelectReactor):
    def __init__(self):
        SelectReactor.__init__(self)
        connection = self.connectTCP('localhost', 8000, factory)
        pygame_test.prepare()
        installReactor(self)

    def doIteration(self, delay):
        print 'calling doIteration'
        SelectReactor.doIteration(self,delay)
        retval = pygame_test.iterate()
        if retval == False:
            thingInControl.stop()
            
        

class ReactorSlaveController(object):
    def __init__(self):
        self.keepGoing = True
        self.reactor = SelectReactor()
        installReactor(self.reactor)
        connection = self.reactor.connectTCP('localhost', 8000, factory)
        self.reactor.startRunning()
        self.futureCall = None
        self.futureCallTimeout = None
        pygame_test.prepare()
        
    def iterate(self):
        print 'in iterate'
        self.reactor.runUntilCurrent()
        self.reactor.doIteration(0)
        #t2 = self.reactor.timeout()
        #print 'timeout', t2
        #t = self.reactor.running and t2
        #self.reactor.doIteration(t)

    def run(self):
	clock = pygame.time.Clock()
        self.reactor.callLater(20, stupidTest)
        while self.keepGoing:
            timeChange = clock.tick(FRAMES_PER_SECOND)
            if self.futureCall:
                self.futureCallTimeout -= timeChange
                print 'future call in', self.futureCallTimeout
                if self.futureCallTimeout <= 0:
                    self.futureCall()
                    self.futureCallTimeout = None
                    self.futureCall= None
            retval = pygame_test.iterate()
            if retval == False:
                thingInControl.stop()
            self.iterate()

    def stop(self):
        print 'stopping'
        self.reactor.stop()
        self.keepGoing = False

    def callLater(self, when, fn):
        self.futureCallTimeout = when*1000
        self.futureCall = fn
        print 'future call in', self.futureCallTimeout


class LoopingCallController(object):
    def __init__(self):
        from twisted.internet import reactor
        from twisted.internet.task import LoopingCall
        self.reactor = reactor
        connection = self.reactor.connectTCP('localhost', 8000, factory)
        self.loopingCall = LoopingCall(self.iterate)
        pygame_test.prepare()

    def iterate(self):
        print 'looping call controller in iterate'
        retval = pygame_test.iterate()
        if retval == False:
            thingInControl.stop()

    def run(self):
        interval = 1.0 / FRAMES_PER_SECOND
        self.loopingCall.start(interval)
        self.reactor.run()

    def stop(self):
        self.reactor.stop()

    def callLater(self, when, fn):
        self.reactor.callLater(when, fn)

def stupidTest():
    print 'stupid test!'

server = None
def gotServer(serv):
    print '-'*79
    print 'got server', serv
    global server
    server = serv
    # stop in exactly 5 seconds
    thingInControl.callLater(65.0, stopLoop)

def stopLoop():
    print '-'*79
    print 'stopping the loop'
    thingInControl.stop()

factory = pb.PBClientFactory()
d = factory.getRootObject()
d.addCallback(gotServer)

import sys
if len(sys.argv) < 2:
    print 'usage: test.py 1|2|3'
    sys.exit(1)
elif sys.argv[1] == '1':
    thingInControl = ReactorController()
elif sys.argv[1] == '2':
    thingInControl = ReactorSlaveController()
else:
    thingInControl = LoopingCallController()

thingInControl.run()

print server

print 'end'
