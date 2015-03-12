import os
import sys
import math

import pygame

from bsp import BSPTree, BSPNode

# BLOCK_SIZE = 16
BLOCK_SIZE = 32
# BLOCK_SIZE = 64

# BL_WIDTH = 64
# BL_HEIGHT = 48

BL_WIDTH = 32
BL_HEIGHT = 24

# BL_WIDTH = 16
# BL_HEIGHT = 12

WIDTH = BL_WIDTH * BLOCK_SIZE
HEIGHT = BL_HEIGHT * BLOCK_SIZE

# WIDTH = 1024
# HEIGHT = 768

FRAMERATE = 60

# Angle of the viewcone, in degrees.
fovDegrees = 135

# Convert that to radians.
FOV = math.radians(fovDegrees)

COLOR_BLACK = (0, 0, 0)
COLOR_GRAY = (128, 128, 128)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (255, 0, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_BLUE = (0, 0, 255)
COLOR_CYAN = (0, 255, 255)
COLOR_MAGENTA = (255, 0, 255)
COLOR_YELLOW = (255, 255, 0)

_bspTree = None


def new_coord_rebaser(base):
    """ Curried coordinate rebase function. Takes a set of base coordinates 
    and returns a function that can be used to convert absolute coordinates 
    to coordinates relative to the given base.
    
    """
    
    def rebaser(absCoords):
        ''' Takes a set of absolute coordinates and returns a new set of 
        coordinates relative to the original base coordinates.
        
        '''
        
        return (absCoords[0] - base[0], absCoords[1] - base[1])
        
    return rebaser
    
    
def normal_from_lineseg(seg):
    """ Returns a normal vector with respect to the given line segment. """
    
    start, end = seg
    
    x1, y1 = start
    x2, y2 = end
    
    dx = x2 - x1
    dy = y2 - y1
    
    return (dy, -dx)
    
    
def dot(a, b):
    """ Returns the dot product of two vectors. """
    return a[0] * b[0] + a[1] * b[1]
    
    
def sign(n):
    """ Returns -1 if n is negative, 1 if n is positive, and 0 otherwise. """
    if n > 0:
        return 1
    elif n < 0:
        return -1
    else:
        return 0
        
        
def intersect_line_ray(lineSeg, raySeg):
    """ Constructs a line from the start and end points of a given line 
    segment, and finds the intersection between that line and a ray 
    constructed from the start and end points of a given ray segment.
    
    If there is no intersection (i.e. the ray goes in the opposite direction 
    or the ray is parallel to the line), returns None.
    
    """
    
    lineStart, lineEnd = lineSeg
    rayStart, rayEnd = raySeg
    
    lineVector = (lineEnd[0] - lineStart[0], lineEnd[1] - lineStart[1])
    rayVector = (rayEnd[0] - rayStart[0], rayEnd[1] - rayStart[1])
    
    p1x, p1y = lineStart
    p2x, p2y = rayStart
    
    d1x, d1y = lineVector
    d2x, d2y = rayVector
    
    # Check if the ray is parallel to the line.
    parallel = (
        (d1x == 0 and d2x == 0)
        or ((d1x != 0 and d2x != 0) and
            (float(d1y) / d1x == float(d2y) / d2x))
    )
    
    intersection = None
    
    # Only non-parallel lines can ever intersect.
    if not parallel:
        # Parametrize the line and ray to find the intersection.
        parameter = (
            float(p2y * d1x - p1y * d1x - p2x * d1y + p1x * d1y)
            / (d2x * d1y - d1x * d2y)
        )
        
        # Only consider intersections that occur in front of the ray.
        if parameter >= 0:
            intersection = (
                p2x + parameter * d2x,
                p2y + parameter * d2y,
            )
            
    return intersection
    
    
def fill_surface_within_viewcone(surface, viewconeLeft, viewconeRight):
    """ Takes a Pygame surface and fills it with white pixels everywhere 
    between and in front of the given viewcone line segments. The viewcone 
    line segment coordinates are expected to be respective to the given 
    surface's expected offset (i.e. the segments need to be rebased with 
    respect to the top-left corner of the visleaf that corresponds to the 
    given surface).
    
    """
    
    surfWidth = surface.get_width()
    surfHeight = surface.get_height()
    
    # The surface's dimensions must be divisible by the block size.
    assert surfWidth % BLOCK_SIZE == 0
    assert surfHeight % BLOCK_SIZE == 0
    
    # Get the viewpoint.
    viewpoint = viewconeLeft[0]
    
    # The left and right line segments must originate from the same point.
    assert viewpoint == viewconeRight[0]
    
    viewpointcoords_from_surfcoords = new_coord_rebaser(viewpoint)
    
    # Get the viewcone normals.
    viewconeLeftNormal = normal_from_lineseg(viewconeLeft)
    viewconeRightNormal = normal_from_lineseg(viewconeRight)
    
    # Populate the block stack with initial blocks.
    blockStack = [
        (BLOCK_SIZE, x, y)
        for y in xrange(0, surfHeight, BLOCK_SIZE)
            for x in xrange(0, surfWidth, BLOCK_SIZE)
    ]
    
    # Quadtree-esque algorithm for fine collision with the viewcone lines.
    while blockStack:
        blockSize, x, y = blockStack.pop()
        
        # Coordinates relative to the viewpoint.
        relX, relY = viewpointcoords_from_surfcoords((x, y))
        
        firstCorner = (relX, relY)
        leftDotSign = sign(dot(viewconeLeftNormal, firstCorner))
        rightDotSign = sign(dot(viewconeRightNormal, firstCorner))
        
        if blockSize == 1:
            # if leftDotSign in (0, 1) or rightDotSign == -1:
            if leftDotSign == -1 and rightDotSign == 1:
                pos = (x, y)
                pygame.draw.line(surface, COLOR_WHITE, pos, pos)
                
            continue
            
        otherCorners = (
            (relX + blockSize, relY),
            (relX, relY + blockSize),
            (relX + blockSize, relY + blockSize),
        )
        
        collision = False
        for corner in otherCorners:
            cornerLeftDotSign = sign(dot(viewconeLeftNormal, corner))
            cornerRightDotSign = sign(dot(viewconeRightNormal, corner))
            
            leftCollision = cornerLeftDotSign != leftDotSign
            rightCollision = cornerRightDotSign != rightDotSign
            
            if leftCollision or rightCollision:
                # Collision with a viewcone line detected.
                
                if not (leftCollision and rightCollision):
                    # Ignore the collision if the block is behind the viewcone 
                    # frustum.
                    if ((leftCollision and rightDotSign == -1)
                            or (rightCollision and leftDotSign == 1)):
                        continue
                        
                newBlockSize = blockSize / 2
                
                blockStack.append(
                        (newBlockSize, x, y)
                    )
                blockStack.append(
                        (newBlockSize, x + newBlockSize, y)
                    )
                blockStack.append(
                        (newBlockSize, x, y + newBlockSize)
                    )
                blockStack.append(
                        (newBlockSize, x + newBlockSize, y + newBlockSize)
                    )
                    
                collision = True
                break
                
        if not collision:
            # No collision detected. Color the block if it falls within the 
            # viewcone.
            
            if leftDotSign == -1 and rightDotSign == 1:
                rect = pygame.Rect((x, y), (blockSize, blockSize))
                pygame.draw.rect(surface, COLOR_WHITE, rect, 0)
                
                
def portal_within_viewcone(portal, viewconeLeft, viewconeRight):
    """ Returns whether or not the given portal is visible within the given 
    viewcone boundaries. Assumes that the viewcone segments use absolute 
    coordinates.
    
    """
    
    # Get the viewpoint.
    viewpoint = viewconeLeft[0]
    
    # The left and right line segments must originate from the same point.
    assert viewpoint == viewconeRight[0]
    
    intersectLeft = intersect_line_ray(
            (portal.start, portal.end),
            viewconeLeft,
        )
        
    intersectRight = intersect_line_ray(
            (portal.start, portal.end),
            viewconeRight,
        )
        
    # if intersectLeft:
        # pygame.draw.circle(
                # overlay, COLOR_BLUE,
                # (int(intersectLeft[0]), int(intersectLeft[1])),
                # 5,
            # )
            
    # if intersectRight:
        # pygame.draw.circle(
                # overlay, COLOR_RED,
                # (int(intersectRight[0]), int(intersectRight[1])),
                # 3,
            # )
            
    if intersectLeft and intersectRight:
        intersectLeftBounded = (
            int(min(max(intersectLeft[0], portal.start[0]), portal.end[0])),
            int(min(max(intersectLeft[1], portal.start[1]), portal.end[1])),
        )
        
        intersectRightBounded = (
            int(min(max(intersectRight[0], portal.start[0]), portal.end[0])),
            int(min(max(intersectRight[1], portal.start[1]), portal.end[1])),
        )
        
        return (
            intersectLeftBounded[0] - intersectRightBounded[0] != 0 or
            intersectLeftBounded[1] - intersectRightBounded[1] != 0
        )
        
        # return (
            # (
                # (intersectLeft[0] <= portal.start[0] <= intersectRight[0]) or
                # (intersectLeft[0] >= portal.start[0] >= intersectRight[0])
            # )
            # and (
                # (intersectLeft[1] <= portal.start[1] <= intersectRight[1]) or
                # (intersectLeft[1] >= portal.start[1] >= intersectRight[1])
            # )
            # or
            # (
                # (intersectLeft[0] <= portal.end[0] <= intersectRight[0]) or
                # (intersectLeft[0] >= portal.end[0] >= intersectRight[0])
            # )
            # and (
                # (intersectLeft[1] <= portal.end[1] <= intersectRight[1]) or
                # (intersectLeft[1] >= portal.end[1] >= intersectRight[1])
            # )
        # )
        
    elif intersectLeft and not intersectRight:
        return True
        
    elif not intersectLeft and intersectRight:
        return True
        
    elif not intersectLeft and not intersectRight:
        return False
        
    # viewcoords_from_abscoords = new_coord_rebaser(viewpoint)
    
    # portalStart = viewcoords_from_abscoords(portal.start)
    # portalEnd = viewcoords_from_abscoords(portal.end)
    
    # # Get the viewcone normals.
    # viewconeLeftNormal = normal_from_lineseg(viewconeLeft)
    # viewconeRightNormal = normal_from_lineseg(viewconeRight)
    
    if 0:   # DEBUG
        rebase = new_coord_rebaser((-200, -200))
        
        pygame.draw.circle(overlay, COLOR_YELLOW, (200, 200), 5)
        
        pygame.draw.line(
                overlay, COLOR_CYAN,
                rebase(portalStart), rebase(portalEnd),
            )
            
        pygame.draw.line(
                overlay, COLOR_CYAN,
                (200, 200), rebase(portalStart),
            )
            
        pygame.draw.line(
                overlay, COLOR_CYAN,
                (200, 200), rebase(portalEnd),
            )
            
        pygame.draw.line(
                overlay, COLOR_BLUE,
                (200, 200),
                rebase(
                        (
                            viewconeLeftNormal[0] * 100,
                            viewconeLeftNormal[1] * 100
                        )
                    ),
            )
            
        pygame.draw.line(
                overlay, COLOR_MAGENTA,
                (200, 200),
                rebase(
                        (
                            viewconeRightNormal[0] * 100,
                            viewconeRightNormal[1] * 100,
                        )
                    ),
            )
            
    # return (
        # (dot(viewconeLeftNormal, portalStart) < 0 and
            # dot(viewconeRightNormal, portalStart) > 0)
        # or (dot(viewconeLeftNormal, portalEnd) < 0 and
            # dot(viewconeRightNormal, portalEnd) > 0)
    # )
    
    assert False
    
    # if portal.orientation == BSPNode.Orientation.VERTI:
        # if viewpoint[0] < portal.start[0]:
            # return (
                # dot(viewconeLeftNormal, portalEnd) < 0 and
                # dot(viewconeRightNormal, portalStart) > 0
            # )
        # elif viewpoint[0] >= portal.start[0]:
            # return (
                # dot(viewconeLeftNormal, portalStart) < 0 and
                # dot(viewconeRightNormal, portalEnd) > 0
            # )
            
    # elif portal.orientation == BSPNode.Orientation.HORIZ:
        # if viewpoint[1] < portal.start[1]:
            # return (
                # dot(viewconeLeftNormal, portalStart) < 0 and
                # dot(viewconeRightNormal, portalEnd) > 0
            # )
        # elif viewpoint[1] >= portal.start[1]:
            # return (
                # dot(viewconeLeftNormal, portalEnd) < 0 and
                # dot(viewconeRightNormal, portalStart) > 0
            # )
            
    # else:
        # assert False
        
        
def restrict_viewcone(portal, viewconeLeft, viewconeRight):
    """ Returns a new set of viewcone line segments that are restricted to fit 
    through the given portal. If the viewcone already fits through the given 
    portal, a set of equivalent viewcone line segments are returned.
    
    Assumes that the viewcone line segments are based with respect to the 
    absolute coordinate system.
    
    """
    
    # Get the viewcone endpoints.
    viewconeLeftStart, viewconeLeftEnd = viewconeLeft
    viewconeRightStart, viewconeRightEnd = viewconeRight
    
    # The left and right line segments must originate from the same point.
    assert viewconeLeftStart == viewconeRightStart
    
    intersectLeft = intersect_line_ray(
            (portal.start, portal.end),
            viewconeLeft,
        )
        
    if intersectLeft is None:
        if portal.orientation == BSPNode.Orientation.VERTI:
            if viewconeLeftStart[0] < portal.start[0]:
                newViewconeLeft = (viewconeLeftStart, portal.start)
            elif viewconeLeftStart[0] >= portal.start[0]:
                newViewconeLeft = (viewconeLeftStart, portal.end)
                
        elif portal.orientation == BSPNode.Orientation.HORIZ:
            if viewconeLeftStart[1] < portal.start[1]:
                newViewconeLeft = (viewconeLeftStart, portal.end)
            elif viewconeLeftStart[1] >= portal.start[1]:
                newViewconeLeft = (viewconeLeftStart, portal.start)
                
        else:
            assert False    # Invalid orientation.
            
    else:
        newViewconeLeft = (
            viewconeLeftStart,
            (
                min(max(intersectLeft[0], portal.start[0]), portal.end[0]),
                min(max(intersectLeft[1], portal.start[1]), portal.end[1]),
            ),
        )
        
    intersectRight = intersect_line_ray(
            (portal.start, portal.end),
            viewconeRight,
        )
        
    if intersectRight is None:
        if portal.orientation == BSPNode.Orientation.VERTI:
            if viewconeRightStart[0] < portal.start[0]:
                newViewconeRight = (viewconeRightStart, portal.end)
            elif viewconeRightStart[0] >= portal.start[0]:
                newViewconeRight = (viewconeRightStart, portal.start)
                
        elif portal.orientation == BSPNode.Orientation.HORIZ:
            if viewconeRightStart[1] < portal.start[1]:
                newViewconeRight = (viewconeRightStart, portal.start)
            elif viewconeRightStart[1] >= portal.start[1]:
                newViewconeRight = (viewconeRightStart, portal.end)
                
        else:
            assert False    # Invalid orientation.
            
    else:
        newViewconeRight = (
            viewconeRightStart,
            (
                min(max(intersectRight[0], portal.start[0]), portal.end[0]),
                min(max(intersectRight[1], portal.start[1]), portal.end[1]),
            ),
        )
        
    return newViewconeLeft, newViewconeRight
    
    
def build_shroud(viewPos, viewTarget):
    """ Takes a viewing position and a view target position, calculates the 
    shroudmap for all leaves visible from that target position and angle, and 
    returns a dictionary that maps visible leaves to their shroudmaps.
    
    """
    
    # Calculate the viewing vector.
    viewVector = (viewTarget[1] - viewPos[1], viewTarget[0] - viewPos[0])
    
    # Determine the viewcone line segment boundaries.
    
    halfFOV = FOV * 0.5
    
    viewAngle = math.atan2(viewVector[1], viewVector[0]) % (2 * math.pi)
    
    viewconeLeftAngle = viewAngle + halfFOV
    viewconeRightAngle = viewAngle - halfFOV
    
    viewconeLeft = (
        viewPos,
        (
            math.sin(viewconeLeftAngle) + viewPos[0],
            math.cos(viewconeLeftAngle) + viewPos[1],
        ),
    )
    
    viewconeRight = (
        viewPos,
        (
            math.sin(viewconeRightAngle) + viewPos[0],
            math.cos(viewconeRightAngle) + viewPos[1],
        ),
    )
    
    # Determine player visleaf.
    playerLeaf = _bspTree.leaf_from_coords(*viewPos)
    
    shroudmapDict = {}
    
    # A set of all portals that we have already processed.
    alreadyProcessedPortals = set()
    
    visleafStack = [(playerLeaf, viewconeLeft, viewconeRight)]
    
    while visleafStack:
        visleaf, viewconeLeft, viewconeRight = visleafStack.pop()
        
        if visleaf not in shroudmapDict:
            shroudmap = pygame.Surface(
                    (visleaf.get_width(), visleaf.get_height())
                )
            shroudmap.fill(COLOR_BLACK)
            shroudmap.set_colorkey(COLOR_WHITE)
            shroudmapDict[visleaf] = shroudmap
            
        else:
            shroudmap = shroudmapDict[visleaf]
            
        leafcoords_from_abscoords = new_coord_rebaser(visleaf.get_top_left())
        
        # Rebase the viewcone vectors with respect to the current visleaf.
        
        visleafViewconeLeft = (
            leafcoords_from_abscoords(viewconeLeft[0]),
            leafcoords_from_abscoords(viewconeLeft[1]),
        )
        
        visleafViewconeRight = (
            leafcoords_from_abscoords(viewconeRight[0]),
            leafcoords_from_abscoords(viewconeRight[1]),
        )
        
        # Fill the surface with white between the viewcone vectors.
        fill_surface_within_viewcone(
                shroudmap,
                visleafViewconeLeft, visleafViewconeRight,
            )
            
        # Test portals for visibility.
        for portal in visleaf.portals:
            if (portal_within_viewcone(portal, viewconeLeft, viewconeRight)
                    and portal not in alreadyProcessedPortals):
                    
                # Add the portal to the set of already-processed portals.
                alreadyProcessedPortals.add(portal)
                
                # Calculate the new view frustum endpoints.
                newViewconeLeft, newViewconeRight = restrict_viewcone(
                        portal,
                        viewconeLeft, viewconeRight,
                    )
                    
                visleafStack.append(
                        (
                            portal.get_other(visleaf),
                            newViewconeLeft, newViewconeRight,
                        )
                    )
                    
    return shroudmapDict
    
    
def main():
    # Load the relevant BSP file.
    levelName = sys.argv[1]
    bspFilePath = "{}-bsp.vdf".format(levelName)
    
    with open(bspFilePath, 'r') as f:
        data = f.read()
        
    # BSP setup
    global _bspTree
    _bspTree = BSPTree.from_vdf(data)
    _bspTree.generate_portals()
    
    os.environ['SDL_VIDEO_WINDOW_POS'] = '{},{}'.format(100, 100)
    
    # Pygame setup
    pygame.init()
    pygame.display.set_caption("Project VIS Main Runtime")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    
    global overlay
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_colorkey(COLOR_BLACK)
    
    playerPos = (100, 100)
    
    while 1:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                return 0
                
        screen.fill(COLOR_BLACK)
        
        overlay.fill(COLOR_BLACK)
        
        pressedKeys = pygame.key.get_pressed()
        
        if pressedKeys[pygame.K_w]:
            playerPos = (playerPos[0], playerPos[1] - 5)
        if pressedKeys[pygame.K_a]:
            playerPos = (playerPos[0] - 5, playerPos[1])
        if pressedKeys[pygame.K_s]:
            playerPos = (playerPos[0], playerPos[1] + 5)
        if pressedKeys[pygame.K_d]:
            playerPos = (playerPos[0] + 5, playerPos[1])
            
        # Pre-build shroudmaps and mark all visible leaves in the process.
        viewTarget = pygame.mouse.get_pos()
        shroudmapDict = build_shroud(playerPos, viewTarget)
        
        visleafRectDict = {
            visleaf : pygame.Rect(visleaf.get_top_left(), visleaf.get_size())
            for visleaf in shroudmapDict
        }
        
        # Draw texmaps for each marked leaf.
        for visleaf in shroudmapDict.iterkeys():
            pygame.draw.rect(screen, COLOR_WHITE, visleafRectDict[visleaf])
            
        # Draw entities in each marked leaf.
        pygame.draw.circle(screen, COLOR_GREEN, playerPos, 10)
        
        # Draw the lightmap overlay for each marked leaf.
        pass
        
        # Draw shroudmaps over each marked leaf.
        for visleaf, shroudmap in shroudmapDict.iteritems():
            screen.blit(shroudmap, visleafRectDict[visleaf])
            
        if 0:   # DEBUG
            viewPos = playerPos
            
            viewVector = (viewTarget[1] - viewPos[1], viewTarget[0] - viewPos[0])
            
            halfFOV = FOV * 0.5
            
            viewAngle = math.atan2(viewVector[1], viewVector[0]) % (2 * math.pi)
            
            viewconeLeftAngle = viewAngle + halfFOV
            viewconeRightAngle = viewAngle - halfFOV
            
            viewconeLeftVector = (
                viewPos,
                (
                    math.sin(viewconeLeftAngle) * 100 + viewPos[0],
                    math.cos(viewconeLeftAngle) * 100 + viewPos[1],
                ),
            )
            
            viewconeRightVector = (
                viewPos,
                (
                    math.sin(viewconeRightAngle) * 100 + viewPos[0],
                    math.cos(viewconeRightAngle) * 100 + viewPos[1],
                ),
            )
            
            pygame.draw.line(screen, COLOR_RED, viewPos, viewTarget)
            pygame.draw.line(screen, COLOR_RED, viewPos, viewconeLeftVector[1])
            pygame.draw.line(screen, COLOR_RED, viewPos, viewconeRightVector[1])
            
        if 1:   # DEBUG
            for visleaf in shroudmapDict:
                rect = pygame.Rect(visleaf.get_top_left(), visleaf.get_size())
                pygame.draw.rect(screen, COLOR_RED, rect, 1)
                
        if 0:   # DEBUG
            for portal in _bspTree.portals:
                pygame.draw.circle(screen, COLOR_YELLOW, portal.start, 5)
                
            for portal in _bspTree.portals:
                pygame.draw.circle(screen, COLOR_RED, portal.end, 3)
                
        screen.blit(overlay, pygame.Rect(0, 0, WIDTH, HEIGHT))
        pygame.display.update()
        
        clock.tick(FRAMERATE)
        
    return 0
    
    
if __name__ == '__main__':
    sys.exit(main())
    