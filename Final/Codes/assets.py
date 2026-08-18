import pygame

# =================================================================
# === CENTRALIZED ASSET STORE ===
# All shared image assets are loaded once here and cached as module-
# level variables, so other modules (tutorial.py, designs.py, etc.)
# can just import and use them directly without repeated disk reads.
#
# IMPORTANT: init_assets() must be called ONCE in main.py, AFTER
# pygame.display.set_mode() has been created — convert_alpha() needs
# an active display surface to work correctly.
# =================================================================

# --- Asset containers (populated by init_assets) ---
ok_sign_img = None


def init_assets():
    """Loads and prepares all shared image assets. Call once at startup."""
    global ok_sign_img

    raw_ok_sign = pygame.image.load(r"C:\Users\rhyan\Desktop\NYP\26S1\EGL314\OpenCV\OpenCV\ok hand sign.png").convert_alpha()

    # Scale proportionally instead of forcing a square, to avoid distortion
    target_height = 180
    aspect_ratio = raw_ok_sign.get_width() / raw_ok_sign.get_height()
    target_width = int(target_height * aspect_ratio)

    ok_sign_img = pygame.transform.smoothscale(raw_ok_sign, (target_width, target_height))

    # === Add more shared assets below as needed ===
    # Example pattern for future images:
    # raw_example = pygame.image.load("assets/example.png").convert_alpha()
    # example_img = pygame.transform.smoothscale(raw_example, (width, height))
