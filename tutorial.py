import pygame

WIDTH, HEIGHT = 1920, 1080

def handle_tutorial_rendering(screen, ui_font, title_font, countdown_font, phase, tutorial_count, now, ready_timer):
    # PHASE_TUTORIAL Text
    if phase == -0:  # PHASE_TUTORIAL
        t1 = ui_font.render("USE YOUR GREEN OBJECT TO MOVE THE CROSSHAIR OVER THE GHOST TO REGISTER A HIT.", True, (255, 230, 150))
        t2 = ui_font.render(f"TRAINING GHOSTS WHACKED: {tutorial_count}/5", True, (180, 255, 200))
        screen.blit(t1, (WIDTH // 2 - t1.get_width() // 2, 60))
        screen.blit(t2, (WIDTH // 2 - t2.get_width() // 2, 128))

    # PHASE_INSTRUCT Layout
    elif phase == 1:  # PHASE_INSTRUCT
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA).convert_alpha()
        dim.fill((10, 8, 20, 130)); screen.blit(dim, (0, 0)) 
        i1 = title_font.render("TUTORIAL COMPLETE - PHASE TWO ENGAGED", True, (255, 215, 0))
        i2 = ui_font.render("-> You have 30 seconds to clear as many ghosts as possible.", True, (240, 240, 255))
        i3 = ui_font.render("-> Level Clear Target: 15 ghosts minimum required to purge.", True, (240, 240, 255))
        i4 = ui_font.render("-> WARNING: Avoid the Jack-o'-Lantern decoys! Hitting them loses 1 point.", True, (255, 100, 100))
        i5 = ui_font.render("-> HINT: Pace yourself! The game speed increases every few seconds.", True, (100, 200, 255))
        i6 = title_font.render("SHOW AN OK SIGN TO CONTINUE", True, (0, 255, 150))
        screen.blit(i1, (WIDTH // 2 - i1.get_width() // 2, 200)) # Title
        screen.blit(i2, (WIDTH // 2 - i2.get_width() // 2, 350)) # Rule 1
        screen.blit(i3, (WIDTH // 2 - i3.get_width() // 2, 410)) # Rule 2
        screen.blit(i4, (WIDTH // 2 - i4.get_width() // 2, 470)) # WARNING (i4 comes before i5 now)
        screen.blit(i5, (WIDTH // 2 - i5.get_width() // 2, 530)) # HINT
        
        screen.blit(i6, (WIDTH // 2 - i6.get_width() // 2, 680))

    # PHASE_PREPARE Countdown
    elif phase == 2:  # PHASE_PREPARE
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA).convert_alpha()
        dim.fill((15, 10, 25, 130)); screen.blit(dim, (0, 0)) 
        seconds_remaining = max(1, 5 - (now - ready_timer) // 1000)
        p_text = title_font.render("GET READY!", True, (255, 69, 0))
        c_text = countdown_font.render(str(seconds_remaining), True, (255, 255, 255))
        screen.blit(p_text, (WIDTH // 2 - p_text.get_width() // 2, HEIGHT // 2 - 210))
        screen.blit(c_text, (WIDTH // 2 - c_text.get_width() // 2, HEIGHT // 2 - 30))