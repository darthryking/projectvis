import gc
from itertools import izip, product, permutations
from collections import OrderedDict

from vdfutils import parse_vdf, format_vdf

__all__ = (
    'BSPTree',
    'BSPElement',
    'BSPNode',
    'BSPLeaf',
    'BSPPortal',
)

COLOR_BLACK = (0, 0, 0)
COLOR_GRAY = (128, 128, 128)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (255, 0, 0)
COLOR_MAGENTA = (255, 0, 255)
COLOR_CYAN = (0, 255, 255)


class BSPTree(object):
    def __init__(self, maxWidth, maxHeight):
        self.maxWidth = maxWidth
        self.maxHeight = maxHeight
        
        self.head = BSPLeaf(None, (0, 0, maxWidth, maxHeight))
        
        # Populated with portal instances once .generate_portals() is called.
        self.portals = set()
        
    def __repr__(self):
        return "BSPTree({}, {})".format(self.maxWidth, self.maxHeight)
        
    def __str__(self):
        return "<BSPTree ({}x{}) with head: {}>".format(
                self.maxWidth, self.maxHeight, self.head
            )
            
    def __iter__(self):
        # Python's iterator protocol is beautiful.
        return self.iter_elements()
        
    @classmethod
    def from_vdf(cls, data):
        ''' Constructs a new BSP tree from a set of VDF KeyValues data. '''
        
        bspDict = parse_vdf(data)['BSP']
        
        # Instantiate a new BSP tree.
        b = cls(bspDict['maxWidth'], bspDict['maxHeight'])
        
        # A dictionary of all elements in the BSP tree.
        elementsDict = bspDict['elements']
        
        # List of all BSP elements (NOT in dictionary form).
        elements = []
        
        # Pass 1: Instantiate all elements.
        for elementDict in elementsDict.itervalues():
            if elementDict['type'] == BSPNode.__name__:
                newElem = BSPNode.from_dict(elementDict)
                
            elif elementDict['type'] == BSPLeaf.__name__:
                newElem = BSPLeaf.from_dict(elementDict)
                
            else:
                assert False
                
            elements.append(newElem)
            
        # Pass 2: Re-link all element relationships.
        for element, elementDict in izip(elements, elementsDict.itervalues()):
            if type(element) is BSPNode:
                leftIndex = int(elementDict['left'])
                rightIndex = int(elementDict['right'])
                
                element.left = elements[leftIndex]
                element.right = elements[rightIndex]
                
                element.left.parent = element
                element.right.parent = element
                
        # Set the first element to be the BSP tree's head node.
        b.head = elements[0]
        
        return b
        
    def to_vdf(self):
        ''' Serializes the BSP tree to VDF KeyValues format. '''
        
        def str_items(inDict):
            ''' Helper function for .to_vdf(). Returns a copy of the given 
            dictionary with all non-str keys and values converted to strings.
            
            '''
            
            result = OrderedDict()
            for key, value in inDict.iteritems():
                if isinstance(value, dict):
                    value = str_items(value)
                else:
                    value = str(value)
                    
                result[str(key)] = value
                
            return result
            
        # Set all leaves' BSPLeaf IDs to -1, pending ID reassignment for each 
        # visleaf.
        for leaf in self.iter_leaves():
            leaf.leafID = -1
            
        # Fix up each visleaf's BSPLeaf ID to be more suitable for visibility 
        # matrix representation.
        for i, visleaf in enumerate(self.iter_visleaves()):
            visleaf.leafID = i
            
        # List of the dictionary forms of all elements in the BSP tree.
        bspElements = []
        
        # Build the BSP elements list.
        for i, element in enumerate(self.iter_elements()):
            element.id = i      # Fix element IDs to be more sane.
            bspElements.append(element.to_dict())
            
        # A dictionary of elements in the BSP tree.
        # Maps element IDs to each elements' dictionary form.
        bspElementsDict = OrderedDict()
        
        # Build the BSP elements dictionary.
        for i, bspElement in enumerate(bspElements):
            if bspElement['type'] == BSPNode.__name__:
                # Correct the node references to hold IDs rather than actual 
                # references.
                bspElement['left'] = bspElement['left'].id
                bspElement['right'] = bspElement['right'].id
                
            bspElementsDict[i] = bspElement
            
        # Build the BSP master dictionary.
        bspDict = OrderedDict(
                (
                    ('maxWidth', self.maxWidth),
                    ('maxHeight', self.maxHeight),
                    ('elements', bspElementsDict),
                )
            )
            
        # Ensure that the BSP dictionary only contains strings.
        bspDict = str_items(bspDict)
        
        return format_vdf(OrderedDict(BSP=bspDict))
        
    def iter_elements(self):
        ''' Returns a iterator over all elements in the BSP tree. '''
        
        nodeStack = [self.head]
        while nodeStack:
            node = nodeStack.pop()
            
            assert isinstance(node, BSPElement)
            
            if type(node) is BSPNode:
                nodeStack.append(node.left)
                nodeStack.append(node.right)
                
            yield node
            
    def iter_leaves(self):
        ''' Returns an iterator over all BSP leaves in the BSP tree. '''
        return (
            elem for elem in self.iter_elements()
            if type(elem) is BSPLeaf
        )
        
    def iter_visleaves(self):
        ''' Returns an iterator over all non-solid BSP leaves in the BSP tree.
        '''
        return (leaf for leaf in self.iter_leaves() if not leaf.solid)
        
    def iter_nodes(self):
        ''' Returns an iterator over all BSP nodes in the BSP tree. '''
        return (
            elem for elem in self.iter_elements()
            if type(elem) is BSPNode
        )
        
    def generate_portals(self):
        ''' Populates the 'portals' attribute with a set of newly-instantiated 
        BSPPortal instances, built from the current state of the BSP tree's 
        geometry. Also populates the corresponding visleaves' 'portals' 
        attributes with sets containing references to their respective 
        portals.
        
        '''
        
        # Ensure that all visleaves' portal sets are empty.
        for visleaf in self.iter_visleaves():
            visleaf.portals.clear()
            
        # A set of (unordered) visleaf pairs that have already been processed.
        alreadyProcessed = set()
        
        # Build the portal sets.
        self.portals.clear()
        for visleaf in self.iter_visleaves():
            for neighbor in visleaf.iter_neighbors():
                if neighbor.solid:
                    continue    # Only process visleaf pairs.
                    
                pair = frozenset({visleaf, neighbor})
                
                if pair in alreadyProcessed:
                    continue
                    
                portal = BSPPortal(visleaf, neighbor)
                alreadyProcessed.add(pair)
                
                self.portals.add(portal)
                visleaf.portals.add(portal)
                neighbor.portals.add(portal)
                
    def load_portals(self, portalDict):
        ''' Loads portals from a dictionary of portal instances, and uses 
        those to re-populate the BSP tree's set of portals, as well as the 
        visleaves' portal sets.
        
        '''
        
        # Ensure that all visleaves' portal sets are empty.
        for visleaf in self.iter_visleaves():
            visleaf.portals.clear()
            
        self.portals.clear()
        for portal in portalDict.itervalues():
            self.portals.add(portal)
            portal.leaf1.portals.add(portal)
            portal.leaf2.portals.add(portal)
            
    def load_visibility_matrix(self, visMatrix):
        ''' Loads a visibility matrix and uses it to construct the PVS of each 
        visleaf.
        
        '''
        
        # Clear the PVS of every visleaf.
        for visleaf in self.iter_visleaves():
            visleaf.pvs.clear()
            
        # Rebuild each PVS from the visibility matrix.
        for visleaf1, visleaf2 in product(self.iter_visleaves(), repeat=2):
            if visMatrix[visleaf1.leafID][visleaf2.leafID]:
                visleaf1.pvs.add(visleaf2)
                
    def draw_leaves(self, canvas):
        for leaf in self.iter_leaves():
            leaf.draw(canvas)
            
    def draw_partitions(self, canvas):
        for node in self.iter_nodes():
            node.draw_partition(canvas)
            
    def leaf_from_coords(self, x, y):
        ''' Given a set of coordinates, return the corresponding BSP leaf. '''
        
        node = self.head
        
        while 1:
            assert isinstance(node, BSPElement)
            
            if type(node) is BSPLeaf:
                return node
                
            elif type(node) is BSPNode:
                if node.orientation == BSPNode.Orientation.HORIZ:
                    if y >= node.partition:
                        node = node.right
                    else:
                        node = node.left
                        
                elif node.orientation == BSPNode.Orientation.VERTI:
                    if x >= node.partition:
                        node = node.right
                    else:
                        node = node.left
                        
                else:
                    assert False    # Invalid orientation.
                    
            else:
                assert False    # Invalid node type.
                
        assert False    # Should never break from loop body.
        
    def divide_leaf(self, leaf, orientation, partition):
        ''' Given a BSP leaf, divide that leaf into a BSP node with two leaf 
        children using the given partition and orientation.
        
        '''
        
        if leaf.parent is None:
            assert leaf is self.head
            self.head = BSPNode(None, leaf.bounds, orientation, partition)
            
        else:
            parent = leaf.parent
            
            assert leaf is parent.left or leaf is parent.right
            
            assert (
                orientation != BSPNode.Orientation.VERTI or
                leaf.bounds[0] < partition < leaf.bounds[2]
            )
            
            assert (
                orientation != BSPNode.Orientation.HORIZ or
                leaf.bounds[1] < partition < leaf.bounds[3]
            )
            
            newNode = BSPNode(parent, leaf.bounds, orientation, partition)
            
            if leaf is parent.left:
                parent.left = newNode
            elif leaf is parent.right:
                parent.right = newNode
            else:
                assert False
                
            assert parent.left.parent is parent
            assert parent.right.parent is parent
            
    def merge_leaf(self, leaf):
        ''' Consolidate all children of a given BSP leaf's parent into a 
        single BSP leaf.
        
        '''
        
        try:
            parent = leaf.parent
            
            if parent is None:
                return
            elif parent is self.head:
                bounds = (0, 0, self.maxWidth, self.maxHeight)
                self.head = BSPLeaf(None, bounds)
                return
                
            parentParent = parent.parent
            
            if parent is parentParent.right:
                parentParent.right = BSPLeaf(parentParent, parent.bounds)
            elif parent is parentParent.left:
                parentParent.left = BSPLeaf(parentParent, parent.bounds)
            else:
                assert False
                
        finally:
            # Manually GC reference cycles here because there is a very good 
            # chance that we created unreachable references while merging.
            gc.collect()
            
    def segment_collision(self, startPos, endPos):
        ''' Returns the first solid leaf that the given line segment collides
        with, if any. Returns None if the line does not collide with any solid 
        leaf.
        
        '''
        
        def point_on_edge(point, bounds):
            ''' Takes a point and four boundaries, and determines whether or 
            not the point is located along any of the boundary edges.
            
            '''
            
            pointX, pointY = point
            left, top, right, bottom = bounds
            
            return (
                (pointY in (top, bottom) and left <= pointX <= right) or
                (pointX in (left, right) and top <= pointY <= bottom)
            )
            
        def node_seg_collision(node, startPos, endPos):
            ''' Takes a node whose bounds are located somewhere along the 
            given line segment, and returns the first solid child of this node 
            that collides with the line segment. If the node is a leaf, 
            returns the leaf if it is solid. If there are no collisions, 
            returns None.
            
            '''
            
            # I really don't want to think about trying to implement this with 
            # stack iteration, unlike all my other tree-traversal algorithms. 
            # It's a hell of a lot easier to think about this one recursively, 
            # and the performance really doesn't seem too horrible as it is, 
            # anyway. Something something premature optimization something 
            # root of all evil... *cough*
            
            if type(node) is BSPLeaf:
                # There is a collision if the leaf is solid.
                return node if node.solid else None
                
                # A precondition of this function is that the node is located 
                # somewhere along the segment's path. This precondition is 
                # never explicitly checked, so it is technically possible that 
                # we might return a bad result in this clause, if we directly 
                # call this base case on a leaf without recursing from the 
                # head element, and the segment happens to miss the leaf.
                
                # Thankfully, we are not going to be stupid enough to make 
                # that kind of call..... Right...? Right?!!
                
            elif type(node) is BSPNode:
                startX, startY = startPos
                endX, endY = endPos
                
                if node.orientation == BSPNode.Orientation.HORIZ:
                    checkValues = (startY, endY)
                elif node.orientation == BSPNode.Orientation.VERTI:
                    checkValues = (startX, endX)
                else:
                    assert False    # Invalid orientation.
                    
                # Check if the line segment starts and ends on the same side 
                # of the partition.
                if (checkValues[0] < node.partition
                        and checkValues[1] < node.partition):
                    return node_seg_collision(node.left, startPos, endPos)
                    
                elif (checkValues[0] >= node.partition
                        and checkValues[1] >= node.partition):
                    return node_seg_collision(node.right, startPos, endPos)
                    
                # The line segment straddles this node's partition.
                else:
                    # First, we need to clip the line segment where it 
                    # intersects the node's partition, to prevent false-
                    # collision problems.
                    if node.orientation == BSPNode.Orientation.HORIZ:
                        ratio = (
                            float(node.partition - startY)
                            / float(endY - startY)
                        )   # Short length to long length ratio
                        
                        splitX = float(endX - startX) * ratio + float(startX)
                        splitPoint = (splitX, float(node.partition))
                        
                    elif node.orientation == BSPNode.Orientation.VERTI:
                        ratio = (
                            float(node.partition - startX)
                            / float(endX - startX)
                        )   # Short length to long length ratio
                        
                        splitY = float(endY - startY) * ratio + float(startY)
                        splitPoint = (float(node.partition), splitY)
                        
                    else:
                        assert False    # Invalid orientation.
                        
                    if checkValues[0] < node.partition:
                        startChild = node.left
                        endChild = node.right
                    else:
                        startChild = node.right
                        endChild = node.left
                        
                    # Check the child on the start side for collisions.
                    result = node_seg_collision(
                            startChild,
                            startPos, splitPoint,
                        )
                        
                    if result:
                        return result
                        
                    # Nothing on the start child's side. Try the end child.
                    result = node_seg_collision(
                            endChild,
                            splitPoint, endPos,
                        )
                        
                    if result:
                        return result
                        
                    # No collisions were found.
                    return None
                    
            else:
                assert False    # Invalid type.
                
            ###############################
            # End of node_seg_collision() #
            ###############################
            
        # Nudge the start point over if the line is moving "backwards" in 
        # either direction, to avoid (some) false-collision corner cases. It 
        # won't eliminate all of them, but it should eliminate at least enough 
        # for LOS calculation routines to not completely screw up.
        if endPos[0] < startPos[0]:
            startPos = (startPos[0] - 1, startPos[1])
            
        if endPos[1] < startPos[1]:
            startPos = (startPos[0], startPos[1] - 1)
            
        return node_seg_collision(self.head, startPos, endPos)
        
        
