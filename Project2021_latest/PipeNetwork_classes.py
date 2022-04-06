import numpy as np
import math
from copy import copy, deepcopy
from scipy.optimize import fsolve
import PyQt5.QtWidgets as qtw
import PyQt5.QtCore as qtc
import PyQt5.QtGui as qtg
import os

class nonSortingTreeItem(
    qtw.QTreeWidgetItem):  # this is called subclassing (i.e., make a sub class of qtw.QTreeWidgetItem)
    """
    I wanted to sort the top level loops ONLY (not the pipes themselves) in the tree_Loops, but the pipes of the loops
    were being sorted too.  So, I created this subclass to make the 'less than' operator of
    the item always return False and this prevents sorting of the pipes.  This is called 'ovrloading' an operator.
    The result of this that if a=nonSortingTreeItem() and b=nonSortingTreeItem() then a<b = False and b<a = False
    """

    def __lt__(self, other):
        return False

class Fluid:
    def __init__(self, mu=0.00089, rho=1000.0, SI=True):
        """
        default properties are for water
        :param mu: dynamic viscosity in Pa*s -> (kg*m/s^2)*(s/m^2) -> kg/(m*s) or (lb*s/ft^2)
        :param rho: density in kg/m^3
        :param SI: tells constructor if unit conversion is needed from english to si if SI==False
        """
        # (lb*s)/ft^2*((3.3ft/m)^2)*(1kg/2.2lb)*(9.81m/s^2)->(Pa*s)
        self.mu = mu if SI else mu * (3.3 ** 2) * (1 / 2.2) * 9.81
        # (lb/ft^3)*((3.3ft/m)^3)*(1kg/2.2lb) -> kg/m^3
        self.rho = rho if SI else rho * (3.3 ** 3) / 2.2
        self.nu = self.mu / self.rho  # kinematic viscosity in units of m^2/s

    def m_to_psi(self, p):
        # convert m of water to psi
        # (m)*(3.3*12in/m)*rho(kg/m^3)*(2.2lb/kg)*(1m/(3.3*12in))^3
        psi = p * self.rho * 2.2 / ((3.3 * 12) ** 2)
        return psi

    def psi_to_m(self, p):
        # convert psi to m of water
        # (lb/in^2)*(1kg/2.2lb)*(3.3*12in/m)^2*(1/rho)(m^3/kg)
        m = p * (1 / 2.2) * ((3.3 * 12) ** 2) * (1 / self.rho)
        return m

# $NEW$ 4/6/21 added a class for position of node
class Position():
    """
    I made this position for holding a position in 3D space (i.e., a point).  I've given it some ability to do
    vector arithmitic and vector algebra (i.e., a dot product).  I could have used a numpy array, but I wanted
    to create my own.  This class uses operator overloading as explained in the class.
    """

    def __init__(self, pos=None, x=None, y=None, z=None):
        """
        x, y, and z have the expected meanings
        :param pos: a tuple (x,y,z)
        :param x: float
        :param y: float
        :param z: float
        """
        # set default values
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        # unpack position from a tuple if given
        if pos is not None:
            self.x, self.y, self.z = pos
        # override the x,y,z defaults if they are given as arguments
        self.x = x if x is not None else self.x
        self.y = y if y is not None else self.y
        self.z = z if z is not None else self.z

    # region operator overloads $NEW$ 4/7/21
    # this is overloading the addition operator.  Allows me to add Position objects with simple math: c=a+b, where
    # a, b, and c are all position objects.
    def __add__(self, other):
        return Position((self.x + other.x, self.y + other.y, self.z + other.z))

    # this overloads the iterative add operator
    def __iadd__(self, other):
        if other in (float, int):
            self.x += other
            self.y += other
            self.z += other
            return self
        if type(other) == Position:
            self.x += other.x
            self.y += other.y
            self.z += other.z
            return self

    # this is overloading the subtract operator.  Allows me to subtract Positions. (i.e., c=b-a)
    def __sub__(self, other):
        return Position((self.x - other.x, self.y - other.y, self.z - other.z))

    # this overloads the iterative subtraction operator
    def __isub__(self, other):
        if other in (float, int):
            self.x -= other
            self.y -= other
            self.z -= other
            return self
        if type(other) == Position:
            self.x -= other.x
            self.y -= other.y
            self.z -= other.z
            return self

    # this is overloading the multiply operator.  Allows me to multiply a scalar or do a dot product (i.e., b=s*a or c=b*a)
    def __mul__(self, other):
        if type(other) in (float, int):
            return Position((self.x * other, self.y * other, self.z * other))
        if type(other) is Position:
            return Position((self.x * other.x, self.y * other.y, self.z * other.z))

    # this is overloading the __rmul__ operator so that s*Pt works.
    def __rmul__(self, other):
        return self * other

    # this is overloading the *= operator.  Same as a = Position((a.x*other, a.y*other, a.z*other))
    def __imul__(self, other):
        if type(other) in (float, int):
            self.x *= other
            self.y *= other
            self.z *= other
            return self

    # this is overloading the division operator.  Allows me to divide by a scalar (i.e., b=a/s)
    def __truediv__(self, other):
        if type(other) in (float, int):
            return Position((self.x / other, self.y / other, self.z / other))

    # this is overloading the /= operator.  Same as a = Position((a.x/other, a.y/other, a.z/other))
    def __idiv__(self, other):
        if type(other) in (float, int):
            self.x /= other
            self.y /= other
            self.z /= other
            return self

    def __round__(self, n=None):
        if n is not None:
            return Position(x=round(self.x, n), y=round(self.y, n), z=round(self.z, n))
        return self

    # endregion

    def set(self, strXYZ=None, tupXYZ=None):
        # set position by string or tuple
        if strXYZ is not None:
            cells = strXYZ.replace('(', '').replace(')', '').strip().split(',')
            x, y, z = float(cells[0]), float(cells[1]), float(cells[2])
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)
        elif tupXYZ is not None:
            x, y, z = tupXYZ  # [0], strXYZ[1],strXYZ[2]
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)

    def getTup(self):  # return (x,y,z) as a tuple
        return (self.x, self.y, self.z)

    def getStr(self, nPlaces=3):
        return '{}, {}, {}'.format(round(self.x, nPlaces), round(self.y, nPlaces), round(self.z, nPlaces))

    def mag(self):  # normal way to calculate magnitude of a vector
        return (self.x ** 2 + self.y ** 2 + self.z ** 2) ** 0.5

    def normalize(self):  # typical way to normalize to a unit vector
        l = self.mag()
        if l <= 0.0:
            return
        self.__idiv__(l)

    def normalize2D(self):
        self.z = 0.0
        self.normalize()

    def getAngleRad(self):
        """
        Gets angle of position relative to an origin (0,0) in the x-y plane
        :return: angle in x-y plane in radians
        """
        l = self.mag()
        if l <= 0.0:
            return 0
        if self.y >= 0.0:
            return math.acos(self.x / l)
        return 2.0 * math.pi - math.acos(self.x / l)

    def getAngleDeg(self):
        """
        Gets angle of position relative to an origin (0,0) in the x-y plane
        :return: angle in x-y plane in degrees
        """
        return 180.0 / math.pi * self.getAngleRad()

class units():
    def __init__(self, SI=True):
        self.set(SI)
        # conversion factors CF*SI=Eng
        self.CFFlowRate = 1.0 / 28.3168  # L/s to cfs
        self.CFLength = 3.3  # m to ft
        self.CFDiameter = 1000.0 / 25.4  # m to in
        self.CFPressure = (1000.0 / 25.4) / 27.7076  # m H20 to psi
        self.CFHeadLoss = 3.3 * 12.0  # m to in
        self.CFHead = 3.3 * 12.0  # m to in
        self.CFRough = 3.3 * 12.0  # m to in

    def set(self, SI=True):
        if SI:
            self.FlowRate = 'L/s'
            self.Length = 'm'
            self.Diameter = 'm'
            self.Pressure = 'm of H20'
            self.HeadLoss = 'm of H2O'
            self.Head = 'm of H2O'
            self.Rough = 'm'
        else:
            self.FlowRate = 'cfs'
            self.Length = 'ft'
            self.Diameter = 'in'
            self.Pressure = 'psi'
            self.HeadLoss = 'in of H2O'
            self.Head = 'in of H2O'
            self.Rough = 'in'

class pipeFitting():
    def __init__(self, type=None):
        self.type = "generic" if type is None else type

class Node:  # $NEW$ 4/6/21 got rid of z and added position variable
    def __init__(self, name=None, pipes=None, ext_flow=None, specifiedP=None, min_ph=None, position=None, fitting=None,
                 oldnode=None):
        """
        A node in a pipe network.
        :param name: name of the node
        :param pipes: a list/array of pipe objects connected to this node
        :param ext_flow: any external flow into (+) or out (-) of this node in L/s
        :param position: a position object
        """
        self.Name = name if oldnode is None else oldnode.getName()
        self.Pipes = pipes if oldnode is None else oldnode.Pipes
        self.E = 0.0 if oldnode is None else oldnode.E
        self.E = ext_flow if ext_flow is not None else self.E
        self.P = 0.0  # the pressure head at the node in m of fluid
        self.Loops = None
        self.SpecifiedP = 0.0 if oldnode is None else oldnode.SpecifiedP
        self.SpecifiedP = specifiedP if specifiedP is not None else self.SpecifiedP
        self.position = Position() if oldnode is None else oldnode.position
        self.position = position if position is not None else self.position
        self.IsSprinkler = False
        self.fitting = pipeFitting() if oldnode is None else oldnode.fitting
        self.fitting = fitting if fitting is not None else self.fitting
        self.K = 1.0
        self.MinPH = 0.0 if oldnode is None else oldnode.MinPH
        self.MinPH = min_ph if min_ph is not None else self.MinPH

    def getNetFlowRate(self):
        """
        Calculates the net flow rate into this node in L/s
        :return:
        """
        Qtot = self.E  # count the external flow first
        for p in self.Pipes:
            # retrieves the pipe flow rate (+) if into node (-) if out of node.  see class for pipe.
            Qtot += p.getFlowIntoNode(self.Name)
        return Qtot

    def getName(self):
        return self.Name

    def modifyNode(self, name=None, pipes=None, ext_flow=None, position=None, specifiedP=None, min_ph=None):
        if not name == None:
            self.Name = name
        if not pipes == None:
            self.Pipes = pipes
        if not ext_flow == None:
            self.E = ext_flow
        if not position == None:
            self.position = position
        if not specifiedP == None:
            self.SpecifiedP = specifiedP
        if not min_ph == None:
            self.MinPH = min_ph

    def setExtFlow(self, E, SI=True):
        # (ft^3/s)*(1m/3.3ft)^3*(1000L/m^3)->L/s
        self.E = E if SI else 1000 * E * (1 / 3.3) ** 3

class SprinklerHead(Node):  # $NEW$ 4/6/21 Like Node class, I added position as an argument and got rid of z.
    def __init__(self, name=None, pipes=None, ext_flow=None, position=None, specifiedP=None, min_ph=None, k=None,
                 oldnode=None, SI=True, fitting=None):
        """
        SprinklerHead inherits from node (i.e., it is a special kind of node).
        :param name: inherits
        :param pipes: inherits
        :param ext_flow: inherits
        :param position: a position object
        :param min_ph: minimum pressure head for sprinkler
        :param k: discharge coefficient k=Q/sqrt(P)
        :param oldnode: a node object that I want to copy properties from if it is specified
        """
        if oldnode != None:
            # if I pass an object from which to inherit properties.
            # run parent constructor
            super().__init__(oldnode=oldnode)
        else:
            # run parent constructor
            super().__init__(name=name, pipes=pipes, ext_flow=ext_flow, position=position, specifiedP=specifiedP,
                             min_ph=min_ph)
        self.E = ext_flow if ext_flow is not None else self.E
        self.setExtFlow(self.E, SI)
        self.position = position if position is not None else self.position
        self.fitting = fitting if fitting is not None else self.fitting
        self.minPH = min_ph if min_ph is not None else 2
        self.minPH = self.minPH if SI else self.minPH / 3.3
        self.K = 1.0 if oldnode is None else oldnode.K
        self.K = k if k is not None else self.K
        self.IsSprinkler = True

    def calc_k(self):  # calculate sprinkler discharge coefficient
        self.K = abs(self.E / math.sqrt(self.P))
        return self.K

    def calc_q(self):  # calculate outflow of sprinkler.  Warning: P should be positive to avoid error.
        self.E = self.K * math.sqrt(self.P)
        return self.E

