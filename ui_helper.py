import pygame
from typing import Tuple

   # --- Globális beállítások (szükséges konstansok a függvényekhez) ---
WIDTH, HEIGHT = 800, 600

def tint_image(image: pygame.Surface, tint_color: Tuple[int, int, int]) -> pygame.Surface:
       """Színezést alkalmaz egy képre per-pixel módszerrel."""
       if any(c < 0 or c > 255 for c in tint_color):
           raise ValueError("tint_color komponenseknek 0..255 között kell lenniük")
       tinted_image = image.copy()
       for x in range(image.get_width()):
           for y in range(image.get_height()):
               pixel = image.get_at((x, y))
               if pixel.a != 0:
                   tinted_image.set_at((x, y), pygame.Color(*tint_color, pixel.a))
       return tinted_image

def load_player() -> Tuple[pygame.Surface, pygame.Rect]:
    """Betölti a játékos sprite-ot és beállítja a kezdőpozíciót."""
    img = pygame.image.load("player.png").convert_alpha()
    img = pygame.transform.smoothscale(img, (img.get_width() * 2, img.get_height() * 2))
    rect = img.get_rect()
    rect.midbottom = (WIDTH // 2, HEIGHT - 50)
    return img, rect

def load_enemy() -> pygame.Surface:
    """Betölti az ellenség alap sprite-ját."""
    return pygame.image.load("enemy_spinvaders.png").convert_alpha()

def load_heart() -> pygame.Surface:
    """Betölti és 32×32-re méretezi az élet szimbólumot."""
    img = pygame.image.load("heart.png").convert_alpha()
    return pygame.transform.smoothscale(img, (32, 32))

def load_powerup_image(image_path: str) -> pygame.Surface:
    """Betölti és 32×32-re méretezi a power-up sprite-ot."""
    img = pygame.image.load(image_path).convert_alpha()
    return pygame.transform.smoothscale(img, (32, 32))