class BSPElement(object):
    """ Base class for BSP Nodes and Leaves. """
    
    def __init__(self, parent, bounds):
        self.parent = parent
        self.bounds = bounds
        
        # Temporary unique element ID to be used until we serialize the tree.
        self.id = id(self)
        
    @classmethod
    def get_bounds_from_dict(cls, elemDict):
        ''' Retrieve the bounds data from a serialized BSPElement. '''
        
        boundsDict = elemDict['bounds']
        
        return (
            int(boundsDict['left']),
            int(boundsDict['top']),
            int(boundsDict['right']),
            int(boundsDict['bottom']),
        )
        
    def to_dict(self):
        return OrderedDict(
                bounds=OrderedDict(
                        (
                            ('left', self.bounds[0]),
                            ('top', self.bounds[1]),
                            ('right', self.bounds[2]),
                            ('bottom', self.bounds[3]),
                        )
                    )
            )
            
    def get_top_left(self):
        return (self.bounds[0], self.bounds[1])
        
    def get_bottom_right(self):
        return (self.bounds[2], self.bounds[3])
        
    def get_width(self):
        return self.bounds[2] - self.bounds[0]
        
    def get_height(self):
        return self.bounds[3] - self.bounds[1]
        
    def get_size(self):
        return (self.get_width(), self.get_height())
        
        
