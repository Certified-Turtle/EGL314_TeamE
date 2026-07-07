import pygame
import random

WIDTH, HEIGHT = 1920, 1080
hole_positions = [(480 + col * 480, 660 + row * 150) for row in range(3) for col in range(3)]

def reset_game():
    # Returns score, time_left, start_ticks, current_hole, game_over
    return 0, 30, pygame.time.get_ticks(), random.choice(hole_positions), False

def render_game_over_screen(screen, score):
    WIDTH, HEIGHT = screen.get_size()
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA).convert_alpha()
    dim.fill((5, 5, 12, 240)); screen.blit(dim, (0, 0))
    
    f1, f2 = pygame.font.SysFont("Courier New", 150, bold=True), pygame.font.SysFont("Courier New", 60, bold=True)
    title_str = "CLEARED!" if score >= 30 else "GAME!"
    title_surf = f1.render(title_str, True, (200, 255, 220) if score >= 30 else (220, 40, 60))
    score_surf = f2.render(f"SPIRITS BANISHED: {score} (Target: 30)", True, (255, 215, 0))
    menu_surf  = f2.render("PRESS [R] TO RE-ENTER OR [Q] TO LEAVE", True, (160, 165, 180))
    
    screen.blit(title_surf, title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 150)))
    screen.blit(score_surf, score_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30)))
    screen.blit(menu_surf, menu_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 180)))