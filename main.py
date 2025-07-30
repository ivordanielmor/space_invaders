# HÁZI FELADAT
# Adj a játékosnak lövés-lehetőséget: amikor a Space billentyűt lenyomod,
# jelenjen meg egy fehér pont (pl. pygame.draw.circle) a sprite tetején!

import pygame

def load_player():
    img = pygame.image.load("player.png").convert_alpha()
    img = pygame.transform.smoothscale(img, (img.get_width()*2, img.get_height()*2))
    rect = img.get_rect()
    rect.midbottom = (WIDTH // 2, HEIGHT)
    return img, rect

def move_player(rect, keys, speed):
    if keys[pygame.K_LEFT]: rect.x -= speed
    if keys[pygame.K_RIGHT]: rect.x += speed
    rect.left = max(rect.left, 0)
    rect.right = min(rect.right, WIDTH)

def shoot(keys, rect, bullets):
    if keys[pygame.K_SPACE]:
        bullets.append([rect.centerx, rect.top])

def move_bullets(bullets, speed):
    for b in bullets: b[1] -= speed
    bullets[:] = [b for b in bullets if b[1] > 0]

def main():
    pygame.init()
    global WIDTH, HEIGHT
    WIDTH, HEIGHT = 800, 600
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    player_img, player_rect = load_player()
    bullets = []
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        keys = pygame.key.get_pressed()
        move_player(player_rect, keys, 5)
        shoot(keys, player_rect, bullets)
        move_bullets(bullets, 10)

        screen.fill((0,0,0))
        screen.blit(player_img, player_rect)
        for b in bullets:
            pygame.draw.circle(screen, (255,255,255), b, 5)
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()

if __name__ == "__main__":
    main()