class Pipe:
    def __init__(self, start='A', end='B', length=100.0, dia=200.0, roughness=0.00025, fluid=Fluid()):
        """
        Defines a generic pipe with orientation from lowest letter to highest.
        :param start: the start node
        :param end: the end node
        :param length: the pipe length in m
        :param dia: the pipe diameter in mm
        :param roughness: the pipe roughness in m
        :param SI: if SI==False, need to convert len, roughness from ft to m and dia from in to m
        """
        self.modifyPipe(start=start, end=end, length=length, dia=dia, roughness=roughness, fluid=fluid)

    def modifyPipe(self, start='A', end='B', length=100.0, dia=200.0, roughness=0.00025, fluid=Fluid()):
        self.startNode = min(start, end)  # makes sure to use the lowest letter for startNode
        self.endNode = max(start, end)  # makes sure to use the highest letter for the endNode
        self.setLength(length)
        self.setDiam(dia)
        self.setRough(roughness)
        self.Q = 10  # working in units of L/s.  Signed flow rate.
        self.fluid = fluid  # the fluid in the pipe
        self.vel = self.v()  # calculate the initial velocity of the fluid
        self.reynolds = self.Re()  # calculate the initial reynolds number

    def setDiam(self, dia):
        self.diam = dia / 1000.0  # pipe diameter in (m)

    def setRough(self, roughness):
        self.rough = roughness  # pipe roughness in (m)

    def setLength(self, length):
        self.length = length  # pipe length in (m)

    def v(self):
        """
        Calculate average velocity for self.Q
        :return: average velocity
        """
        A = math.pi / 4.0 * self.diam ** 2
        self.vel = (abs(self.Q) / 1000.0) / A  # need to convert Q to m^3/s
        return self.vel

    def Re(self):
        """
        Calculate the reynolds number under current conditions.
        :return:
        """
        self.reynolds = self.v() * self.diam / self.fluid.nu
        return self.reynolds

    def LaminarFrictionFactor(self, Re):
        return 64.0 / Re

    def BlasiusFrictionFactor(self, Re):
        return 0.316 * Re ** (-0.25)

    def ColebrookFrictionFactor(self, Re):
        relrough = self.rough / self.diam

        def ffc(ff):  # friction factor calculator
            LHS = 1 / (ff ** 0.5)
            RHS = -2.0 * math.log10(relrough / 3.7 + 2.51 / (Re * ff ** 0.5))
            return LHS - RHS

        f = fsolve(ffc, np.array([0.008]))  # use fsolve to find friction factor
        return f[0]

    def FrictionFactor(self):
        """
        $ 4/29/2021 Modified to include friction factor calculations
            when Re<2000 (laminar): f=64/Re
            when 3000<Re<4000 (Blasius): f=0.316*Re**(-0.25)
            when Re>5000 (Colebrook)
            Note1: if 2000<Re<3000, I will linearly interpolate between the laminar and Blasius values
            Note2:  math.log is natural log, math.log10 is base 10 log
        """
        Re = self.Re()
        if Re <= 2000.0:  # use laminar flow equation
            f = self.LaminarFrictionFactor(Re)
        elif Re > 2000.0 and Re < 3000.0:  # linear interpolation between laminar and Blasius
            x = (Re - 2000.0) / (1000.0)
            fl = self.LaminarFrictionFactor(Re)
            fb = self.BlasiusFrictionFactor(Re)
            f = fl + x * (fb - fl)
        elif Re >= 3000 and Re <= 4000:  # use Blasius equation
            f = self.BlasiusFrictionFactor(Re)
        else:  # use Colebrook equation for fully turbulent flow
            f = self.ColebrookFrictionFactor(Re)
        return f

    def FlowHeadLoss(self):
        """
        Use the Darcy-Weisbach equation to find the frictional head loss through a section of pipe.
        """
        g = 9.81  # m/s^2
        ff = self.FrictionFactor()
        hl = ff * (self.length / self.diam) * (self.v() ** 2) / (2 * g)  # m of water
        return hl

    def getFlowHeadLoss(self, s):
        """
        Calculate the head loss for the pipe in direction of loop traversal.
        :param s: the node i'm starting with in a traversal of the pipe
        :return: the signed headloss through the pipe in m of fluid
        """
        # while traversing a loop, if s = startNode I'm traversing in same direction as positive pipe flow
        nTraverse = 1 if s == self.startNode else -1
        # if flow is positive sense, scalar =1 else =-1
        nFlow = 1 if self.Q >= 0 else -1
        return nTraverse * nFlow * self.FlowHeadLoss()

    def getName(self):
        """
        Gets the pipe name.
        :return: pipe name (e.g., 'a-b')
        """
        return self.startNode + '-' + self.endNode

    def oContainsNode(self, node):
        # does the pipe connect to the node?
        return self.startNode == node or self.endNode == node

    def printPipeFlowRate(self, SI=True):
        q_units = 'L/s' if SI else 'cfs'
        q = self.Q if SI else self.Q / 1000 * (3.3 ** 3)
        print('Q {} = {:0.2f} {}'.format(self.getName(), q, q_units))

    def getPipeFlowRateOutput(self, SI=True, tabs='', tooltip=False, units=None):
        """
        $NEW$ 4/8/21 added the tooltip argument for returning in the format for a tooltip if True
        :param SI: boolean
        :param tabs: string
        :param tooltip: boolean
        :return: string
        """
        if units is not None:
            q_units = units.FlowRate
            q = self.Q if SI else units.CFFlowRate * self.Q
            return tabs + '{} {} {:0.2f} {}'.format(self.getName(), '->' if q >= 0.0 else '<-', abs(q),
                                                    q_units if tooltip else '')
        return "No units passed"

    def getFlowIntoNode(self, n):
        """
        determines the flow rate into node n
        :param n: a node object
        :return: +/-Q
        """
        return -self.Q if n == self.startNode else self.Q

class Loop():
    def __init__(self, Name='A', loopPipes=None):
        """
        Defines a loop in a pipe network.
        :param Name: name of the loop
        :param loopPipes: a list/array of pipe objects in this loop
        """
        self.name = Name
        self.pipes = loopPipes if not loopPipes == None else []

    def getName(self):
        return self.name

    def getPipes(self):
        return self.pipes

    def findCentroid(self, nodes):
        """
        $NEW$ 4/8/21 added this to find the centroid of nodes in the loop for placing the label.
        :param nodes: list of node objects
        :return:
        """
        nnn = self.pipes[0].startNode  # node name next (nnn)
        c = Position()  # for sum of all node coords
        for p in self.pipes:
            nnn = p.endNode if p.startNode == nnn else p.startNode
            c += (self.getNode(nodes=nodes, name=nnn)).position
        c /= len(self.pipes)  # divide by number of nodes/pipes
        return c

    def getNode(self, nodes, name):
        # get a node object from list of nodes by name
        return next(n for n in nodes if n.getName() == name)

    def getLoopHeadLoss(self, nodes):
        """
        Calculates the net head loss as I traverse around the loop, in m of fluid.
        Also, calculates pressure head at each node.
        :param nodes: pass along the list of nodes for the pipe network so I can find pressures at nodes
        :return:
        """
        deltaP = 0  # initialize loop pressure drop to zero
        sn_n = self.pipes[0].startNode  # name of node at the start of the first pipe
        sn_o = self.getNode(nodes, sn_n)  # get the stating node object
        ph = sn_o.P  # pressure head at startNode
        for p in self.pipes:
            # calculates the flow head loss in the pipe considering loop traversal and flow directions
            phl = p.getFlowHeadLoss(sn_n)
            # determine next node in the loop
            nn_n = p.endNode if p.startNode == sn_n else p.startNode
            # gets the node object at other end of current pipe
            nn_o = self.getNode(nodes, nn_n)
            # calculate head loss due to elevation change
            deltaZ = nn_o.position.z - sn_o.position.z  # $NEW$ 4/7/21 updated this to use position.z
            # update the loop head loss
            deltaP += (phl + deltaZ)
            # calc pressure head at end node
            ph -= (phl + deltaZ)
            # set pressure head at end node
            nn_o.P = ph
            # set ns node object to ne node object
            sn_o = nn_o
            # set start node (name) to the next node (name)
            sn_n = nn_n
        return deltaP

    def getLoopNodeNames(self):
        nodes = []
        nnn = self.pipes[0].startNode  # node name next (nnn)
        for p in self.pipes:
            nnn = p.endNode if p.startNode == nnn else p.startNode
            nodes += [nnn]
        return nodes

