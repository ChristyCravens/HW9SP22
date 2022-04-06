import sys
from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtGui as qtg
from PipeNetwork_GUI import Ui_Form
from PipeNetwork_classes import *

class MainWindow(qtw.QWidget, Ui_Form):
    def __init__(self):
        """
        Main window constructor.
        """
        super().__init__()
        self.setupUi(self)
        self.dlg =qtw.QFileDialog()
        #initialize Controller and give some widgets to view for display
        #Note: the controller contains the PipeNetwork object and a PipeNetworkView object.  This way of making the
        #controller "self contained" makes interaction between the Model-View-Controller more efficient.  In the app,
        #I always refer to the controller if I want to modify the model or update the view.
        self.Controller = PipeNetworkController()
        self.Controller.rdo_SI=self.rdo_Metric
        #I found it convenient to pass references to the trees, tables and labels to the View object so that I needn't
        #worry about constantly passing them in the main app.  Now, the controller can update the view internally.
        widgets=(self.tree_Loops, self.table_Pipes, self.table_Nodes, self.tree_LoopPipes, self.lbl_PipeHeadLosses, \
                 self.lbl_NodePressures, self.lbl_FlowRates, self.lbl_PressureAndFlowChecks, self.lbl_Diam, \
                 self.le_Diam, self.lbl_Rough, self.le_Roughness)
        self.Controller.setViewWidgets(widgets)

        self.setupGraphicsView()

        #set tables and trees to sort alphabetically by name as default
        self.table_Pipes.sortItems(0,0)
        self.tree_Loops.sortItems(0,0)
        self.table_Nodes.sortItems(0,0)

        # Main UI code goes here
        self.setupSignalsSlotsEventFilter()
        # end Main UI code

        self.show()  # show the main widget
        self.readPipeNetworkFile()  # this opens the dialog box to read a pipe network file upon running the program

    def setupSignalsSlotsEventFilter(self):
        """
        This is called from the constructor to wire up the signals and slots and install event filter if needed.
        :return: nothing
        """
        # CONNECTING SIGNALS AND SLOTS
        # these available signals can be easily connected to a slot
        self.btn_AddPipe.clicked.connect(self.addPipe)
        self.btn_DeletePipe.clicked.connect(self.deletePipe)
        self.btn_AddPipeToLoop.clicked.connect(self.addPipeToLoop)
        self.btn_CreateLoop.clicked.connect(self.createLoop)
        self.btn_Evaluate.clicked.connect(self.EvaluatePipeNetwork)
        self.table_Pipes.itemChanged.connect(self.modifyPipe)
        self.table_Pipes.itemSelectionChanged.connect(self.highlightPipe)
        self.table_Nodes.itemChanged.connect(self.modifyNode)
        self.tree_Loops.itemChanged.connect(self.modifyLoop)
        self.btn_OpenPipeNetworkFile.clicked.connect(self.readPipeNetworkFile)
        self.btn_SavePipeNetworkFile.clicked.connect(self.savePipeNetworkFile)
        self.spnd_Zoom.valueChanged.connect(self.setZoom) #$NEW$ double spinner widget for setting zoom level
        self.rdo_Metric.toggled.connect(self.Controller.setUnits)

        # INSTALLING AN EVENT FILTER ON THE TREE WIDGETS
        # I do this if there is no easy signal to connect to do what I want.
        # The event filter allows the widget to analyze events from the windows event loop when
        # they occur on the widget.
        # if a signal is not available, I can use the event filter to take action
        self.table_Pipes.installEventFilter(self)
        self.table_Nodes.installEventFilter(self)
        self.tree_LoopPipes.installEventFilter(self)
        self.tree_Loops.installEventFilter(self)

    def eventFilter(self, obj, event):
        """
        This overrides the default eventFilter of the widget.  It takes action on events and then passes the event
        along to the parent widget.
        :param obj: The object on which the event happened
        :param event: The event itself
        :return: boolean from the parent widget
        """
        #region $NEW$ 4/6/21 for mouse tracking on the drawing
        if obj == self.Controller.View.scene:
            et=event.type()
            if event.type() == qtc.QEvent.GraphicsSceneMouseMove:
                w=app.topLevelAt(event.screenPos())
                scenePos=event.scenePos()
                s=self.Controller.View.scene.itemAt(scenePos,self.gv_Main.transform())  # gets item from graphics scene under the mouse
                strScene="Mouse Position:  x = {}, y = {}".format(round(scenePos.x(),2), round(-scenePos.y(),2)) #$NEW$ 4/7/21 flip y
                if s is not None and s.data(0) is not None:  # when creating nodes and pipes, I used the setData() function to store a name
                    strScene += ' ' + s.data(0)
                self.lbl_MousePosition.setText(strScene)  # display information in a label
            if event.type()==qtc.QEvent.GraphicsSceneWheel:  # I added this to zoom on mouse wheel scroll
                if event.delta()>0:
                    self.spnd_Zoom.stepUp()
                else:
                    self.spnd_Zoom.stepDown()
                pass
        #endregion
        # allow table_Pipes, table_Nodes, tree_LoopPipes, and tree_Loops to respond to delete key
        if event.type() == qtc.QEvent.KeyPress:
            if event.key() == qtc.Qt.Key_Delete:
                if obj == self.table_Pipes:
                    self.deletePipe()
                elif obj == self.table_Nodes:
                    self.deleteNode()
                elif obj == self.tree_LoopPipes:
                    self.deleteLoopPipe()
                elif obj == self.tree_Loops:
                    self.deleteLoop()

        # pass the event along to the parent widget if there is one.
        return super(MainWindow, self).eventFilter(obj, event)

    #region functions associated with the drawing
    def setupGraphicsView(self):
        #create a scene object
        scene=self.Controller.View.scene
        #scene = qtw.QGraphicsScene()
        scene.setObjectName("MyScene")
        scene.setSceneRect(-200, -200, 400, 400)  # xLeft, yTop, Width, Height
        scene.installEventFilter(self) #install the event filter for use in mouse tracking

        self.setMouseTracking(True)
        self.gv_Main.setMouseTracking(True)

        #set the scene for the graphics view object
        self.gv_Main.setScene(scene)

    def setZoom(self):
        self.gv_Main.resetTransform()
        self.gv_Main.scale(self.spnd_Zoom.value(), self.spnd_Zoom.value())
    #endregion

    #region Functions that act as Slots
    def readPipeNetworkFile(self):
        """
        Read the information from a pipe network file.
        :return:
        """
        # open the file dialog box to search for the file I want
        filename = self.dlg.getOpenFileName(caption='Select a pipe network file to open.')[0]
        if len(filename) == 0:  # no file selected
            return
        #self.le_FileName.setText(filename)  # echo the filename on the GUI
        file = open(filename, 'r')  # open the file
        data = file.readlines()  # read all the lines of the file into a list of strings
        self.Controller.importPipeNetwork(data, PN=self.Controller.Model)  # import the pipe network information

    def savePipeNetworkFile(self):
        """
        Read the information from a pipe network file.
        :return:
        """
        # open the file dialog box to search for the file I want

        filename = self.dlg.getSaveFileName()[0]
        if len(filename) == 0:  # no file selected
            return
        else:
            #self.Controller.View.getPipeNetworkOutputForFileSorted(filename=filename, PN=self.Controller.Model, treeP=self.table_Pipes, tableN=self.table_Nodes, treeL=self.tree_Loops)
            self.Controller.View.getPipeNetworkOutputForFileSortedWithNodePositions(filename=filename, PN=self.Controller.Model, tableP=self.table_Pipes, tableN=self.table_Nodes, treeL=self.tree_Loops)

    def addPipe(self):
        """
        I use this as the slot for the clicked signal of the Add Pipe button.  It reads from the
        line edit boxes and creates a top level QTreeWidgetItem and places it in the table_Pipes widget.
        :return: none
        """
        node1 = self.le_StartNode.text()  # read from GUI
        node2 = self.le_EndNodeName.text()  # read from GUI
        name = '{}-{}'.format(min(node1, node2), max(node1, node2))  # follow alphabetical naming convention
        #length = self.le_PipeLength.text()  # read from GUI
        diam = float(self.le_Diam.text())  # read from GUI
        rough = self.le_Roughness.text()  # read from GUI
        itm = (name, 1.0, diam, rough)
        self.Controller.addPipe(itm)  # part of the controller that updates the model with changes on the view

    def modifyPipe(self):
        self.Controller.modifyPipe()

    def highlightPipe(self):
        names=[]
        self.Controller.View.removePipeHighlights()
        for i in self.table_Pipes.selectedItems():
            r=i.row()
            p=self.table_Pipes.item(r,0).text()
            if not p in names:
                names.append(p)
                self.Controller.View.highlightPipe(PN=self.Controller.Model,pipeName=p)

    def modifyNode(self):
        self.Controller.modifyNode(self.table_Nodes)

    def modifyLoop(self, item, col):
        self.Controller.modifyLoop(item, col)

    def deletePipe(self):
        """
        This is the slot for the clicked signal of the Delete Pipe button as well as the response to the delete
        key being pressed when in the tree_Pipe widget.  This latter behavior is implemented with the eventFilter
        method that is installed on the tree_Pipe widget.
        :return: none
        """
        self.Controller.deletePipe()

    def deleteNode(self):
        if self.table_Nodes.rowCount()==0: return
        row=self.table_Nodes.currentRow()
        itm=self.table_Nodes.item(row,0)
        if itm is None: return
        self.Controller.deleteNode(itm)

    def deleteLoopPipe(self):
        """
        This is the response to the delete
        key being pressed when in the tree_LoopPipes widget.  It implemented with the eventFilter
        method that is installed on the tree_LoopPipe widget.
        :return:
        """
        index = self.tree_LoopPipes.currentIndex().row()
        self.tree_LoopPipes.takeTopLevelItem(index)

    def deleteLoop(self):
        """
        This is the response to the delete
        key being pressed when in the tree_Loops widget.  It implemented with the eventFilter
        method that is installed on the tree_Loops widget.
        :return:
        """
        isParent = self.tree_Loops.currentItem().parent() is None
        itm = self.tree_Loops.currentItem()
        index = self.tree_Loops.currentIndex().row()
        if isParent:
            self.Controller.deleteLoop(self.tree_Loops.takeTopLevelItem(index))
        else:
            parent = self.tree_Loops.currentItem().parent()
            self.tree_Loops.currentItem().parent().removeChild(itm)
            self.Controller.modifyLoop(parent, 0)

    def addPipeToLoop(self):
        """
        I use this as the slot for the clicked signal of the Add Pipe to loop button.  It reads from the
        table_Pipes widget and creates a top level QTreeWidgetItem and places it in the tree_LoopPipes widget.
        :return: none
        """
        for p in self.table_Pipes.selectedItems():
            r=p.row()
            name = self.table_Pipes.item(r,0).text()
            rows = str(self.tree_LoopPipes.topLevelItemCount())
            itm = qtw.QTreeWidgetItem((rows, name))
            itm.setFlags(qtc.Qt.ItemIsSelectable | qtc.Qt.ItemIsEditable | qtc.Qt.ItemIsDragEnabled | qtc.Qt.ItemIsUserCheckable | qtc.Qt.ItemIsEnabled)
            self.tree_LoopPipes.addTopLevelItem(itm)
        # rows = self.tree_LoopPipes.topLevelItemCount()

    def createLoop(self):
        """
        This is the slot for the clicked signal of btn_CreateLoop.  It reads from the tree_LoopPipes and builds
        the hierarchy of a loop object and adds it to the tree_Loops widget.
        :return:
        """
        loopName = [self.le_LoopName.text()]
        pipes = []
        while self.tree_LoopPipes.topLevelItemCount() > 0:
            pipe = self.tree_LoopPipes.takeTopLevelItem(0)
            pipes.append([pipe.text(1)])
        loop = qtw.QTreeWidgetItem(loopName)
        loop.setFlags(qtc.Qt.ItemIsSelectable | qtc.Qt.ItemIsEditable | qtc.Qt.ItemIsDragEnabled | qtc.Qt.ItemIsUserCheckable | qtc.Qt.ItemIsEnabled)
        for p in pipes:
            itm =nonSortingTreeItem(p)
            itm.setFlags(qtc.Qt.ItemIsSelectable | qtc.Qt.ItemIsEditable | qtc.Qt.ItemIsDragEnabled | qtc.Qt.ItemIsUserCheckable | qtc.Qt.ItemIsEnabled)
            loop.addChild(itm)
        self.tree_Loops.addTopLevelItem(loop)
        self.Controller.addLoop(loop)

    def EvaluatePipeNetwork(self):
        """
        Use the controller to call evaluate pipe network and display output
        :return:
        """
        self.Controller.EvaluatePipeNetwork()
        return None
    #endregion

if __name__ == '__main__':
    # Handle high resolution displays:
    # if hasattr(qtc.Qt, 'AA_EnableHighDpiScaling'):
    #     qtw.QApplication.setAttribute(qtc.Qt.AA_EnableHighDpiScaling, True)
    # if hasattr(qtc.Qt, 'AA_UseHighDpiPixmaps'):
    #     qtw.QApplication.setAttribute(qtc.Qt.AA_UseHighDpiPixmaps, True)
    app = qtw.QApplication(sys.argv)
    mw = MainWindow()
    mw.setWindowTitle('Pipe Network Calculator')
    sys.exit(app.exec())