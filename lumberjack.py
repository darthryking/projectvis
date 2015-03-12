import sys

import graphics
from bsp import BSPTree, BSPElement, BSPNode, BSPLeaf

BLOCK_SIZE = 32

BL_WIDTH = 32
BL_HEIGHT = 24

WIDTH = BL_WIDTH * BLOCK_SIZE
HEIGHT = BL_HEIGHT * BLOCK_SIZE

FRAMERATE = 60

COLOR_BLACK = (0, 0, 0)
COLOR_GRAY = (128, 128, 128)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (255, 0, 0)
COLOR_MAGENTA = (255, 0, 255)
COLOR_CYAN = (0, 255, 255)


def draw_grid(canvas):
    for i in xrange(BL_WIDTH):
        x = i * BLOCK_SIZE
        
        start = (x, 0)
        end = (x, HEIGHT)
        
        canvas.draw_line(start, end, COLOR_GRAY)
        
    for i in xrange(BL_HEIGHT):
        y = i * BLOCK_SIZE
        
        start = (0, y)
        end = (WIDTH, y)
        
        canvas.draw_line(start, end, COLOR_GRAY)
        
        
def snap_to_grid(x, y):
    """ Returns the grid line intersection nearest to the given point. """
    return (
        int(round(float(x) / BLOCK_SIZE) * BLOCK_SIZE),
        int(round(float(y) / BLOCK_SIZE) * BLOCK_SIZE),
    )
    
    
def main():
    c = graphics.Canvas(WIDTH, HEIGHT)
    c.show()
    
    c.set_title("Lumberjack Tree Carver")
    
    if len(sys.argv) > 1:
        bspFilePath = sys.argv[1]
        
        with open(bspFilePath, 'r') as f:
            data = f.read()
            
        b = BSPTree.from_vdf(data)
        
    else:
        bspFilePath = 'out-bsp.vdf'
        b = BSPTree(WIDTH, HEIGHT)
        
    startPos = None
    
    clickLock = False
    
    while c.is_active():
        mousePos = c.get_mouse_pos()
        snappedCoords = snap_to_grid(*mousePos)
        
        b.draw_leaves(c)
        
        draw_grid(c)
        
        b.draw_partitions(c)
        
        leaf = b.leaf_from_coords(*mousePos)
        
        assert leaf
        
        # for neighbor in leaf.iter_neighbors():
            # c.draw_box(
                    # neighbor.get_top_left(),
                    # neighbor.get_bottom_right(),
                    # COLOR_CYAN,
                # )
                
        c.draw_box(leaf.get_top_left(), leaf.get_bottom_right(), COLOR_RED)
        
        keysPressed = c.get_keys_pressed()
        
        if c.get_mouse_l():
            if not startPos:
                startPos = snappedCoords
                
        elif c.get_mouse_r():
            if not clickLock:
                leaf.solid = not leaf.solid
                clickLock = True
                
        elif keysPressed['delete']:
            if not clickLock:
                b.merge_leaf(leaf)
                clickLock = True
                
        elif keysPressed['left ctrl'] and keysPressed['s']:
            if not clickLock:
                with open(bspFilePath, 'w') as f:
                    f.write(b.to_vdf())
                clickLock = True
                
        else:
            if startPos:
                endPos = snappedCoords
                
                if startPos != endPos:
                    left, top, right, bottom = leaf.bounds
                    
                    if startPos[0] == endPos[0]:
                        orientation = BSPNode.Orientation.VERTI
                        partition = startPos[0]
                        
                        if not (left < partition < right):
                            partition = None
                            
                    elif startPos[1] == endPos[1]:
                        orientation = BSPNode.Orientation.HORIZ
                        partition = startPos[1]
                        
                        if not (top < partition < bottom):
                            partition = None
                            
                    else:
                        orientation = None
                        partition = None
                        
                    if None not in (orientation, partition):
                        b.divide_leaf(leaf, orientation, partition)
                        
                    startPos = None
                    
            if clickLock:
                clickLock = False
                
        if startPos:
            c.draw_line(startPos, snappedCoords, COLOR_MAGENTA)
            
        c.fill_circle(snappedCoords, 5, COLOR_RED)
        
        c.refresh()
        
        graphics.wait_framerate(FRAMERATE)
        
    return 0
    
    
if __name__ == '__main__':
    sys.exit(main())
    