class BSPNode(BSPElement):
    """ Represents a non-leaf node in the BSP Tree. Always has two children.
    """
    
    class Orientation:
        HORIZ = 0
        VERTI = 1
        
    def __init__(self, parent, bounds, orientation, partition):
        super(BSPNode, self).__init__(parent, bounds)
        
        self.orientation = orientation
        self.partition = partition
        
        left, top, right, bottom = bounds
        
        if orientation == BSPNode.Orientation.VERTI:
            leftBounds = (left, top, partition, bottom)
            rightBounds = (partition, top, right, bottom)
            
        elif orientation == BSPNode.Orientation.HORIZ:
            leftBounds = (left, top, right, partition)
            rightBounds = (left, partition, right, bottom)
            
        self.left = BSPLeaf(self, leftBounds)
        self.right = BSPLeaf(self, rightBounds)
        
        assert self.left.parent is self
        assert self.right.parent is self
        
    def __repr__(self):
        return "BSPNode({}, {})".format(self.orientation, self.partition)
        
    def __str__(self):
        return "BSPNode<{}, {}>".format(self.left, self.right)
        
    @classmethod
    def from_dict(cls, nodeDict):
        bounds = cls.get_bounds_from_dict(nodeDict)
        
        orientation = int(nodeDict['orientation'])
        partition = int(nodeDict['partition'])
        
        return cls(None, bounds, orientation, partition)
        
    def to_dict(self):
        bspNodeDict = super(BSPNode, self).to_dict()
        
        bspNodeDict.update(
                OrderedDict(
                        (
                            ('type', type(self).__name__),
                            ('orientation', self.orientation),
                            ('partition', self.partition),
                            ('left', self.left),
                            ('right', self.right),
                        )
                    )
            )
            
        return bspNodeDict
        
    def draw_partition(self, canvas):
        left, top, right, bottom = self.bounds
        
        partition = self.partition
        
        if self.orientation == BSPNode.Orientation.HORIZ:
            start = (left, partition)
            end = (right, partition)
            
        elif self.orientation == BSPNode.Orientation.VERTI:
            start = (partition, top)
            end = (partition, bottom)
            
        else:
            assert False
            
        canvas.draw_line(start, end, COLOR_MAGENTA)
        
    def straddles_segment(self, startPos, endPos):
        ''' Returns whether or not the given line segment directly straddles 
        this node's partition (and vice versa).
        
        '''
        
        if self.orientation == BSPNode.Orientation.HORIZ:
            partitionStart = (self.bounds[0], self.partition)
            partitionEnd = (self.bounds[2], self.partition)
        elif self.orientation == BSPNode.Orientation.VERTI:
            partitionStart = (self.partition, self.bounds[1])
            partitionEnd = (self.partition, self.bounds[3])
        else:
            assert False
            
        return segments_intersect(
                (startPos, endPos),
                (partitionStart, partitionEnd),
            )
            
            