class PipeNetwork():
    def __init__(self, Pipes=None, Loops=None, Nodes=None, fluid=Fluid(), SI=True):
        """
        The pipe network is built from pipe, node, loop, and fluid objects.
        :param Pipes: a list of pipe objects
        :param Loops: a list of loop objects
        :param Nodes: a list of node objects
        :param fluid: a fluid object
        """
        self.pipes = Pipes if not Pipes == None else []
        self.loops = Loops if not Loops == None else []
        self.nodes = Nodes if not Nodes == None else []
        self.Fluid = fluid
        self.SI = SI
        self.units = units(self.SI)

    def getNodePipes(self, node):
        # returns a list of pipe objects that are connected to the node object
        l = [p for p in self.pipes if p.oContainsNode(node)]  # a list comprehension
        return l

    def setNodePipes(self):
        for n in self.nodes:
            n.Pipes = self.getNodePipes(n.getName())

    def setNodeLoops(self):
        for n in self.nodes:
            n.Loops = []
        for l in self.loops:
            nodes = l.getLoopNodeNames()
            for n in self.nodes:
                if n.getName() in nodes:
                    n.Loops += [l.getName()]

    def buildNodes(self):
        # automatically create the node objects by looking at the pipe ends
        for p in self.pipes:
            if self.hasNode(p.startNode) == False:
                # instantiate a node object and append it to the list of nodes
                self.nodes.append(Node(name=p.startNode))
            if self.hasNode(p.endNode) == False:
                # instantiate a node object and append it to the list of nodes
                self.nodes.append(Node(p.endNode))
        self.setNodePipes()
        self.setNodeLoops()
        # remove unused nodes $NEW$ 4/6/21
        for n in range(len(self.nodes) - 1, -1, -1):
            if self.nodes[n].Pipes is None or len(self.nodes[n].Pipes) == 0:
                self.nodes.pop(n)

        self.recalcPipeLengths()  # $NEW$ 4/6/21 new function to calculate pipe lengths based on node positions.

    # region Functions for evaluating the pipe network
    def findFlowRates(self):
        """
        A method to analyze the pipe network and find the flow rates in each pipe
        given the constraints of no net flow into a node and no net pressure drops in the loops.
        Here, the sprinkler min pressure is set to 2m and the output of each sprinkler head is fixed
        so that we can calculate the discharge coefficient for each sprinkler.
        :return: a list of flow rates in the pipes
        """
        # see how many nodes and loops there are
        N = len(self.nodes) + len(self.loops)
        # build an initial guess for flow rates
        Q0 = np.full(N, 5)
        self.iterations = 0

        def fn(q):  # the callback for fsolve
            # update the flow rate in each pipe object
            for i in range(len(self.pipes)):
                self.pipes[i].Q = q[i]
            # calculate the net head loss for the loop objects
            LHL = self.getLoopHeadLosses()
            # calculate the net flow rate for the node objects
            NFR = self.getNodeFlowRates()
            self.iterations += 1
            return LHL + NFR

        # using fsolve to find the flow rates
        FR = fsolve(fn, Q0)
        self.calcPressAtNonLoopNodes()
        return FR

    def findFlowRates2(self):
        """
        A method to analyze the pipe network and find the flow rates in each pipe.
        Given the constraints of: i) no net flow into a node, ii) no net pressure drop in the loops and
        iii) no mass accumulation in the pipe network.
        I used the last variable in q for the minimum sprinkler pressure.
        I found that setting this value at 2m, didn't allow system to converge, so I let fsolve
        vary the min sprinkler pressure and got convergence.
        :return: a list of flow rates in the pipes + other variables
        """
        # see how many nodes and loops there are +1 for network mass balance
        N = len(self.nodes) + len(self.loops) + 1
        # build an initial guess for flow fsolve variables
        Q0 = np.full(N, 1)
        self.iterations = 0

        def fn(q):  # the callback for fsolve
            # update the flow rate in each pipe object
            for i in range(len(self.pipes)):
                self.pipes[i].Q = q[i]

            # calculate the net head loss for the loop objects
            LHL = self.getLoopHeadLosses()
            # update the sprinkler flow rates and calculate net outflow for the network
            minP = abs(q[len(q) - 1])  # allows fsolve to set min sprinkler pressure
            NFO = self.getNetOutFlow(minP)
            # calculate the net flow rate for the node objects
            NNF = self.getNodeFlowRates()
            self.iterations += 1
            return NFO + LHL + NNF

        # using fsolve to find the flow rates
        FR = fsolve(fn, Q0, factor=1000)
        NFO = self.getNetOutFlow(setmin=False)  # debugging check
        return FR

    def getNetOutFlow(self, minP=2.0, setmin=True):
        """
        Calculate the mass balance for the pipe network.
        :param minP: the minimum pressure head at a sprinkler in (m).
        :param setmin: if True, set min pressure for sprinkler by increasing pump pressure.
        :return: [net mass balance]
        """
        if setmin:
            self.setMinNodePressureHead(minP, calcK=False)
        netOut = 0
        for n in self.nodes:
            if n.IsSprinkler:
                n.E = -1.0 * n.K * math.sqrt(n.P)
            netOut += n.E
        return [netOut]

    def getNodeFlowRates(self):
        # each node object is responsible for calculating its own net flow rate
        fr = [n.getNetFlowRate() for n in self.nodes]
        return fr

    def getLoopHeadLosses(self):
        # each loop object is responsible for calculating its own net head loss
        for N in self.nodes:
            N.P = 0
        lhl = [l.getLoopHeadLoss(self.nodes) for l in self.loops]
        return lhl

    def calcPressAtNonLoopNodes(self):
        for n in self.nodes:  # scan across all nodes.  Nodes in a loop already accurately calculated
            if len(n.Loops) == 0:  # non-loop node identified
                # a non-loop node is connected to a loop by a riser pipe.
                # pressure at non-loop node is pressure at loop node - flow head loss - elevation head loss
                z = n.position.z  # elevation of the node (i.e., sprinkler head)
                p = n.Pipes[0]  # get pipe connected to node
                nnn = n.getName()  # the name of the node
                fhl = p.getFlowHeadLoss(nnn)  # flow head loss assuming flow away from node
                nnn = p.endNode if p.startNode == nnn else p.startNode
                nno = self.getNode(nnn)
                # n.P+ehl+fhl=nno.P -> n.P=nno.P-ehl-fhl
                ehl = z - nno.position.z  # head loss due to elevation change
                n.P = nno.P - fhl - ehl  # pressure at the non-loop node

    def setMinNodePressureHead(self, minPH, calcK=True):
        """
        Assuming we have calculated the pressure head at each node in the calculation of loop pressure drops,
        where we set ph at node 'a'=0, we can set the minPH specified at a node or sprinkler in the system.
        :param minPH:
        :param calcK:  determines if I should calc K values for sprinklers
        :return:
        """
        delta = minPH  # calculate how much we need to up the pressure head at the pump
        for n in self.nodes:  # look for minimum sprinkler pressure head
            if n.IsSprinkler:
                delta = max(delta, n.MinPH - n.P)
            elif n.SpecifiedP > 0.0:
                delta = max(delta, n.SpecifiedP - n.P)
        # dial up the pump pressure/node pressure
        for n in self.nodes:
            n.P += delta
            if n.IsSprinkler and calcK:  # if called for, calculate discharge coefficient of sprinklers
                n.calc_k()

    def setRefPressure(self, RefP=0.0, nodeName='a'):
        deltaP = RefP - self.getNode(nodeName).P
        for n in self.nodes:
            n.P += deltaP

    def recalcPipeLengths(self):
        """
        When altering the elevation of the nodes in the pipe network, I make the assumption that
        the pipe connecting two nodes is a straight piece of pipe, now at an angle relative
        to the horizontal.  So calculate the new length of that pipe.
        The other option would be to assume a vertical riser and simply add on the length of the
        riser to the length of pipe.  $NEW$ 4/6/21 updated this to calculate length based on node positions
        :return: length of the new pipe
        """
        for p in self.pipes:
            n1 = self.getNode(p.startNode).position
            n2 = self.getNode(p.endNode).position
            c = n2 - n1
            p.length = c.mag()

    # endregion

    # region Functions to determine existance of Node, Pipe, or Loop by passing name
    def hasPipe(self, name):
        # determines if this pipe exists in the list of pipes
        return any(x.getName() == name for x in self.pipes)

    def hasLoop(self, name):
        # determines if this pipe exists in the list of pipes
        return any(x.getName() == name for x in self.loops)

    def hasNode(self, name):
        # determines if I have already constructed this node object (by name)
        return any(x.getName() == name for x in self.nodes)

    # endregion

    # region functions to get Node, Pipe, or Loop objects by passing name
    def getNode(self, name):
        return next(x for x in self.nodes if x.getName() == name)

    def getPipe(self, name):
        # returns a pipe object by its name
        return next(p for p in self.pipes if p.getName() == name)

    def getLoop(self, name):
        # returns a loop object by its name
        return next(l for l in self.loops if l.getName() == name)

    # endregion

    # region functions to get Node, Pipe or Loop index by passing name
    def getNodeIndex(self, name):
        """
        This way of searching a list of objects uses enumerate to return
        both the index in the list and the object from the list.  We can
        compare the object name property to the target name and return the
        index value for the object with the desired property.
        :param name:
        :return:
        """
        I = next(i for i, x in enumerate(self.nodes) if x.getName() == name)
        return I

    def getPipeIndex(self, name):
        """
        This way of searching a list of objects uses enumerate to return
        both the index in the list and the object from the list.  We can
        compare the object name property to the target name and return the
        index value for the object with the desired property.
        :param name:
        :return:
        """
        I = next(i for i, x in enumerate(self.pipes) if x.getName() == name)
        return I

    def getLoopIndex(self, name):
        """
        This way of searching a list of objects uses enumerate to return
        both the index in the list and the object from the list.  We can
        compare the object name property to the target name and return the
        index value for the object with the desired property.
        :param name:
        :return:
        """
        I = next(i for i, x in enumerate(self.loops) if x.getName() == name)
        return I
    # endregion

