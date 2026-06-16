import pygame
import designs

WIDTH, HEIGHT = 1920, 1080
START_BUTTON_RECT = pygame.Rect(WIDTH//2 - 250, HEIGHT//2 + 80, 500, 160)
HOVER_TO_START_FRAMES = 35

def handle_intro_phase(screen, title_font, ui_font, cursor_pos, hover_progress):
    screen.fill((10, 8, 20))
    
    intro_title = title_font.render("WHACK-A-GHOST SYSTEM", True, (0, 255, 180))
    screen.blit(intro_title, intro_title.get_rect(center=(WIDTH//2, HEIGHT//2 - 180)))
    
    guide_txt = ui_font.render("MOVE THE CROSSHAIR OVER THE BUTTON TO START", True, (170, 185, 200))
    screen.blit(guide_txt, guide_txt.get_rect(center=(WIDTH//2, HEIGHT//2 - 60)))
    
    hovering = START_BUTTON_RECT.collidepoint(cursor_pos[0], cursor_pos[1])
    if hovering:
        hover_progress += 1
    else:
        hover_progress = max(0, hover_progress - 2)
        
    fill_width = int((hover_progress / HOVER_TO_START_FRAMES) * START_BUTTON_RECT.width)
    pygame.draw.rect(screen, (40, 40, 60), START_BUTTON_RECT, border_radius=14)
    if fill_width > 0:
        pygame.draw.rect(screen, (0, 255, 180), (START_BUTTON_RECT.x, START_BUTTON_RECT.y, fill_width, START_BUTTON_RECT.height), border_radius=14)
    pygame.draw.rect(screen, (0, 255, 180), START_BUTTON_RECT, width=4, border_radius=14)
    
    btn_label = "START WHACKING!" if hover_progress < HOVER_TO_START_FRAMES else "INITIATING..."
    btn_text = ui_font.render(btn_label, True, (230, 240, 255))
    screen.blit(btn_text, btn_text.get_rect(center=START_BUTTON_RECT.center))
    
    designs.draw_crosshair(screen, cursor_pos)
    return hover_progress