class BSPLeaf(BSPElement):
    """ Represents a leaf in the BSP Tree. """
    
    # The number of BSP leaves that have ever been instantiated during this 
    # session. Used pretty much only to generate temporary sequential BSPLeaf 
    # IDs.
    _numLeaves = 0
    
    def __init__(self, parent, bounds):
        super(BSPLeaf, self).__init__(parent, bounds)
        
        # Non-solid leaves are called 'visleaves'.
        # Solid leaves are just called 'solid leaves'.
        self.solid = True
        
        # Temporarily give myself a unique sequential BSPLeaf ID, distinct 
        # from my BSPElement ID, for the purposes of representation in the 
        # visibility matrix. Only really applicable to visleaves.
        self.leafID = BSPLeaf._numLeaves
        BSPLeaf._numLeaves += 1
        
        # The temporary leafID will be overwritten to be something more 
        # reasonable upon serialization. The 'reasonable' ID will also be 
        # preserved upon deserialization.
        
        # Holds a set of BSP portals that correspond to this leaf, if this 
        # leaf is a visleaf. This set is populated by the BSPTree's 
        # .generate_portals() method.
        self.portals = set()
        
        # The potentially visible set of this leaf. This set is populated by 
        # the BSPTree's .load_visibility_matrix() method.
        self.pvs = set()
        
    def __repr__(self):
        return "BSPLeaf({}, {})".format(repr(self.parent), self.bounds)
        
    def __str__(self):
        return "BSPLeaf<leafID: {}; solid: {}>".format(
                self.leafID, self.solid
            )
            
    @classmethod
    def from_dict(cls, leafDict):
        bounds = cls.get_bounds_from_dict(leafDict)
        
        solid = leafDict['solid']
        
        assert solid in (str(True), str(False))
        
        # There's a new leeeeaf your neighbor's turned oooover...
        # ... over and oooover, clover by clooooverrrrr.....
        newLeaf = cls(None, bounds)
        newLeaf.leafID = int(leafDict['leafID'])
        newLeaf.solid = (solid == str(True))
        
        return newLeaf
        
    def to_dict(self):
        bspLeafDict = super(BSPLeaf, self).to_dict()
        
        bspLeafDict.update(
                (
                    ('type', type(self).__name__),
                    ('leafID', self.leafID),
                    ('solid', self.solid),
                )
            )
            
        return bspLeafDict
        
    def draw(self, canvas):
        color = COLOR_BLACK if self.solid else COLOR_WHITE
        canvas.fill_box(self.get_top_left(), self.get_bottom_right(), color)
        
    def iter_corners(self):
        ''' Returns an iterator over the four corners of this leaf. '''
        return (
            (x, y)
            for x in (self.bounds[0], self.bounds[2])
                for y in (self.bounds[1], self.bounds[3])
        )
        
    def _iter_directed_neighbors(self, direction):
        ''' Returns an iterator over all neighbors in a particular 
        direction relative to this leaf.
        
        '''
        
        # Procedure to get left neighbors:
        # 1. Move upward until we approach a vertical node from the right.
        #   This is the nearest common ancestor node.
        #   - If we must recurse upward and there is no parent, then there are 
        #       no left neighbors. Return an empty list/stop iteration.
        # 2. Recurse downward from the left child of the ancestor node. If we 
        #   reach a leaf, add the leaf to the left neighbor list. If we
        #   reach a horizontal node, recurse on both children. If we reach 
        #   a vertical node, recurse on the right child only.
        # 3. Eliminate non-neighbors by boundaries. Leaves whose bottoms are
        #   less than the target's top, or whose tops are greater than the 
        #   target's bottom, are not neighbors.
        
        # Extend the procedure to get right, top, and bottom neighbors as 
        # necessary.
        
        assert direction in ('L', 'R', 'T', 'B')
        
        # Travel upward until we approach a node of a particular 
        # orientation from a particular direction.
        # The node that we approach is the common ancestor node of all 
        # leaves that are potentially neighbors.
        commonAncestor = None
        node = self
        
        while node.parent:
            if direction == 'L':
                if (node.parent.orientation == BSPNode.Orientation.VERTI
                        and node is node.parent.right):
                    commonAncestor = node.parent
                    break
                    
            elif direction == 'R':
                if (node.parent.orientation == BSPNode.Orientation.VERTI
                        and node is node.parent.left):
                    commonAncestor = node.parent
                    break
                    
            elif direction == 'T':
                if (node.parent.orientation == BSPNode.Orientation.HORIZ
                        and node is node.parent.right):
                    commonAncestor = node.parent
                    break
                    
            elif direction == 'B':
                if (node.parent.orientation == BSPNode.Orientation.HORIZ
                        and node is node.parent.left):
                    commonAncestor = node.parent
                    break
                    
            else:
                assert False
                
            node = node.parent
            
        if not commonAncestor:
            # Common ancestor node not found.
            # There are no adjacent leaves in this direction.
            return
            
        # Initialize the tree traversal stack.
        if direction in ('L', 'T'):
            nodeStack = [commonAncestor.left]
        elif direction in ('R', 'B'):
            nodeStack = [commonAncestor.right]
        else:
            assert False
            
        # Traverse the tree downwards from the common ancestor's child.
        while nodeStack:
            node = nodeStack.pop()
            
            if type(node) is BSPLeaf:
                # Only yield the leaf if its bounds intersect ours.
                if direction in ('L', 'R'):
                    if not (node.bounds[3] <= self.bounds[1]
                            or node.bounds[1] >= self.bounds[3]):
                        yield node
                        
                elif direction in ('T', 'B'):
                    if not (node.bounds[2] <= self.bounds[0]
                            or node.bounds[0] >= self.bounds[2]):
                        yield node
                        
                else:
                    assert False
                    
            elif type(node) is BSPNode:
                if direction == 'L':
                    if node.orientation == BSPNode.Orientation.VERTI:
                        nodeStack.append(node.right)
                        
                    elif node.orientation == BSPNode.Orientation.HORIZ:
                        nodeStack.append(node.left)
                        nodeStack.append(node.right)
                        
                    else:
                        assert False
                        
                elif direction == 'R':
                    if node.orientation == BSPNode.Orientation.VERTI:
                        nodeStack.append(node.left)
                        
                    elif node.orientation == BSPNode.Orientation.HORIZ:
                        nodeStack.append(node.left)
                        nodeStack.append(node.right)
                        
                    else:
                        assert False
                        
                elif direction == 'T':
                    if node.orientation == BSPNode.Orientation.HORIZ:
                        nodeStack.append(node.right)
                        
                    elif node.orientation == BSPNode.Orientation.VERTI:
                        nodeStack.append(node.left)
                        nodeStack.append(node.right)
                        
                    else:
                        assert False
                        
                elif direction == 'B':
                    if node.orientation == BSPNode.Orientation.HORIZ:
                        nodeStack.append(node.left)
                        
                    elif node.orientation == BSPNode.Orientation.VERTI:
                        nodeStack.append(node.left)
                        nodeStack.append(node.right)
                        
                    else:
                        assert False
                        
                else:
                    # The direction is invalid.
                    assert False
                    
            else:
                # The node is neither a BSPLeaf nor a BSPNode.
                assert False
                
    def iter_left_neighbors(self):
        ''' Returns an iterator over all neighbors to the left of this leaf.
        '''
        return self._iter_directed_neighbors('L')
        
    def iter_top_neighbors(self):
        ''' Returns an iterator over all neighbors above this leaf. '''
        return self._iter_directed_neighbors('T')
        
    def iter_right_neighbors(self):
        ''' Returns an iterator over all neighbors to the right of this leaf.
        '''
        return self._iter_directed_neighbors('R')
        
    def iter_bottom_neighbors(self):
        ''' Returns an iterator over all neighbors below this leaf. '''
        return self._iter_directed_neighbors('B')
        
    def iter_neighbors(self):
        ''' Returns an iterator over all neighbor leaves that are directly 
        touching this leaf.
        
        '''
        
        return (
            neighbor
            for neighbors in (
                        self._iter_directed_neighbors(direction)
                        for direction in ('L', 'T', 'R', 'B')
                    )
                for neighbor in neighbors
        )
        # Python generator expressions are beautiful.
        
    def is_neighbor_of(self, other):
        ''' Returns whether or not this leaf is a neighbor of some other leaf.
        '''
        return self in other.iter_neighbors()
        
    def is_left_neighbor_of(self, other):
        ''' Returns whether or not this leaf is a left neighbor of some other 
        leaf.
        
        '''
        
        return self in other.iter_left_neighbors()
        
    def is_top_neighbor_of(self, other):
        ''' Returns whether or not this leaf is a top neighbor of some other 
        leaf.
        
        '''
        
        return self in other.iter_top_neighbors()
        
    def is_right_neighbor_of(self, other):
        ''' Returns whether or not this leaf is a right neighbor of some other 
        leaf.
        
        '''
        
        return self in other.iter_right_neighbors()
        
    def is_bottom_neighbor_of(self, other):
        ''' Returns whether or not this leaf is a bottom neighbor of some 
        other leaf.
        
        '''
        
        return self in other.iter_bottom_neighbors()
        
        