class PipeNetworkController():
    def __init__(self):
        self.Model = PipeNetwork()
        self.View = PipeNetworkView()
        self.rdo_SI = qtw.QRadioButton()

    def EvaluatePipeNetwork(self):
        self.Model.findFlowRates()

        # search the nodes and find the minimum pressure head needed in the system.
        # minPH=2
        # for n in self.Model.nodes:
        #     minPH=max(minPH,n.SpecifiedP,n.MinPH)
        self.Model.setMinNodePressureHead(minPH=0.0, calcK=True)

        self.updateView()

    def setUnits(self):
        self.Model.SI = self.rdo_SI.isChecked()
        self.Model.units.set(self.Model.SI)
        self.updateView()

    # region Functions to add, delete or modify Nodes, Pipes or Loops by passing QTreeWidget item
    def addPipe(self, item):
        PN = self.Model
        if type(item) is tuple:
            self.addPipe_TupleItem(item)
        elif type(item) is Pipe:
            TF = PN.hasPipe(item.getName())
            if TF:
                p = PN.getPipe(item.getName())
                p.length = float(item.length)
                p.diam = float(item.diam)
                p.modifyPipe(start=p.startNode, end=p.endNode, length=float(p.length), dia=float(p.diam),
                             roughness=float(p.rough),
                             fluid=Fluid(), SI=PN.SI)
            else:
                PN.pipes.append(item)
        PN.buildNodes()  # makes new node if needed
        PN.setNodePipes()
        self.updateView()

    def addPipe_TupleItem(self, item):
        stNn, enNn = item[0].split('-')
        PN = self.Model
        # get conversion factors for later
        cfLen = 1.0 if PN.SI else PN.units.CFLength
        cfDia = 1.0 if PN.SI else PN.units.CFDiameter / 1000.0
        cfRough = 1.0 if PN.SI else PN.units.CFRough

        p = Pipe(start=stNn, end=enNn, dia=float(item[2]) / cfDia, roughness=float(item[3]) / cfRough)
        self.addPipe(p)

    def addLoop(self, item):
        PN = self.Model
        if type(item) is qtw.QTreeWidgetItem:
            self.modifyLoop(item)
        elif type(item) is Loop:
            PN.loops.append(item)
        self.updateView()

    def deletePipe(self):
        PN = self.Model
        table = self.View.tablePipes
        row = table.currentRow()
        name = table.item(row, 0).text()
        if PN.hasPipe(name):
            PN.pipes.pop(PN.getPipeIndex(name))
        table.removeRow(row)
        PN.buildNodes()  # $NEW$ 4/6/21 might need to delete unused nodes
        self.updateView()

    def deleteLoop(self, item):
        PN = self.Model
        name = item.text(0)
        if PN.hasLoop(name):
            PN.loops.pop(PN.getLoopIndex(name))
        self.updateView()

    def deleteNode(self, item):
        PN = self.Model
        name = item.text()  # expecting a QTableWidgetItem
        if PN.hasNode(name):
            PN.nodes.pop(PN.getNodeIndex(name))
        self.updateView()

    def modifyPipe(self):
        """
        This one modifies (typical) or creates a pipe in the pipe network from the pipe table of the gui.
        """
        table = self.View.tablePipes
        PN = self.Model  # short name for the model
        # get conversion factors for later
        cfLen = 1.0 if PN.SI else PN.units.CFLength
        cfDia = 1.0 if PN.SI else PN.units.CFDiameter
        cfRough = 1.0 if PN.SI else PN.units.CFRough
        itm = table.currentItem()
        # all items in pipe table are just QTableWidgetItem types (i.e., just text)
        row = itm.row()
        cols = table.columnCount()
        p = [table.item(row, c).text() for c in range(cols)]
        name, length, diam, rough = p  # unpack p to useful names
        length = float(length) / cfLen  # convert to m
        diam = float(diam) * 1000.0 / cfDia  # convert to mm
        rough = float(rough) / cfRough  # convert to m
        nodes = name.split('-')
        stNode = nodes[0]
        enNode = nodes[1]
        TF = PN.hasPipe(name)
        if TF:
            p = PN.getPipe(name)
            p.length = float(length)
            p.diam = float(diam)
            p.modifyPipe(start=stNode, end=enNode, length=float(length), dia=float(diam), roughness=float(rough),
                         fluid=Fluid())
        else:
            PN.pipes.append(
                Pipe(start=stNode, end=enNode, length=float(length), dia=float(diam), roughness=float(rough),
                     fluid=Fluid()))
        PN.buildNodes()
        self.updateView()

    def modifyNode(self, item=None, **kwargs):
        if type(item) is qtw.QTableWidget:
            self.modifyNode_TableItem()
        else:  # this is mostly used for cli rather than gui.  No fittings in this one.
            PN = self.Model
            name = kwargs.get('name')
            TF = PN.hasNode(name)  # existing (True) or new (False) node
            if TF:
                oldnode = PN.getNode(name)
                index = PN.getNodeIndex(name)
                if kwargs.get('makesprinkler'):
                    extFlow = kwargs.get('ext_flow')
                    minPH = kwargs.get('min_ph')
                    position = kwargs.get('position')
                    PN.nodes[index] = SprinklerHead(oldnode=oldnode, ext_flow=extFlow, position=position, min_ph=minPH)
                else:
                    extFlow = kwargs.get('ext_flow')
                    specPH = kwargs.get('specified_PH')
                    position = kwargs.get('position')
                    PN.nodes[index] = Node(oldnode=oldnode, ext_flow=extFlow, position=position, specifiedP=specPH)
            else:
                if kwargs.get('makesprinkler'):
                    extFlow = kwargs.get('ext_flow')
                    minPH = kwargs.get('min_ph')
                    position = kwargs.get('position')  # $NEW$ 4/7/21 updated to use position keyword
                    PN.nodes.append(Node(name=name, ext_flow=extFlow, position=position, min_ph=minPH))
                else:
                    extFlow = kwargs.get('ext_flow')
                    specPH = kwargs.get('specified_PH')
                    position = kwargs.get('position')  # $NEW$ 4/7/21 updated to use position keyword
                    PN.nodes.append(Node(name=name, ext_flow=extFlow, position=position, specifiedP=specPH))
        self.updateView()

    def modifyNode_TableItem(self):
        """
        This function modifies a node that gets edited in a table.
        The node is identified by name and all properties are on one row of the table.
        Most of the cell items are just text, but the Sprinkler? is a cell widget item (QCheckBox)
        and the fitting is a cell widget item (QComboBox).
        """
        table = self.View.table_Nodes
        PN = self.Model  # quick name for the model
        # set up some conversion factors.  All data stored in model is in metric units.
        cfLen = 1.0 if PN.SI else PN.units.CFLength
        cfQ = 1.0 if PN.SI else PN.units.CFFlowRate
        cfP = 1.0 if PN.SI else PN.units.CFPressure

        itm = table.currentItem()
        row = -1
        if itm is not None:  # behavior if a cell in the table is the item (QTableWidgetItem)
            row = itm.row()
        else:  # behavior if a cell widget (i.e., check box or combo box) is causing the action
            pos = table.focusWidget().pos()  # gets current widget in focus
            ind = table.indexAt(pos)  # gets index (row, col) of widget
            row = ind.row()
        if row < 0:  # make sure row >= 0
            return

        # now that I have the row, scan across all the columns of the row to set node properties
        cols = table.columnCount()
        p = []
        for c in range(cols):
            if table.item(row, c) is not None:  # cells with a widget (check box or combobox) have None for cell item
                p += [table.item(row, c).text()]  # just get text of the cell
            elif table.cellWidget(row, c) is not None:  # a cell widget exists
                w = table.cellWidget(row, c)  # get the cell widget
                if isinstance(w, qtw.QCheckBox):  # is it a QCheckBox?
                    p += [str(w.isChecked())]  # get bool string
                elif isinstance(w, qtw.QComboBox):  # is it a QComboBox?
                    p += [str(w.currentText())]  # get string of current text

        # Unpack elements of p with useful names
        name, x, y, z, extflow, issprinkler, fittingType, minph = p

        if issprinkler.lower().strip() == 'true':
            N = SprinklerHead(name=name, ext_flow=float(extflow), fitting=pipeFitting(fittingType),
                              min_ph=float(minph) if not minph.lower().strip() == 'none' else None)
        else:
            N = Node(name=name, ext_flow=float(extflow), fitting=pipeFitting(fittingType),
                     specifiedP=float(minph) if not minph.lower().strip() == 'none' else None)
        N.position.set(tupXYZ=(float(x), float(y), float(z)))
        # do unit conversions if needed
        N.position = round(N.position / cfLen, 2)
        N.E = round(N.E / cfQ, 2)
        N.SpecifiedP = round(N.SpecifiedP / cfP, 3)
        N.MinPH = round(N.MinPH / cfP, 3)
        N.Pipes = PN.getNodePipes(N.getName())

        TF = PN.hasNode(N.getName())  # new or existing node?
        if TF:
            i = PN.getNodeIndex(N.getName())
            PN.nodes[i] = N
        else:
            PN.nodes.append(N)
        PN.recalcPipeLengths()
        self.updateView()

    def modifyLoop(self, item, col=0):
        """
        Generally, the item passed is a tree with a trunk of a node name and leaves of pipe names
        :param item: a tree widget item
        :param col: the col that was modified
        :return: nothing
        """
        PN = self.Model
        i = item
        loopname = item.text(0)
        pipes = []
        for c in range(item.childCount()):
            pipes.append(PN.getPipe(item.child(c).text(0)))
        L = Loop(Name=loopname, loopPipes=pipes)
        TF = PN.hasLoop(loopname)
        if TF:
            i = PN.getLoopIndex(loopname)
            PN.loops[i] = L
        else:
            PN.loops.append(L)
        self.updateView()

    # endregion

    # region Functions responsible for importing/building objects from a data file
    def importPipeNetwork(self, data, PN=PipeNetwork()):
        """
        Build a pipe network from a data file
        :param data: a list of lines from a file.  Lines starting with # are comments to be ignored
        :return:
        """
        i = 0
        PN.pipes.clear()
        PN.nodes.clear()
        PN.loops.clear()
        while i < len(data):
            L = '' + data[i]
            L = L.lower().strip()
            # read in a pipe
            if L.find('#') == 0:
                n = 1
                pass
            elif L.find('pipe') >= 0:
                # read in a pipe and increase i to end of pipe section
                i = self.importPipe(data, i, PN)
                pass
            elif L.find('loop') >= 0:
                i = self.importLoop(data, i, PN)
                pass
            elif L.find('node') >= 0:
                i = self.importNode(data, i, PN)
            elif L.find('fluid') >= 0:
                i = self.importFluid(data, i, PN)
                pass
            elif L.find('network') >= 0:
                i = self.importUnits(data, i, PN)
                pass
            i += 1
        PN.buildNodes()
        self.updateView()

    def importPipe(self, data, j, PN=PipeNetwork()):
        """
        Read in a pipe from the data that comes from a file
        :param data: the list of strings from reading a file
        :param j: an index value for the list where the pipe definition starts
        :return: an index value for where the pipe definition ends
        """
        j += 1
        L = data[j].lower()
        P = Pipe(fluid=PN.Fluid)
        while L.find('/pipe') == -1:
            cells = data[j].split(':')
            if cells[0].lower().find('nodes') >= 0:
                nodes = cells[1].replace('(', '').replace(')', '').strip().split(',')
                P.startNode = nodes[0]
                P.endNode = nodes[1]
            elif cells[0].lower().find('length') >= 0:
                P.setLength(float(cells[1].strip()))
            elif cells[0].lower().find('dia') >= 0:
                P.setDiam(float(cells[1].strip()))
            elif cells[0].lower().find('rough') >= 0:
                P.setRough(float(cells[1].strip()))
            j += 1
            L = data[j].lower()
        if not PN.hasPipe(P.getName()):
            PN.pipes.append(P)
        return j

    def importLoop(self, data, j, PN=PipeNetwork()):
        """
        Read in a loop from the data that comes from a file
        :param data: the list of strings from reading a file
        :param j: an index value for the list where the loop definition starts
        :return: an index value for where the loop definition ends
        """
        j += 1
        L = data[j].lower()
        Lp = Loop()
        while L.find('/loop') == -1:
            cells = data[j].split(':')
            if cells[0].lower().find('pipes') >= 0:
                cells = cells[1].split(',')
                for c in cells:
                    Lp.pipes.append(PN.getPipe(c.strip().replace("'", '')))
            elif cells[0].lower().find('name') >= 0:
                Lp.name = cells[1].strip()
            j += 1
            L = data[j].lower()
        if not PN.hasLoop(Lp.getName()):
            PN.loops.append(copy(Lp))
        return j

    def importFluid(self, data, j, PN=PipeNetwork()):
        """
        Read in a fluid from the data that comes from a file
        :param data: the list of strings from reading a file
        :param j: an index value for the list where the fluid definition starts
        :return: an index value for where the fluid definition ends
        """
        j += 1
        L = data[j].lower()
        f = Fluid(SI=PN.SI)
        while L.find('/fluid') == -1:
            cells = data[j].split(':')
            if cells[0].lower().find('mu') >= 0:
                f.mu = float(cells[1].strip())
            elif cells[0].lower().find('rho') >= 0:
                f.rho = float(cells[1].strip())
            j += 1
            L = data[j].lower()
        PN.Fluid = f
        return j

    def importUnits(self, data, j, PN=PipeNetwork()):
        """
        Read in a loop from the data that comes from a file
        :param data: the list of strings from reading a file
        :param j: an index value for the list where the loop definition starts
        :return: an index value for where the loop definition ends
        """
        j += 1
        L = data[j].lower()
        while L.find('/network') == -1:
            cells = data[j].split(':')
            if cells[0].lower().find('units') >= 0:
                PN.SI = cells[1].strip().lower() == 'si'
            j += 1
            L = data[j].lower()
        return j

    def importNode(self, data, j, PN=PipeNetwork()):
        """
        Read in a node from the data that comes from a file
        :param data: the list of strings from reading a file
        :param j: an index value for the list where the node definition starts
        :return: an index value for where the node definition ends
        """
        j += 1
        L = data[j].lower()
        N = Node()
        isSprinkler = False  # assume not a sprinkler at first
        while L.find('/node') == -1:
            cells = data[j].split(':')
            if cells[0].lower().find('name') >= 0:
                N.Name = cells[1].strip()
            elif cells[0].lower().find('sprinkler') >= 0:
                isSprinkler = cells[1].strip().lower() == 'true'
            elif cells[0].lower().find('ext') >= 0:
                N.E = float(cells[1].strip())
            elif cells[0].lower().find('minp') >= 0:
                N.MinPH = float(cells[1].strip())
            elif cells[0].lower().find('specified') >= 0:
                N.SpecifiedP = float(cells[1].strip())
            elif cells[0].lower().find('position') >= 0:  # $NEW$ 4/6/21 for reading in position from file
                N.position.set(strXYZ=cells[1])
            elif cells[0].lower().find('fitting') >= 0:
                N.fitting = pipeFitting(cells[1].strip())
            j += 1
            L = data[j].lower()
        if not PN.hasNode(N.Name):
            N.Pipes = PN.getNodePipes(N.Name)
            PN.nodes.append(N)
        else:
            PN.getNode(N.Name).modifyNode(ext_flow=N.E, position=N.position, specifiedP=N.SpecifiedP, min_ph=N.MinPH)
        if isSprinkler:  # may need to convert a node to a sprinkler head
            if PN.getNode(N.Name).IsSprinkler == False:
                n = PN.getNodeIndex(N.Name)
                PN.nodes[n] = SprinklerHead(oldnode=PN.getNode(N.Name))
        return j

    # endregion

    # region functions interacting with View
    def setViewWidgets(self, w):
        """
        Set the gui widgets that view will update
        :param w: a tuple of widgets
        :return: nothing
        """
        self.View.setViewWidgets(w)

    def updateView(self):
        self.View.updateView(PN=self.Model)
        # need to set signals and slots for NodeTable
        for r in range(self.View.table_Nodes.rowCount()):
            for c in range(self.View.table_Nodes.rowCount()):
                w = self.View.table_Nodes.cellWidget(r, c)
                if isinstance(w, qtw.QCheckBox):
                    w.stateChanged.connect(self.modifyNode_TableItem)
                elif isinstance(w, qtw.QComboBox):
                    w.currentTextChanged.connect(self.modifyNode_TableItem)

    def printOutput(self):
        self.View.printPipeFlowRates(self.Model)
        self.View.printPipeHeadLoss(self.Model)
        self.View.printNodeHead(self.Model)
        self.View.printLoopHeadLoss(self.Model)
        self.View.printNetNodeFlows(self.Model)
    # endregion

