import pygame
import sys
import math
import random

RADIUS = 20
WIDTH, HEIGHT = 800, 600

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dodge Game")

bac_color = (0, 0, 0)
color = (255, 255, 255)

clock = pygame.time.Clock()
running = True

# 물리 값들
ACCELERATION = 5000.0
FRICTION = 4000.0
MAX_SPEED = 400.0

# 플레이어
pos = [400.0, 300.0]
vel = [0.0, 0.0]

# 탄
BULLET_RADIUS = 8
BASE_BULLET_SPEED = 250.0
bullets = []

spawn_timer = 0

# 게임 상태
game_over = False
score = 0.0
level = 10

font_small = pygame.font.SysFont(None, 36)
font_big = pygame.font.SysFont(None, 72)


def spawn_bullet():
    side = random.choice(["top", "bottom", "left", "right"])

    if side == "top":
        x = random.uniform(0, WIDTH)
        y = -BULLET_RADIUS
    elif side == "bottom":
        x = random.uniform(0, WIDTH)
        y = HEIGHT + BULLET_RADIUS
    elif side == "left":
        x = -BULLET_RADIUS
        y = random.uniform(0, HEIGHT)
    else:
        x = WIDTH + BULLET_RADIUS
        y = random.uniform(0, HEIGHT)

    dx = pos[0] - x
    dy = pos[1] - y
    length = math.sqrt(dx**2 + dy**2)

    if length != 0:
        dx /= length
        dy /= length

    # 🔥 레벨 기반 속도 증가
    speed = BASE_BULLET_SPEED + level * 40

    bullets.append({
        "pos": [x, y],
        "vel": [dx * speed, dy * speed]
    })


while running:
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    if not game_over:
        # ⏱️ 점수 (생존 시간)
        score += dt

        # 📈 레벨 증가 (5초마다)
        level = int(score // 5) + 1

        keys = pygame.key.get_pressed()

        dir_x = 0
        dir_y = 0

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dir_y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dir_y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dir_x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dir_x += 1

        # 정규화
        length = math.sqrt(dir_x**2 + dir_y**2)
        if length != 0:
            dir_x /= length
            dir_y /= length

            vel[0] += dir_x * ACCELERATION * dt
            vel[1] += dir_y * ACCELERATION * dt
        else:
            speed = math.sqrt(vel[0]**2 + vel[1]**2)
            if speed != 0:
                decel = FRICTION * dt

                if decel > speed:
                    vel = [0.0, 0.0]
                else:
                    vel[0] -= (vel[0] / speed) * decel
                    vel[1] -= (vel[1] / speed) * decel

        # 최대 속도 제한
        speed = math.sqrt(vel[0]**2 + vel[1]**2)
        if speed > MAX_SPEED:
            vel[0] = (vel[0] / speed) * MAX_SPEED
            vel[1] = (vel[1] / speed) * MAX_SPEED

        # 위치 업데이트
        pos[0] += vel[0] * dt
        pos[1] += vel[1] * dt

        # 벽 충돌
        if pos[0] < RADIUS:
            pos[0] = RADIUS
            vel[0] = 0
        elif pos[0] > WIDTH - RADIUS:
            pos[0] = WIDTH - RADIUS
            vel[0] = 0

        if pos[1] < RADIUS:
            pos[1] = RADIUS
            vel[1] = 0
        elif pos[1] > HEIGHT - RADIUS:
            pos[1] = HEIGHT - RADIUS
            vel[1] = 0

        # 🔥 생성 속도 (레벨 올라갈수록 빨라짐)
        spawn_interval = max(0.15, 1.5 - level * 0.1)

        spawn_timer -= dt
        if spawn_timer <= 0:
            spawn_bullet()
            spawn_timer = spawn_interval

        # 🔥 탄 이동
        for b in bullets:
            b["pos"][0] += b["vel"][0] * dt
            b["pos"][1] += b["vel"][1] * dt

        # 🔥 화면 밖 탄 제거 (최적화)
        bullets = [
            b for b in bullets
            if -50 < b["pos"][0] < WIDTH + 50 and -50 < b["pos"][1] < HEIGHT + 50
        ]

        # 🔥 충돌 판정 (sqrt 제거)
        for b in bullets:
            dx = pos[0] - b["pos"][0]
            dy = pos[1] - b["pos"][1]

            if dx*dx + dy*dy < (RADIUS + BULLET_RADIUS) ** 2:
                game_over = True

    # 🎨 그리기
    screen.fill(bac_color)

    pygame.draw.circle(screen, color, (int(pos[0]), int(pos[1])), RADIUS)

    for b in bullets:
        pygame.draw.circle(screen, (255, 0, 0),
                           (int(b["pos"][0]), int(b["pos"][1])), BULLET_RADIUS)

    # 📊 UI 표시
    score_text = font_small.render(f"Score: {int(score)}", True, (255, 255, 255))
    level_text = font_small.render(f"Level: {level}", True, (255, 255, 0))

    screen.blit(score_text, (10, 10))
    screen.blit(level_text, (10, 40))

    if game_over:
        text = font_big.render("GAME OVER", True, (255, 0, 0))
        rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(text, rect)

    pygame.display.flip()

pygame.quit()
sys.exit()