class BSPPortal(object):
    """ A bidirectional link between two non-solid BSP leaves. """
    
    def __init__(self, leaf1, leaf2):
        # The leaves must be visleaves (i.e. they must be non-solid).
        assert not leaf1.solid
        assert not leaf2.solid
        
        self.leaf1 = leaf1
        self.leaf2 = leaf2
        
        if leaf1.is_left_neighbor_of(leaf2):
            neighborRelation = 'L'
            startX = endX = leaf1.bounds[2]
            
        elif leaf1.is_top_neighbor_of(leaf2):
            neighborRelation = 'T'
            startY = endY = leaf1.bounds[3]
            
        elif leaf1.is_right_neighbor_of(leaf2):
            neighborRelation = 'R'
            startX = endX = leaf1.bounds[0]
            
        elif leaf1.is_bottom_neighbor_of(leaf2):
            neighborRelation = 'B'
            startY = endY = leaf1.bounds[1]
            
        else:
            assert False
            
        if neighborRelation in ('L', 'R'):
            self.orientation = BSPNode.Orientation.VERTI
            
            startY = max(leaf1.bounds[1], leaf2.bounds[1])
            endY = min(leaf1.bounds[3], leaf2.bounds[3])
            
        elif neighborRelation in ('T', 'B'):
            self.orientation = BSPNode.Orientation.HORIZ
            
            startX = max(leaf1.bounds[0], leaf2.bounds[0])
            endX = min(leaf1.bounds[2], leaf2.bounds[2])
            
        else:
            assert False
            
        self.start = (startX, startY)
        self.end = (endX, endY)
        
    def __repr__(self):
        return "BSPPortal({}, {})".format(
                repr(self.leaf1), repr(self.leaf2)
            )
            
    def __str__(self):
        return "<BSPPortal {} <-> {}; start: {}; end: {}>".format(
                self.leaf1.leafID, self.leaf2.leafID,
                self.start, self.end,
            )
            
    def get_other(self, leaf):
        if leaf is self.leaf1:
            return self.leaf2
            
        elif leaf is self.leaf2:
            return self.leaf1
            
        else:
            assert False
            
    def iter_critical_LOS_points(self, otherPortal):
        ''' Takes another portal and, based on the start and end points of 
        that portal, returns an iterator over all points along this portal 
        that should be tested for unobstructed line of sight in order for the 
        two portals to be considered visible to each other.
        
        TODO: Figure out a way to definitively pass the 'narrow' and 'crazy' 
        test cases.
        
        '''
        
        yield self.start
        
        # We only need to do clipping if the other portal has the same 
        # orientation, and at least one of its endpoints is between this 
        # portal's endpoints
        if self.orientation == otherPortal.orientation:
            if self.orientation == BSPNode.Orientation.VERTI:
                startX = self.start[0]
                
                startY = self.start[1]
                endY = self.end[1]
                
                if startY < otherPortal.start[1] < endY:
                    yield (startX, otherPortal.start[1])
                    
                if startY < otherPortal.end[1] < endY:
                    yield (startX, otherPortal.end[1])
                    
            elif self.orientation == BSPNode.Orientation.HORIZ:
                startY = self.start[0]
                
                startX = self.start[1]
                endX = self.end[1]
                
                if startX < otherPortal.start[1] < endX:
                    yield (otherPortal.start[0], startY)
                    
                if startX < otherPortal.end[1] < endX:
                    yield (otherPortal.end[0], startY)
                    
            else:
                assert False
                
        yield self.end
        
        