class PipeNetworkView():
    def __init__(self):
        self.pipeHighlights = []

        # region setup pens and brushes and scene
        # make the pens first
        # a thick darkGray pen
        self.penPipe = qtg.QPen(qtc.Qt.darkGray)
        self.penPipe.setWidth(4)
        # a medium darkBlue pen
        self.penNode = qtg.QPen(qtc.Qt.darkBlue)
        self.penNode.setStyle(qtc.Qt.SolidLine)
        self.penNode.setWidth(1)
        # a pen for the grid lines
        self.penGridLines = qtg.QPen()
        self.penGridLines.setWidth(1)
        # I wanted to make the grid lines more subtle, so set alpha=25
        self.penGridLines.setColor(qtg.QColor.fromHsv(197, 144, 228, alpha=50))
        # now make some brushes
        # build a brush for filling with solid red
        self.brushFill = qtg.QBrush(qtc.Qt.darkRed)
        # a brush that makes a hatch pattern
        self.brushNode = qtg.QBrush(qtg.QColor.fromCmyk(0, 0, 255, 0, alpha=100))
        # a brush for the background of my grid
        self.brushGrid = qtg.QBrush(qtg.QColor.fromHsv(87, 98, 245, alpha=128))
        # Finally, the scene where pipe network objects are drawn
        self.scene = qtw.QGraphicsScene()
        # endregion

    #region setup functions
    def setViewWidgets(self, w):
        """
        Gets a tuple of widgets and makes them part of the view
        :param w: a tuple of widgets
        :return:
        """
        #unpack the tuples
        self.tree_Loops, self.table_Pipes, self.table_Nodes, self.tree_LoopPipes, self.lbl_PipeHeadLosses, \
        self.lbl_NodePressures, self.lbl_FlowRates, self.lbl_PressureAndFlowChecks, self.lbl_Diam, \
        self.le_Diam, self.lbl_Rough, self.le_Roughness=w

    #endregion

    # region Functions to display on GUI
    def updatePipeTable(self, PN=None):
        table = self.table_Pipes
        table.blockSignals(True)
        table.setSortingEnabled(False)
        table.clear()
        header = ['Name', 'Length ({})'.format(PN.units.Length)]
        header += ['Diam ({})'.format(PN.units.Diameter)]
        header += ['Rough ({})'.format(PN.units.Rough)]
        table.setRowCount(len(PN.pipes))
        table.setHorizontalHeaderLabels(header)
        row = 0
        for p in PN.pipes:
            l = "{:0.2f}".format(p.length if PN.SI else PN.units.CFLength * p.length)
            d = "{:0.3f}".format(p.diam if PN.SI else PN.units.CFDiameter * p.diam)
            r = "{:0.5f}".format(p.rough if PN.SI else PN.units.CFRough * p.rough)
            txt = (p.getName(), l, d, r)
            for c in range(len(txt)):
                if c != 1:
                    itm = qtw.QTableWidgetItem(txt[c])
                    itm.setFlags(
                        qtc.Qt.ItemIsSelectable | qtc.Qt.ItemIsEditable | qtc.Qt.ItemIsDragEnabled | qtc.Qt.ItemIsEnabled)
                else:
                    itm = qtw.QTableWidgetItem(txt[1])
                    itm.setFlags(qtc.Qt.ItemIsSelectable | qtc.Qt.ItemIsDragEnabled)
                table.setItem(row, c, itm)
            row += 1
        table.setSortingEnabled(True)
        table.blockSignals(False)

    def updateNodeTable(self, PN=None):
        table = self.table_Nodes
        table.blockSignals(True)
        table.setSortingEnabled(False)
        table.clear()
        PN.buildNodes()
        table.setRowCount(len(PN.nodes))
        itm = ['Name']
        itm += ['x ({})'.format(PN.units.Length)]
        itm += ['y ({})'.format(PN.units.Length)]
        itm += ['z ({})'.format(PN.units.Length)]
        itm += ['Q ({})'.format(PN.units.FlowRate)]
        itm += ['Sprinkler?']
        itm += ['Type']
        itm += ['P ({})'.format(PN.units.Pressure)]
        table.setColumnCount(len(itm))
        table.setHorizontalHeaderLabels(itm)
        r = 0
        for n in PN.nodes:
            x = "{:0.2f}".format(n.position.x if PN.SI else n.position.x * PN.units.CFLength)
            y = "{:0.2f}".format(n.position.y if PN.SI else n.position.y * PN.units.CFLength)
            z = "{:0.2f}".format(n.position.z if PN.SI else n.position.z * PN.units.CFLength)
            Q = "{:0.3f}".format(n.E if PN.SI else n.E * PN.units.CFFlowRate)
            type = n.fitting.type
            minPH = "{:0.2f}".format(n.MinPH if PN.SI else n.MinPH * PN.units.CFPressure)
            pSpec = "{:0.2f}".format(n.SpecifiedP if PN.SI else n.SpecifiedP * PN.units.CFPressure)
            strs = (n.getName(), x, y, z, Q, str(n.IsSprinkler), type, minPH if n.IsSprinkler else pSpec)
            for c in range(len(strs)):
                itm = qtw.QTableWidgetItem(strs[c])
                # itm.setFlags(qtc.Qt.ItemIsSelectable | qtc.Qt.ItemIsEditable | qtc.Qt.ItemIsDragEnabled  | qtc.Qt.ItemIsEnabled)
                table.setItem(r, c, itm)

            # make checkbox for IsSprinkler
            itm = qtw.QCheckBox()
            itm.setChecked(n.IsSprinkler)
            itm.setText(str(itm.isChecked()))
            table.setItem(r, 5, None)
            table.setCellWidget(r, 5, itm)
            # make combobox for Fitting
            itm = qtw.QComboBox()
            itm.addItems(['elbow', 'reducing elbow', 'tee', 'reducing tee', 'coupler', 'reducing coupler', 'n-way',
                          'reducing n-way'])
            ind = itm.findText(n.fitting.type.strip())
            if ind >= 0:
                itm.setCurrentIndex(ind)
            table.setItem(r, 6, None)
            table.setCellWidget(r, 6, itm)
            r += 1
        table.setSortingEnabled(True)
        table.blockSignals(False)

    def updateLoopTree(self, PN=None):
        """
        The loop tree is a little different than the other in that it involves parents (i.e., the loop)
        and children (i.e., the pipes of the loop)
        :param tree:
        :param PN:
        :return:
        """
        tree = self.tree_Loops
        tree.clear()
        for l in PN.loops:
            loopName = [l.getName()]
            pipes = l.getPipes()
            loop = qtw.QTreeWidgetItem(loopName)
            loop.setFlags(
                qtc.Qt.ItemIsSelectable | qtc.Qt.ItemIsEditable | qtc.Qt.ItemIsDragEnabled | qtc.Qt.ItemIsUserCheckable | qtc.Qt.ItemIsEnabled)
            for p in pipes:
                itm = nonSortingTreeItem([p.getName()])
                itm.setFlags(
                    qtc.Qt.ItemIsSelectable | qtc.Qt.ItemIsEditable | qtc.Qt.ItemIsDragEnabled | qtc.Qt.ItemIsUserCheckable | qtc.Qt.ItemIsEnabled)
                loop.addChild(itm)
            tree.addTopLevelItem(loop)

    def fitColumns(self):
        for i in range(self.table_Pipes.columnCount()):
            self.table_Pipes.resizeColumnToContents(i)
        for i in range(self.table_Nodes.columnCount()):
            self.table_Nodes.resizeColumnToContents(i)
        for i in range(self.tree_Loops.columnCount()):
            self.tree_Loops.resizeColumnToContents(i)
        for i in range(self.tree_LoopPipes.columnCount()):
            self.tree_LoopPipes.resizeColumnToContents(i)

    # region functions for drawing the pipe network
    def updateView(self, PN=None):
        self.updatePipeTable(PN=PN)
        self.updateNodeTable(PN=PN)
        self.updateLoopTree(PN=PN)

        self.lbl_Diam.setText('Diam ({})'.format('mm' if PN.SI else 'in'))
        self.lbl_Rough.setText('Roughness ({})'.format('m' if PN.SI else 'in'))

        self.fitColumns()
        self.getPipeFlowRatesOutputSorted(tabs='', PN=PN)
        self.getPipeHeadLossesOutputSorted(tabs='', PN=PN)
        self.getNodeHeadOutputSorted(tabs='', PN=PN)
        self.getRealityCheckOutputSorted(tabs='', PN=PN)
        self.buildScene(PN=PN)

    def buildScene(self, PN=None):
        # clear out the old scene first
        self.scene.clear()

        # draw a grid
        self.drawAGrid(DeltaX=10, DeltaY=10, Height=400, Width=400)
        # draw the pipe network
        self.drawPipes(PN=PN)
        self.drawNodes(PN=PN)
        self.drawLoopLabels(PN=PN)

    def drawAGrid(self, DeltaX=10, DeltaY=10, Height=200, Width=200, CenterX=0, CenterY=0):
        """
        This makes a grid for reference.  No snapping to grid enabled.
        :param DeltaX: grid spacing in x direction
        :param DeltaY: grid spacing in y direction
        :param Height: height of grid (y)
        :param Width: width of grid (x)
        :param CenterX: center of grid (x, in scene coords)
        :param CenterY: center of grid (y, in scene coords)
        :param Pen: pen for grid lines
        :param Brush: brush for background
        :return: nothing
        """
        Pen = self.penGridLines
        Brush = self.brushGrid
        height = self.scene.sceneRect().height() if Height is None else Height
        width = self.scene.sceneRect().width() if Width is None else Width
        left = self.scene.sceneRect().left() if CenterX is None else (CenterX - width / 2.0)
        right = self.scene.sceneRect().right() if CenterX is None else (CenterX + width / 2.0)
        top = -1.0 * self.scene.sceneRect().top() if CenterY is None else (-CenterY + height / 2.0)
        bottom = -1.0 * self.scene.sceneRect().bottom() if CenterY is None else (-CenterY - height / 2.0)
        Dx = DeltaX
        Dy = DeltaY
        pen = qtg.QPen() if Pen is None else Pen

        # make the background rectangle first
        if Brush is not None:
            rect = qtw.QGraphicsRectItem(left, -top, width, height)
            rect.setBrush(Brush)
            rect.setPen(pen)
            self.scene.addItem(rect)
        # draw the vertical grid lines
        x = left
        while x <= right:
            lVert = qtw.QGraphicsLineItem(x, top, x, bottom)
            lVert.setPen(pen)
            self.scene.addItem(lVert)
            x += Dx
        # draw the horizontal grid lines
        y = bottom
        while y <= top:
            lHor = qtw.QGraphicsLineItem(left, -y, right, -y)  # now flip y
            lHor.setPen(pen)
            self.scene.addItem(lHor)
            y += Dy

    def drawNodes(self, PN=None, scene=None):
        """
        Draws a circle for each node along with a label and creates the tool tip.
        Also, draws an arrow for external flow.
        """
        if scene is None:
            scene = self.scene
        penNode = self.penNode
        brushNode = self.brushNode
        penNodeOutline = qtg.QPen() if penNode is None else penNode
        penNodeLabel = qtg.QPen(qtc.Qt.darkMagenta)
        penExtFlow = qtg.QPen(qtc.Qt.darkGreen)
        brushNodeFill = qtg.QBrush() if brushNode is None else brushNode
        brushArrowHead = qtg.QBrush(qtg.QColor.fromRgb(255, 128, 0, alpha=255))
        for n in PN.nodes:
            x = n.position.x
            y = n.position.y

            # make a tool tip
            q_units = PN.units.FlowRate
            p_units = PN.units.Pressure
            tooltip = 'Node {}: {} \n'.format(n.getName(), n.fitting.type)
            p = n.P if PN.SI else PN.units.CFPressure * n.P
            if n.IsSprinkler:
                tooltip += 'K = {:0.2f}\n'.format(n.K)
            if n.E is not None and n.E != 0.0:
                Q = n.E if PN.SI else n.E * PN.units.CFFlowRate
                tooltip += 'Qin = {:0.2f} ({})\n'.format(Q, q_units)
            tooltip += 'P = {:0.3f} ({})'.format(p, p_units)

            self.drawACircle(x, y, 7, brush=brushNodeFill, pen=penNodeOutline, name=('node: ' + n.getName()),
                             tooltip=tooltip)
            self.drawALabel(x - 15, y + 15, str=n.getName(), pen=penNodeLabel)
            # region add arrows for external flows $NEW$ 4/7/21
            if n.E is not None and n.E != 0.0:
                unitVec = self.AngleForExtFlowArrow(n,
                                                    PN=PN)  # resultant of unit vector for all pipes connected to node
                if unitVec.mag() <= 0.0:
                    unitVec = Position(x=-1.0, y=-1.0, z=0.0)
                    unitVec.normalize()
                a = n.position  # arrow start point
                b = a - 45.0 * unitVec  # arrow end point
                c = b - 30.0 * unitVec  # label position
                Q = n.E if PN.SI else n.E * PN.units.CFFlowRate
                q_units = PN.units.FlowRate
                self.drawAnArrow(startX=a.x, startY=a.y, endX=b.x, endY=b.y, stArrow=(n.E > 0.0), endArrow=(n.E < 0.0),
                                 pen=penNode, brush=brushArrowHead)
                self.drawALabel(x=c.x, y=c.y, str='{:0.2f} {}'.format(abs(Q), q_units), pen=penExtFlow)
            # endregion

    def AngleForExtFlowArrow(self, node=None, PN=None):
        """
        Sum the unit vectors along each pipe outward from the node.  Then normalize the resultant and multiply by -1.0
        :param node: node object of interest
        :param PN: pipe network object
        :return: a Position object pointing away from the node.
        """
        if node is None:
            return 45.0
        nPipes = 0
        n = node  # short name for easy use
        a = n.position  # position of the node
        r = Position()  # my resultant
        for p in node.Pipes:
            if p.startNode == node.Name:
                d = PN.getNode(p.endNode)
            else:
                d = PN.getNode(p.startNode)
            nPipes += 1
            b = d.position  # d is the other node of the pipe
            c = (b - a)
            c.normalize()
            r = r + c
        r.normalize2D()
        if r.mag() == 0.0:
            r.x = -1.0
            r.y = -1.0
            r.normalize()
        return r

    def drawPipes(self, PN=None):
        scene = self.scene
        penPipe = self.penPipe
        for p in PN.pipes:
            n1 = PN.getNode(p.startNode)
            n2 = PN.getNode(p.endNode)
            # set up to draw a triangle for flow direction
            angDeg = (n2.position - n1.position).getAngleDeg()
            flowBrush = qtg.QBrush(qtg.QColor.fromRgb(0, 255, 0, alpha=50))
            flowPen = qtg.QPen(qtg.QColor.fromRgb(0, 100, 0, alpha=128))
            if p.Q < 0.0:
                angDeg += 180
                flowBrush.setColor(qtg.QColor.fromRgb(255, 0, 0, alpha=50))
                flowPen.setColor(qtg.QColor.fromRgb(100, 0, 0, alpha=128))
            p1 = n1.position
            p2 = n2.position
            c = (p1 + p2) / 2.0
            line = qtw.QGraphicsLineItem(p1.x, -p1.y, p2.x, -p2.y)  # $NEW$ 4/7/21 flip y axis
            # give the pipe a name for rollover behavior
            line.setData(0, ('pipe: ' + p.getName()))
            # build a tool tip string
            st = 'pipe: ' + p.getName() + '\n'
            st += p.getPipeFlowRateOutput(tooltip=True, SI=PN.SI, units=PN.units) + '\n'
            p_units = PN.units.Head
            hl = p.FlowHeadLoss() if PN.SI else PN.units.CFHead * p.FlowHeadLoss()
            st += 'HL = {:0.3f} {}'.format(hl, p_units)
            # assign tool tip string
            line.setToolTip(st)
            line.setPen(penPipe)
            # add pipe to scene
            scene.addItem(line)
            # make a triangle in the middle of pipe to indicate flow direction.
            self.drawATriangle(centerX=c.x, centerY=c.y, Radius=7, angleDeg=angDeg, brush=flowBrush, pen=flowPen,
                               tip=st)

    def removePipeHighlights(self):
        scene = self.scene
        try:
            for n in range(len(self.pipeHighlights) - 1, -1, -1):
                scene.removeItem(self.pipeHighlights[n])
                self.pipeHighlights.pop(n)
        except:
            pass

    def highlightPipe(self, PN=None, pipeName=None):
        scene = self.scene
        p = PN.getPipe(pipeName)
        a = (PN.getNode(p.startNode)).position
        b = (PN.getNode(p.endNode)).position
        # build a fat line to highlight the pipe
        highlight = qtw.QGraphicsLineItem(a.x, -a.y, b.x, -b.y)
        penHighlight = qtg.QPen(qtg.QColor.fromRgb(255, 128, 0, alpha=30))
        penHighlight.setWidth(15)
        highlight.setPen(penHighlight)
        # add highlight to the scene
        scene.addItem(highlight)
        # put highlight in a list so I can remove it if I want later.
        self.pipeHighlights.append(highlight)

    def drawLoopLabels(self, PN=None):
        scene = self.scene
        penLoop = qtg.QPen(qtc.Qt.cyan)
        penLoop.setColor(qtg.QColor.fromRgb(0, 100, 100, alpha=85))
        brushLoop = qtg.QBrush(qtg.QColor.fromRgb(100, 128, 0, alpha=85))
        for L in PN.loops:
            c = L.findCentroid(nodes=PN.nodes)
            tt = 'Loop ' + L.getName() + ':\n'
            for p in L.pipes:
                tt += '{}\n'.format(p.getName())
            self.drawALabel(x=c.x, y=c.y, str=L.getName(), pen=penLoop, brush=brushLoop, tip=tt)

    def polarToRect(self, centerX, centerY, radius, angleDeg=0.0):
        angleRad = angleDeg * 2.0 * math.pi / 360.0
        return centerX + radius * math.cos(angleRad), centerY + radius * math.sin(angleRad)

    def drawACircle(self, centerX, centerY, Radius, angle=0, brush=None, pen=None, name=None, tooltip=None):
        scene = self.scene
        # ellipse = qtw.QGraphicsEllipseItem(centerX - Radius, centerY - Radius, 2 * Radius, 2 * Radius)
        ellipse = qtw.QGraphicsEllipseItem(centerX - Radius, -1.0 * (centerY + Radius), 2 * Radius,
                                           2 * Radius)  # $NEW$ 4/7/21 flip y
        if pen is not None:
            ellipse.setPen(pen)
        if brush is not None:
            ellipse.setBrush(brush)
        if name is not None:
            ellipse.setData(0, name)
        if tooltip is not None:
            ellipse.setToolTip(tooltip)
        scene.addItem(ellipse)

    def drawASquare(self, centerX, centerY, Size, brush=None, pen=None):
        # coordinates specified as y up, so need to flip y in calculation
        # top left corner (centerX-Size/2, centerY+Size/2)
        # width=Size, height=Size
        # sqr = qtw.QGraphicsRectItem(centerX - Size / 2.0, centerY - Size / 2.0, Size, Size)
        scene = self.scene
        sqr = qtw.QGraphicsRectItem(centerX - Size / 2.0, -1.0 * (centerY - Size / 2.0), Size, Size)
        if pen is not None:
            sqr.setPen(pen)
        if brush is not None:
            sqr.setBrush(brush)
        scene.addItem(sqr)

    def drawATriangle(self, centerX, centerY, Radius, angleDeg=0.0, brush=None, pen=None, tip=None):
        scene = self.scene
        pts = []
        # calculations assuming y is pointed up, so need to flip y for drawing
        x, y = self.polarToRect(centerX, centerY, Radius, 0.0 + angleDeg)
        pts.append(qtc.QPointF(x, -y))  # flip y
        x, y = self.polarToRect(centerX, centerY, Radius, 120.0 + angleDeg)
        pts.append(qtc.QPointF(x, -y))  # flip y
        x, y = self.polarToRect(centerX, centerY, Radius, 240.0 + angleDeg)
        pts.append(qtc.QPointF(x, -y))  # flip y
        x, y = self.polarToRect(centerX, centerY, Radius, 0.0 + angleDeg)
        pts.append(qtc.QPointF(x, -y))  # flip y

        pg = qtg.QPolygonF(pts)
        PG = qtw.QGraphicsPolygonItem(pg)
        if pen is not None:
            PG.setPen(pen)
        if brush is not None:
            PG.setBrush(brush)
        if tip is not None:
            PG.setToolTip(tip)
        scene.addItem(PG)

    def drawAnArrow(self, startX=None, startY=None, endX=None, endY=None, stArrow=False, endArrow=True, pen=None,
                    brush=None):
        scene = self.scene
        line = qtw.QGraphicsLineItem(startX, -startY, endX, -endY)
        p = qtg.QPen() if pen is None else pen
        line.setPen(pen)
        a = Position((startX, startY, 0.0))
        b = Position((endX, endY, 0.0))
        pt = b - a

        angleDeg = pt.getAngleDeg()

        scene.addItem(line)
        if endArrow:
            self.drawATriangle(endX, endY, 5, angleDeg=angleDeg, pen=pen, brush=brush)
        if stArrow:
            self.drawATriangle(startX, startY, 5, angleDeg=(180.0 + angleDeg), pen=pen, brush=brush)

    def drawALabel(self, x, y, str='', pen=None, brush=None, tip=None):
        """
        I've decided that x,y are the center of the label.  Find corner based on label width and height.
        """
        scene = self.scene
        lbl = qtw.QGraphicsTextItem(str)
        w = lbl.boundingRect().width()
        h = lbl.boundingRect().height()
        lbl.setX(x - w / 2.0)
        lbl.setY(-y - h / 2.0)
        if tip is not None:
            lbl.setToolTip(tip)
        if pen is not None:
            lbl.setDefaultTextColor(pen.color())
        if brush is not None:
            # this makes a nice background
            bkg = qtw.QGraphicsRectItem(lbl.x(), lbl.y(), w, h)
            bkg.setBrush(brush)
            outlinePen = qtg.QPen(brush.color())
            bkg.setPen(outlinePen)
            scene.addItem(bkg)
        scene.addItem(lbl)

    # endregion

    # endregion

    # region Functions to print output to CLI
    def printPipeFlowRates(self, PN=None):
        for p in PN.pipes:
            p.printPipeFlowRate(SI=PN.SI)

    def printNetNodeFlows(self, PN=None):
        for n in PN.nodes:
            Q = n.getNetFlowRate()
            Q = Q if PN.SI else PN.uints.CFFlowRate * Q
            q_units = PN.units.FlowRate
            print('Q into {} = {:0.2f} {}'.format(n.Name, n.getNetFlowRate(), q_units))

    def printLoopHeadLoss(self, PN=None):
        for l in PN.loops:
            hl = l.getLoopHeadLoss(PN.nodes)
            hl = hl if PN.SI else PN.units.CFHeadLoss * hl
            p_units = PN.units.FlowHeadLoss
            print('HL for {} = {:0.2f} {}'.format(l.name, l.getLoopHeadLoss(PN.nodes), p_units))

    def printPipeHeadLoss(self, PN=None):
        for p in PN.pipes:
            hl = p.FlowHeadLoss()
            hl = hl if PN.SI else PN.units.CFHeadLoss * hl
            l = p.length if PN.SI else p.length * PN.units.CFLength
            d = p.diam if PN.SI else p.diam * PN.units.CFDiameter
            p_units = PN.units.FlowHeadLoss

            print('HL for {} (L={:0.2f}, d={:0.3f}) = {:0.3f} {}'.format(p.getName(), l, d, hl, p_units))

    def printNodeHead(self, PN=None):
        for N in PN.nodes:
            p = N.P if PN.SI else PN.units.CFPressure * N.P
            p_units = PN.units.Pressure
            z_units = PN.units.Length
            z = N.position.z if PN.SI else PN.units.CFLength * N.position.z
            q_units = PN.units.FlowRate
            Q = N.E if PN.SI else PN.units.CFFlowRate * N.E
            if N.IsSprinkler:
                print('PH at sprinkler {} (Z={:0.2f} {}) = {:0.2f} {} (K={:0.2f}, Q={:0.2f} {}})'.format(N.Name, z,
                                                                                                         z_units, p,
                                                                                                         p_units, N.K,
                                                                                                         Q, q_units))
            else:
                print('PH at node {} (Z={:0.2f} {}) = {:0.2f} {}'.format(N.Name, z, z_units, p, p_units))

    # endregion

    # region Functions to output strings to be displayed on GUI
    def getPipeFlowRatesOutput(self, tabs='', PN=None):
        lbl = self.lbl_FlowRates
        stOut = 'Flow Results:\n'
        for p in PN.pipes:
            stOut += p.getPipeFlowRateOutput(SI=PN.SI, tabs=tabs, units=PN.units) + '\n'
        if not lbl is None:
            lbl.setText(stOut)
        return stOut

    def getPipeFlowRatesOutputSorted(self, tabs='', PN=None):
        table = self.table_Pipes
        lbl = self.lbl_FlowRates
        q_units = PN.units.FlowRate
        stOut = 'Flow Results (' + q_units + ')\n'
        rows = table.rowCount()
        for i in range(rows):
            p = PN.getPipe(table.item(i, 0).text())
            stOut += p.getPipeFlowRateOutput(SI=PN.SI, tabs=tabs, units=PN.units) + '\n'
        if not lbl is None:
            lbl.setText(stOut)
        return stOut

    def getNetNodeFlowsOutput(self, tabs='', PN=None):
        lbl = self.lbl_PressureAndFlowChecks
        stOut = 'Net Flow Into Nodes:\n'
        for n in PN.nodes:
            Q = n.getNetFlowRate()
            Q = Q if PN.SI else PN.units.CFFlowRate * Q
            q_units = PN.units.FlowRate
            stOut += tabs + 'Q into {} = {:0.2f} {}'.format(n.getName(), Q, q_units) + '\n'
        if not lbl is None:
            lbl.setText(stOut)
        return stOut

    def getNetNodeFlowsOutputSorted(self, tabs='', PN=None):
        lbl = self.lbl_PressureAndFlowChecks
        table = self.table_Nodes
        q_units = PN.units.FlowRate
        stOut = 'Net Flow Into Nodes: (' + q_units + '):\n'
        rows = table.rowCount()
        for i in range(rows):
            n = PN.getNode(table.item(i, 0).text())
            Q = n.getNetFlowRate()
            Q = Q if PN.SI else PN.units.CFFlowRate * Q
            stOut += tabs + '{} -> {:0.2f}'.format(n.getName(), n.getNetFlowRate()) + '\n'
        if not lbl is None:
            lbl.setText(stOut)
        return stOut

    def getLoopHeadLossOutput(self, tabs='', PN=None):
        lbl = self.lbl_PressureAndFlowChecks
        stOut = 'Loop Head Losses:\n'
        for l in PN.loops:
            hl = l.getLoopHeadLoss(PN.nodes)
            hl = hl if PN.SI else PN.units.CFHeadLoss * hl
            hl_units = PN.units.FlowHeadLoss
            stOut += tabs + 'HL for {} = {:0.2f} {}'.format(l.getName(), hl, hl_units) + '\n'
        if not lbl is None:
            lbl.setText(stOut)
        return stOut

    def getLoopHeadLossOutputSorted(self, tabs='', PN=None):
        lbl = self.lbl_PressureAndFlowChecks
        tree = self.tree_Loops
        hl_units = PN.units.HeadLoss
        stOut = 'Loop Head Loss (' + hl_units + '):\n'
        items = tree.topLevelItemCount()
        for i in range(items):
            l = PN.getLoop(tree.topLevelItem(i).text(0))
            hl = l.getLoopHeadLoss(PN.nodes)
            hl = hl if PN.SI else PN.units.CFHeadLoss * hl
            stOut += tabs + '{} -> {:0.2f}'.format(l.getName(), l.getLoopHeadLoss(PN.nodes)) + '\n'
        if not lbl is None:
            lbl.setText(stOut)
        return stOut

    def getPipeHeadLossesOutput(self, tabs='', PN=None):
        lbl = self.lbl_PipeHeadLosses
        stOut = 'Pipe Head Losses:\n'
        for p in PN.pipes:
            hl = p.FlowHeadLoss()
            hl = hl if PN.SI else PN.units.CFHeadLoss * hl
            l = p.length if PN.SI else p.length * PN.units.CFLength
            d = p.diam if PN.SI else p.diam * PN.units.CFDiameter
            hl_units = PN.units.FlowHeadLoss
            stOut += tabs + 'HL in {} (L={:0.2f}, d={:0.3f}) is {:0.2f} {}'.format(p.getName(), l, d, hl,
                                                                                   hl_units) + '\n'
        if not lbl is None:
            lbl.setText(stOut)
        return stOut

    def getPipeHeadLossesOutputSorted(self, tabs='', PN=None):
        lbl = self.lbl_PipeHeadLosses
        table = self.table_Pipes
        hl_units = PN.units.Head
        stOut = 'Pipe Head Loss (' + hl_units + '):\n'
        rows = table.rowCount()
        for i in range(rows):
            p = PN.getPipe(table.item(i, 0).text())
            hl = p.FlowHeadLoss()
            hl = hl if PN.SI else PN.units.CFHeadLoss * hl
            l = p.length if PN.SI else PN.units.CFLength * p.length
            d = p.diam if PN.SI else PN.units.CFDiameter * p.diam
            stOut += tabs + '{} (L={:0.2f}, d={:0.3f}) -> {:0.2f}'.format(p.getName(), l, d, hl) + '\n'
        if not lbl is None:
            lbl.setText(stOut)
        return stOut

    def getNodeHeadOutput(self, tabs='', PN=None):
        lbl = self.lbl_NodePressures
        stOut = 'Node Pressures\n'
        for N in PN.nodes:
            p = N.P if PN.SI else PN.units.CFPressure * N.P
            p_units = PN.units.Pressure
            z_units = PN.units.Length
            z = N.position.z if PN.SI else PN.units.CFLength * N.position.z
            Q = N.E if PN.SI else PN.units.CFFlowRate * N.E
            Q_units = PN.units.FlowRate
            if N.IsSprinkler:
                stOut += tabs + 'PH at sprinkler {} (Z={:0.2f} {}) = {:0.2f} {} (K={:0.2f}, Q={:0.2f} {}})'.format(
                    N.getName(), z, z_units, p, p_units, N.K, Q, Q_units) + '\n'
            else:
                stOut += tabs + 'PH at node {} (Z={:0.2f} {}) = {:0.2f} {}'.format(N.getName(), z, z_units, p,
                                                                                   p_units) + '\n'
        if not lbl is None:
            lbl.setText(stOut)
        return stOut

    def getNodeHeadOutputSorted(self, tabs='', PN=None):
        lbl = self.lbl_NodePressures
        table = self.table_Nodes
        p_units = PN.units.Pressure
        z_units = PN.units.Length
        q_units = PN.units.FlowRate

        stOut = 'Node Pressures (' + p_units + ')\n'
        rows = table.rowCount()
        for i in range(rows):
            N = PN.getNode(table.item(i, 0).text())  # get node name from table
            p = N.P if PN.SI else PN.units.CFPressure * N.P
            z = N.position.z
            z = z if PN.SI else PN.units.CFLength * z
            Q = N.E if PN.SI else PN.units.CFFlowRate * N.E
            if N.IsSprinkler:
                stOut += tabs + '{} (Z={:0.2f}{}) -> {:0.2f} (K={:0.2f}, Q={:0.2f} {})'.format(
                    N.getName(), z, z_units, p, N.K, abs(Q), q_units) + '\n'
            else:
                stOut += tabs + '{} (Z={:0.2f} {}) -> {:0.2f}'.format(N.getName(), z, z_units, p) + '\n'
        if not lbl is None:
            lbl.setText(stOut)
        return stOut

    def getRealityCheckOutputSorted(self, tabs='', PN=None):
        lbl = self.lbl_PressureAndFlowChecks
        stOut = self.getLoopHeadLossOutputSorted(tabs='', PN=PN)
        stOut += '\n\n'
        stOut += self.getNetNodeFlowsOutputSorted(tabs='', PN=PN)
        if not lbl is None:
            lbl.setText(stOut)
        return stOut

    # endregion

    # region Function for output to a file
    def getPipeNetworkOutputForFile(self, filename=None, PN=None):
        header = '# Pipe Network\n\
# The SI units are: m for pipe length, mm for pipe diameter\n\
#                  L/s for external flow rates\n\
#                  m of water for pressure head\n\
#                  m for elevation of node\n\
#                  Pa*s for dynamic viscosity\n\
#                  m for pipe roughness\n\
#                  m of water for specified pressure\n\
#                  kg/m^3 for density\n\
# The English units are:  ft for pipe length, in for pipe diameter\n\
#                        cfs for external flow rates\n\
#                        psi for specified node pressure\n\
#                        in of water for head loss\n\
#                        ft for pipe roughness\n\
#                        lb*s/ft^2 for dynamic viscosity\n\
#                        lb/ft^3 for specific gravity\n'
        stTmp = ''
        stTmp += '<Fluid>\n'
        stTmp += '\tmu: {:0.5f}\n'.format(PN.Fluid.mu)
        stTmp += '\trho: {:0.1f}\n'.format(PN.Fluid.rho)
        stTmp += '</Fluid>\n'
        for p in PN.pipes:
            stTmp += '<Pipe>\n'
            stTmp += '\tnodes: ({},{})\n'.format(p.startNode, p.endNode)
            stTmp += '\tlength: {:0.1f}\n'.format(p.length)
            stTmp += '\tdiam: {:0.1f}\n'.format(p.diam * 1000.0)
            stTmp += '\trough: {:0.5f}\n'.format(p.rough)
            stTmp += '</Pipe>\n'
        for l in PN.loops:
            stTmp += '<Loop>\n'
            stTmp += '\tName: {}\n'.format(l.getName())
            stTmp += '\tPipes: '
            for i in range(len(l.pipes)):
                p = l.pipes[i]
                stTmp += (', ' if i > 0 else '') + '{}'.format(p.getName())
            stTmp += '\n'
            stTmp += '</Loop>\n'
        for n in PN.nodes:
            if n.E > 0.0 or n.E < 0.0:
                stTmp += '<Node>\n'
                stTmp += '\tName: {}\n'.format(n.getName())
                stTmp += '\tExternal Flow: {:0.1f}\n'.format(n.E)
                stTmp += '\tMinP: {}\n'.format(n.MinPH) if n.IsSprinkler else ''
                stTmp += '\tSprinkler: True\n' if n.IsSprinkler else ''
                stTmp += '</Node>\n'
        if filename is not None:
            # output to a file
            file = open(filename, 'w')
            file.write(header + stTmp)
            file.close()
        else:
            return stTmp

    def getPipeNetworkOutputForFileSorted(self, filename=None, PN=None, treeP=None, tableN=None, treeL=None):

        header = '# Pipe Network\n\
    # The SI units are: m for pipe length, mm for pipe diameter\n\
    #                  L/s for external flow rates\n\
    #                  m of water for pressure head\n\
    #                  m for elevation of node\n\
    #                  Pa*s for dynamic viscosity\n\
    #                  m for pipe roughness\n\
    #                  m of water for specified pressure\n\
    #                  kg/m^3 for density\n\
    # The English units are:  ft for pipe length, in for pipe diameter\n\
    #                        cfs for external flow rates\n\
    #                        psi for specified node pressure\n\
    #                        in of water for head loss\n\
    #                        ft for pipe roughness\n\
    #                        lb*s/ft^2 for dynamic viscosity\n\
    #                        lb/ft^3 for specific gravity\n'
        stTmp = ''
        stTmp += '<Fluid>\n'
        stTmp += '\tmu: {:0.5f}\n'.format(PN.Fluid.mu)
        stTmp += '\trho: {:0.1f}\n'.format(PN.Fluid.rho)
        stTmp += '</Fluid>\n'
        for i in range(treeP.topLevelItemCount()):
            p = PN.getPipe(treeP.topLevelItem(i).text(0))
            stTmp += '<Pipe>\n'
            stTmp += '\tnodes: ({},{})\n'.format(p.startNode, p.endNode)
            stTmp += '\tlength: {:0.1f}\n'.format(p.length)
            stTmp += '\tdiam: {:0.1f}\n'.format(p.diam * 1000.0)
            stTmp += '\trough: {:0.5f}\n'.format(p.rough)
            stTmp += '</Pipe>\n'
        for i in range(treeL.topLevelItemCount()):
            l = PN.getLoop(treeL.topLevelItem(i).text(0))
            stTmp += '<Loop>\n'
            stTmp += '\tName: {}\n'.format(l.getName())
            stTmp += '\tPipes: '
            for i in range(len(l.pipes)):
                p = l.pipes[i]
                stTmp += (', ' if i > 0 else '') + '{}'.format(p.getName())
            stTmp += '\n'
            stTmp += '</Loop>\n'
        for i in range(tableN.topLevelItemCount()):
            n = PN.getNode(tableN.topLevelItem(i).text(0))
            if n.E > 0.0 or n.E < 0.0:
                stTmp += '<Node>\n'
                stTmp += '\tName: {}\n'.format(n.getName())
                stTmp += '\tExternal Flow: {:0.1f}\n'.format(n.E)
                stTmp += '\tMinP: {}\n'.format(n.MinPH) if n.IsSprinkler else ''
                stTmp += '\tSprinkler: True\n' if n.IsSprinkler else ''
                stTmp += '</Node>\n'
        if filename is not None:
            # output to a file
            file = open(filename, 'w')
            file.write(header + stTmp)
            file.close()
        else:
            return stTmp

    def getPipeNetworkOutputForFileSortedWithNodePositions(self, filename=None, PN=None, tableP=None, tableN=None,
                                                           treeL=None):
        if tableP is None:
            tableP = self.table_Pipes
        if tableN is None:
            tableN = self.table_Nodes
        if treeL is None:
            treeL = self.tree_Loops
        header = '# Pipe Network\n\
    # The SI units are: m for pipe length, mm for pipe diameter\n\
    #                  L/s for external flow rates\n\
    #                  m of water for pressure head\n\
    #                  m for elevation of node\n\
    #                  Pa*s for dynamic viscosity\n\
    #                  m for pipe roughness\n\
    #                  m of water for specified pressure\n\
    #                  kg/m^3 for density\n\
    # The English units are:  ft for pipe length, in for pipe diameter\n\
    #                        cfs for external flow rates\n\
    #                        psi for specified node pressure\n\
    #                        in of water for head loss\n\
    #                        ft for pipe roughness\n\
    #                        lb*s/ft^2 for dynamic viscosity\n\
    #                        lb/ft^3 for specific gravity\n'
        stTmp = ''
        stTmp += '<Fluid>\n'
        stTmp += '\tmu: {:0.5f}\n'.format(PN.Fluid.mu)
        stTmp += '\trho: {:0.1f}\n'.format(PN.Fluid.rho)
        stTmp += '</Fluid>\n'
        for i in range(tableP.rowCount()):
            p = PN.getPipe(tableP.item(i, 0).text())
            stTmp += '<Pipe>\n'
            stTmp += '\tnodes: ({},{})\n'.format(p.startNode, p.endNode)
            # stTmp += '\tlength: {:0.1f}\n'.format(p.length)
            stTmp += '\tdiam: {:0.1f}\n'.format(p.diam * 1000.0)
            stTmp += '\trough: {:0.5f}\n'.format(p.rough)
            stTmp += '</Pipe>\n'
        for i in range(treeL.topLevelItemCount()):
            l = PN.getLoop(treeL.topLevelItem(i).text(0))
            stTmp += '<Loop>\n'
            stTmp += '\tName: {}\n'.format(l.getName())
            stTmp += '\tPipes: '
            for i in range(len(l.pipes)):
                p = l.pipes[i]
                stTmp += (', ' if i > 0 else '') + '{}'.format(p.getName())
            stTmp += '\n'
            stTmp += '</Loop>\n'
        for i in range(tableN.rowCount()):
            n = PN.getNode(tableN.item(i, 0).text())
            stTmp += '<Node>\n'
            stTmp += '\tName: {}\n'.format(n.getName())
            stTmp += '\tPosition: {}\n'.format(n.position.getStr())
            stTmp += '\tFitting:  {}\n'.format(n.fitting.type)
            stTmp += '\tExternal Flow: {:0.2f}\n'.format(n.E)
            stTmp += '\tMinP: {:0.3f}\n'.format(n.MinPH) if n.IsSprinkler else ''
            stTmp += '\tSpecifiedP: {:0.3f}\n'.format(n.SpecifiedP) if n.SpecifiedP > 0.0 else ''
            stTmp += '\tSprinkler: True\n' if n.IsSprinkler else ''
            stTmp += '</Node>\n'
        if filename is not None:
            # output to a file
            file = open(filename, 'w')
            file.write(header + stTmp)
            file.close()
        else:
            return stTmp
    # endregion

