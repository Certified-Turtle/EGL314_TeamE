import pygame
import assets

WIDTH, HEIGHT = 1920, 1080

# How many frames the crosshair must hover over the button to advance
STAGE_HOVER_TARGET = 90

def handle_stage_clear_screen(screen, ui_font, title_font, cursor_pos, cursor_pos_p2, score, current_stage, stage_passed, stage_targets, hover_progress):
    """Renders the between-stage screen and returns updated hover progress."""
    # Dim overlay
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA).convert_alpha()
    dim.fill((10, 8, 20, 160))
    screen.blit(dim, (0, 0))

    # Stage complete header
    color = (0, 255, 150) if stage_passed else (255, 100, 100)
    label = "STAGE CLEARED!" if stage_passed else "TIME'S UP!"
    header = title_font.render(label, True, color)
    screen.blit(header, (WIDTH // 2 - header.get_width() // 2, 180))

    # Stage number
    stage_txt = ui_font.render(f"STAGE {current_stage} OF 3 COMPLETE", True, (220, 200, 255))
    screen.blit(stage_txt, (WIDTH // 2 - stage_txt.get_width() // 2, 290))

    # Score so far
    score_txt = title_font.render(f"SCORE: {score:02d}", True, (255, 255, 255))
    screen.blit(score_txt, (WIDTH // 2 - score_txt.get_width() // 2, 380))

    # Target result
    target = stage_targets[current_stage]
    if stage_passed:
        result_txt = ui_font.render(f"TARGET MET — {score} / {target} PHANTOMS SWEPT", True, (0, 255, 150))
    else:
        result_txt = ui_font.render(f"TARGET MISSED — {score} / {target} PHANTOMS SWEPT", True, (255, 100, 100))
    screen.blit(result_txt, (WIDTH // 2 - result_txt.get_width() // 2, 480))

    # Next stage preview
    next_stage = current_stage + 1
    next_labels = {2: "STAGE 2 — FASTER PHANTOMS", 3: "STAGE 3 — DANGER MODE (DECOYS ACTIVE)"}
    next_txt = ui_font.render(f"UP NEXT: {next_labels[next_stage]}", True, (255, 200, 80))
    screen.blit(next_txt, (WIDTH // 2 - next_txt.get_width() // 2, 560))

    # Hover-to-continue button
    btn_x, btn_y, btn_w, btn_h = WIDTH // 2 - 200, 660, 400, 80
    fill_w = int(btn_w * (hover_progress / STAGE_HOVER_TARGET))
    pygame.draw.rect(screen, (40, 35, 55), (btn_x, btn_y, btn_w, btn_h), border_radius=10)
    pygame.draw.rect(screen, (0, 200, 120), (btn_x, btn_y, fill_w, btn_h), border_radius=10)
    pygame.draw.rect(screen, (100, 100, 130), (btn_x, btn_y, btn_w, btn_h), width=3, border_radius=10)
    btn_label = ui_font.render("HOVER TO CONTINUE", True, (255, 255, 255))
    screen.blit(btn_label, (btn_x + btn_w // 2 - btn_label.get_width() // 2, btn_y + btn_h // 2 - btn_label.get_height() // 2))

    # Check if crosshair is hovering over button
    cx, cy = cursor_pos
    p1_hovering = btn_x <= cx <= btn_x + btn_w and btn_y <= cy <= btn_y + btn_h

    p2_hovering = False
    if cursor_pos_p2 is not None:
        cx2, cy2 = cursor_pos_p2
        p2_hovering = btn_x <= cx2 <= btn_x + btn_w and btn_y <= cy2 <= btn_y + btn_h

    if p1_hovering or p2_hovering:
        hover_progress = min(STAGE_HOVER_TARGET, hover_progress + 3)
    else:
        hover_progress = max(0, hover_progress - 2)

    return hover_progress


def handle_tutorial_rendering(screen, ui_font, title_font, countdown_font, phase, tutorial_count, now, ready_timer, mp_tutorial_count=0):
    # PHASE_TUTORIAL (single player)
    if phase == 0:  # PHASE_TUTORIAL
        t1 = ui_font.render("USE YOUR GREEN GUN TO MOVE THE CROSSHAIR OVER THE PHANTOM TO REGISTER A HIT.", True, (255, 230, 150))
        t2 = ui_font.render(f"TRAINING PHANTOMS SWEPT: {tutorial_count}/5", True, (180, 255, 200))
        screen.blit(t1, (WIDTH // 2 - t1.get_width() // 2, 60))
        screen.blit(t2, (WIDTH // 2 - t2.get_width() // 2, 128))

    # PHASE_TUTORIAL_MP (multiplayer training)
    elif phase == 5:  # PHASE_TUTORIAL_MP
        t1 = ui_font.render("P1 — USE YOUR GREEN GUN  |  P2 — USE YOUR BLUE GUN", True, (255, 230, 150))
        t2 = ui_font.render("MOVE YOUR CROSSHAIR OVER THE PHANTOM TO REGISTER A HIT.", True, (200, 200, 255))
        t3 = ui_font.render(f"COMBINED HITS: {mp_tutorial_count} / 10", True, (180, 255, 200))
        screen.blit(t1, (WIDTH // 2 - t1.get_width() // 2, 60))
        screen.blit(t2, (WIDTH // 2 - t2.get_width() // 2, 110))
        screen.blit(t3, (WIDTH // 2 - t3.get_width() // 2, 168))

    # PHASE_INSTRUCT Layout
    elif phase == 1:  # PHASE_INSTRUCT
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA).convert_alpha()
        dim.fill((10, 8, 20, 130)); screen.blit(dim, (0, 0))

        bar_center_y = HEIGHT // 2
        bar_height = 40  # placeholder — update once we confirm addons.py's real value

        img = assets.ok_sign_img
        label = title_font.render("SHOW AN OK SIGN TO CONTINUE", True, (0, 255, 150))

        label_y = bar_center_y - (bar_height // 2) - 40 - label.get_height()
        img_y = label_y - 30 - img.get_height()

        img_x = WIDTH // 2 - img.get_width() // 2
        screen.blit(img, (img_x, img_y))
        screen.blit(label, (WIDTH // 2 - label.get_width() // 2, label_y))

    # PHASE_PREPARE Countdown
    elif phase == 2:  # PHASE_PREPARE
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA).convert_alpha()
        dim.fill((15, 10, 25, 130)); screen.blit(dim, (0, 0)) 
        seconds_remaining = max(1, 5 - (now - ready_timer) // 1000)
        p_text = title_font.render("GET READY!", True, (255, 69, 0))
        c_text = countdown_font.render(str(seconds_remaining), True, (255, 255, 255))
        screen.blit(p_text, (WIDTH // 2 - p_text.get_width() // 2, HEIGHT // 2 - 210))
        screen.blit(c_text, (WIDTH // 2 - c_text.get_width() // 2, HEIGHT // 2 - 30))