def segments_intersect(seg1, seg2):
    """ Returns whether or not two line segments intersect. """
    
    def orientation(p1, p2, p3):
        ''' Returns 1 if p1, p2, and p3 are in counterclockwise order, -1 if 
        they are in clockwise order, and 0 if they are collinear.
        
        '''
        
        p1x, p1y = p1
        p2x, p2y = p2
        p3x, p3y = p3
        
        # Line 1: p1 -> p2
        # Line 2: p1 -> p3
        
        result = (p3y - p1y) * (p2x - p1x) - (p3y - p1y) * (p2x - p1x)
        
        if result > 0:
            return 1
        elif result < 0:
            return -1
        else:
            return 0
            
    def point_on_segment(p, segStart, segEnd):
        ''' Determines whether or not the point 'p' is on the given line 
        segment.
        
        '''
        
        px, py = p
        segStartX, segStartY = segStart
        segEndX, segEndY = segEnd
        
        return all(
                (
                    px <= max(segStartX, segEndX),
                    px >= min(segStartX, segEndX),
                    py <= max(segStartY, segEndY),
                    py >= min(segStartY, segEndY),
                )
            )
            
    seg1Start, seg1End = seg1
    seg2Start, seg2End = seg2
    
    o1 = orientation(seg1Start, seg1End, seg2Start)
    o2 = orientation(seg1Start, seg1End, seg2End)
    o3 = orientation(seg2Start, seg2End, seg1Start)
    o4 = orientation(seg2Start, seg2End, seg1End)
    
    if o1 != o2 and o3 != o4:
        return True
        
    else:
        return any(
                (
                    (o1 == 0
                        and point_on_segment(seg2Start, seg1Start, seg1End)),
                    (o2 == 0
                        and point_on_segment(seg2End, seg1Start, seg1End)),
                    (o3 == 0
                        and point_on_segment(seg1Start, seg2Start, seg2End)),
                    (o4 == 0
                        and point_on_segment(seg1End, seg2Start, seg2End)),
                )
            )
            
            