def mainHW5():
    '''
    This program analyzes flows in a given pipe network based on the following:
    1. The pipe segments are named by their endpoint node names:  e.g., a-b, b-e, etc.
    2. Flow from the lower letter to the higher letter of a pipe is considered positive.
    3. Pressure decreases in the direction of flow through a pipe.
    4. At each node in the pipe network, mass is conserved.
    5. For any loop in the pipe network, the pressure loss is zero
    Approach to analyzing the pipe network:
    Step 1: build a pipe network object that contains pipe, node, loop and fluid objects
    Step 2: calculate the flow rates in each pipe using fsolve
    Step 3: output results
    Step 4: check results against expected properties of zero head loss around a loop and mass conservation at nodes.
    :return:
    '''
    # instantiate a Fluid object to define the working fluid as water
    water = Fluid(mu=0.00089, rho=1000.0)
    roughness = 0.00025  # in m

    # instantiate a new PipeNetworkController
    PNC = PipeNetworkController()

    # add Pipe objects to the pipe network through PNC
    PNC.addPipe(Pipe('a', 'b', 185.0, 300.0, roughness, water))
    PNC.addPipe(Pipe('a', 'c', 100.0, 200.0, roughness, water))
    PNC.addPipe(Pipe('b', 'e', 165.0, 200.0, roughness, water))
    PNC.addPipe(Pipe('c', 'd', 125.0, 200.0, roughness, water))
    PNC.addPipe(Pipe('c', 'f', 100.0, 150.0, roughness, water))
    PNC.addPipe(Pipe('d', 'e', 125.0, 200.0, roughness, water))
    PNC.addPipe(Pipe('d', 'g', 100.0, 150.0, roughness, water))
    PNC.addPipe(Pipe('e', 'h', 100.0, 150.0, roughness, water))
    PNC.addPipe(Pipe('f', 'g', 125.0, 250.0, roughness, water))
    PNC.addPipe(Pipe('g', 'h', 125.0, 250.0, roughness, water))
    # add Node objects to the pipe network
    # modify the nodes appropriately
    PNC.modifyNode(item=None, name='a', makesprinkler=False, ext_flow=60.0, position=Position(pos=(-125.0, 100, 0.0)))
    PNC.modifyNode(item=None, name='b', makesprinkler=False, position=Position(pos=(125.0, 100.0, 0.0)), min_ph=2.0)
    PNC.modifyNode(item=None, name='c', makesprinkler=False, position=Position(pos=(-125.0, 0.0, 0.0)))
    PNC.modifyNode(item=None, name='d', makesprinkler=True, ext_flow=-30, position=Position(pos=(0.0, 0.0, 0.0)),
                   min_ph=2.0)
    PNC.modifyNode(item=None, name='e', makesprinkler=False, position=Position(pos=(125.0, 0.0, 0.0)))
    PNC.modifyNode(item=None, name='f', makesprinkler=True, ext_flow=-15, position=Position(pos=(-125.0, -100.0, 0)),
                   min_ph=2.0)
    PNC.modifyNode(item=None, name='g', makesprinkler=False, position=Position(pos=(0.0, -100.0, 0.0)))
    PNC.modifyNode(item=None, name='h', makesprinkler=True, ext_flow=-15, position=Position(pos=(125.0, -100.0, 0)),
                   min_ph=2.0)
    PNC.Model.buildNodes()

    # add Loop objects to the pipe network
    PNC.addLoop(Loop('A', [PNC.Model.getPipe('a-b'), PNC.Model.getPipe('b-e'), PNC.Model.getPipe('d-e'),
                           PNC.Model.getPipe('c-d'), PNC.Model.getPipe('a-c')]))
    PNC.addLoop(Loop('B', [PNC.Model.getPipe('c-d'), PNC.Model.getPipe('d-g'), PNC.Model.getPipe('f-g'),
                           PNC.Model.getPipe('c-f')]))
    PNC.addLoop(Loop('C', [PNC.Model.getPipe('d-e'), PNC.Model.getPipe('e-h'), PNC.Model.getPipe('g-h'),
                           PNC.Model.getPipe('d-g')]))

    # call the findFlowRates method of the PN (a PipeNetwork object)
    PNC.EvaluatePipeNetwork()

    # get output for zero height nodes
    PNC.printOutput()

    # new node elevations
    # now change node elevations (which also changes pipe lengths by geometry assuming straight pipe runs between nodes)
    sf = 1.0
    # modify the nodes appropriately
    PNC.modifyNode(item=None, name='a', makesprinkler=False, ext_flow=60.0, position=Position(pos=(-125.0, 100, 0.0)))
    PNC.modifyNode(item=None, name='b', makesprinkler=False, position=Position(pos=(125.0, 100.0, 2.5)), min_ph=2.0)
    PNC.modifyNode(item=None, name='c', makesprinkler=False, position=Position(pos=(-125.0, 0.0, 5.0)))
    PNC.modifyNode(item=None, name='d', makesprinkler=True, ext_flow=-30, position=Position(pos=(0.0, 0.0, 5.0)),
                   min_ph=2.0)
    PNC.modifyNode(item=None, name='e', makesprinkler=False, position=Position(pos=(125.0, 0.0, 5.0)))
    PNC.modifyNode(item=None, name='f', makesprinkler=True, ext_flow=-15, position=Position(pos=(-125.0, -100.0, 4.0)),
                   min_ph=2.0)
    PNC.modifyNode(item=None, name='g', makesprinkler=False, position=Position(pos=(0.0, -100.0, 4.5)))
    PNC.modifyNode(item=None, name='h', makesprinkler=True, ext_flow=-15, position=Position(pos=(125.0, -100.0, 4.5)),
                   min_ph=2.0)
    PNC.Model.buildNodes()

    # calculate the flow rates for the new pipe network layout without fixed sprinkler flow rates
    PNC.Model.findFlowRates2()

    print()
    print('Second pipe network')
    PNC.printOutput()

if __name__ == '__main__':
    mainHW5()
    # mainX2()
