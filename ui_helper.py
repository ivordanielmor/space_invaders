import pygame
from typing import Tuple

# --- Globális beállítások (szükséges konstansok a függvényekhez) ---
WIDTH, HEIGHT = 800, 600

def tint_image(image: pygame.Surface, tint_color: Tuple[int, int, int]) -> pygame.Surface:
    """Színezést alkalmaz egy képre per-pixel módszerrel.

    Paraméterek:
        image (pygame.Surface): A forrás kép, amin a tintelést végrehajtjuk. A felületnek
                                alpha csatornával kell rendelkeznie (convert_alpha által).
        tint_color (Tuple[int, int, int]): RGB szín triple, amelyet rávetítünk a képre.
                                           Minden komponensnek 0..255 közé eső egész számnak kell lennie.

    Visszatérés:
        pygame.Surface: A tinteléssel létrehozott új Surface példány. A forráskép érintetlen marad.

    Mellékhatás:
        - Végigiterál a kép minden pixelén, és ahol a pixel alfa értéke nem nulla,
          ott az adott pixel színét a megadott `tint_color`-ra cseréli, megtartva az eredeti alfa értéket.
        - Lassabb lehet nagy felbontású képeknél, mivel per-pixel műveletet végez Python-szinten.
        - Ha a `tint_color` komponensei kívül esnek a 0..255 tartományon, `ValueError`-t dob.

    Példa:
        tinted = tint_image(player_img, (255, 0, 0))
    """
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
    """Betölti a játékos sprite-ot és beállítja a kezdőpozíciót.

    Paraméterek:
        Nincsenek — a függvény a forrásfájlt ("player.png") és a globális WIDTH, HEIGHT konstansokat használja.

    Visszatérés:
        Tuple[pygame.Surface, pygame.Rect]: A betöltött és méretezett Surface, valamint annak Rect-je,
                                           amelynek `midbottom` attribútuma a képernyő alján középre van helyezve.

    Mellékhatás:
        - Betölti a "player.png" fájlt alpha csatornával (`convert_alpha()`).
        - A sprite-ot kétszeresére skálázza mindkét dimenzióban (`smoothscale`).
        - Létrehoz egy Rect-et és a kezdő pozíciót `rect.midbottom = (WIDTH // 2, HEIGHT - 50)`-ra állítja.
        - Ha a fájl nem található, `pygame.error` vagy `FileNotFoundError` keletkezhet, amelyet a hívónak kell kezelnie.

    Példa:
        player_img, player_rect = load_player()
    """
    img = pygame.image.load("player.png").convert_alpha()
    img = pygame.transform.smoothscale(img, (img.get_width() * 2, img.get_height() * 2))
    rect = img.get_rect()
    rect.midbottom = (WIDTH // 2, HEIGHT - 50)
    return img, rect

def load_enemy() -> pygame.Surface:
    """Betölti az ellenség alap sprite-ját.

    Paraméterek:
        Nincsenek — a függvény a "enemy_spinvaders.png" fájlt használja.

    Visszatérés:
        pygame.Surface: A betöltött enemy sprite alpha csatornával (`convert_alpha()`).

    Mellékhatás:
        - Betölti a megadott képfájlt; ha az hiányzik vagy sérült, `pygame.error` keletkezhet.
        - A függvény nem módosítja a sprite méretét.

    Példa:
        enemy_img = load_enemy()
    """
    return pygame.image.load("enemy_spinvaders.png").convert_alpha()

def load_heart() -> pygame.Surface:
    """Betölti és 32×32-re méretezi az élet szimbólumot.

    Paraméterek:
        Nincsenek — a függvény a "heart.png" fájlt használja.

    Visszatérés:
        pygame.Surface: A 32×32-re átméretezett life/heart sprite.

    Mellékhatás:
        - Betölti a "heart.png" fájlt alpha csatornával és `smoothscale`-lal 32×32-re méretezi.
        - Hibák (fájl hiánya stb.) `pygame.error`-t okozhatnak, amelyet a hívónak kell kezelnie.

    Példa:
        heart_img = load_heart()
    """
    img = pygame.image.load("heart.png").convert_alpha()
    return pygame.transform.smoothscale(img, (32, 32))

def load_powerup_image(image_path: str) -> pygame.Surface:
    """Betölti és 32×32-re méretezi a power-up sprite-ot.

    Paraméterek:
        image_path (str): A betölteni kívánt power-up képfájl elérési útja.

    Visszatérés:
        pygame.Surface: A 32×32 méretű power-up sprite.

    Mellékhatás:
        - Betölti a megadott képfájlt alpha csatornával és 32×32-re skálázza.
        - Ha a fájl nem található, `pygame.error` keletkezhet.

    Példa:
        p_img = load_powerup_image("power_speed.png")
    """
    img = pygame.image.load(image_path).convert_alpha()
    return pygame.transform.smoothscale(img, (32, 32))

def draw_top5(screen: pygame.Surface, font: pygame.font.Font, font_small: pygame.font.Font) -> None:
    """Kirajzolja a Top5 ranglistát a képernyőre (Pygame).

    Paraméterek:
        screen (pygame.Surface): A renderelési célfelület (általában a fő képernyőfelület).
        font (pygame.font.Font): Nagyobb betűtípus a címhez.
        font_small (pygame.font.Font): Kis betűtípus a ranglista soraihoz.

    Visszatérés:
        None

    Mellékhatás:
        - Lokálisan importálja a `load_top5` függvényt a `csv_helper` modulból (ciklikus import elkerüléséhez).
        - Kitölti a képernyőt feketével, kirajzol egy címet és a TOP 5 listát középre igazítva.
        - Ha nincs adat, megjelenít egy üzenetet.
        - Kirajzol egy súgósort (Esc = vissza), majd meghívja a `pygame.display.flip()`-et,
          ami frissíti a teljes képernyőt.
        - A függvény feltételezi, hogy a megadott fontok megfelelően inicializáltak és a `screen`
          érvényes, különben `pygame.error` keletkezhet.

    Példa:
        draw_top5(screen, title_font, small_font)
    """
    from csv_helper import load_top5  # lokális import a ciklikus import elkerüléséhez
    screen.fill((0, 0, 0))
    title = font.render("Ranglista - TOP 5", True, (255, 255, 255))
    screen.blit(title, ((WIDTH - title.get_width()) // 2, 80))

    top = load_top5()
    if not top:
        msg = font_small.render("Még nincs adat a ranglistán.", True, (200, 200, 200))
        screen.blit(msg, ((WIDTH - msg.get_width()) // 2, HEIGHT // 2))
    else:
        for i, (name, score) in enumerate(top, start=1):
            line = font_small.render(f"{i}. {name} — {score} pont", True, (255, 255, 255))
            screen.blit(line, ((WIDTH - line.get_width()) // 2, 160 + i * 40))

    hint = font_small.render("Esc = vissza a főmenübe", True, (180, 180, 180))
    screen.blit(hint, ((WIDTH - hint.get_width()) // 2, HEIGHT - 60))
    pygame.display.flip()
