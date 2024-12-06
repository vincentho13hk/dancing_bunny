import math
import pygame

def blit_rotate(surf, image, pos, originPos, angle):
    """
    Draws 'image' onto 'surf', rotated around a pivot point.
    
    Parameters:
    - surf: The pygame.Surface to draw on.
    - image: The pygame.Surface image to rotate and draw.
    - pos: A tuple (x, y), the world position on 'surf' where the pivot should be placed.
    - originPos: A tuple (ox, oy), the pivot point inside 'image' coordinates 
                 (relative to the image's top-left corner). For example:
                 If pivot is the center of a 64x64 image, originPos would be (32,32).
    - angle: The rotation angle in degrees. Positive angles rotate counter-clockwise.
    
    This function calculates how to position the rotated image so that the 'originPos'
    inside the image stays fixed at 'pos' on the target surface.
    """

    # Get a rectangle of the original image at (pos - originPos)
    # This places the image so that 'originPos' would be at 'pos' if the image were not rotated
    image_rect = image.get_rect(topleft=(pos[0] - originPos[0], pos[1] - originPos[1]))

    # Offset vector from image center to pivot (pos)
    # image_rect.center is the center of the image if placed with top-left at (pos - originPos)
    offset_center_to_pivot = pygame.math.Vector2(pos) - pygame.math.Vector2(image_rect.center)

    # Rotate this offset vector by -angle because:
    # - pygame.transform.rotate() rotates counter-clockwise,
    # - pygame.math.Vector2.rotate() rotates in a way that we need to invert the angle.
    rotated_offset = offset_center_to_pivot.rotate(-angle)

    # The new center of the rotated image is pivot position minus the rotated offset
    rotated_image_center = (pos[0] - rotated_offset.x, pos[1] - rotated_offset.y)

    # Rotate the original image
    rotated_image = pygame.transform.rotate(image, angle)

    # Get the rectangle of the rotated image with the new center
    rotated_image_rect = rotated_image.get_rect(center=rotated_image_center)

    # Blit the rotated image onto the surface
    surf.blit(rotated_image, rotated_image_rect)