import pygame
import random
import math
import colorsys

pygame.init()
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("ULTRA PARTICLE FX")

clock = pygame.time.Clock()

particles = []

# 트레일 효과용 반투명 레이어
trail = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

time = 0

class Particle:

    def __init__(self, x, y):

        self.x = x
        self.y = y

        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(2, 8)

        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed

        self.life = random.randint(50, 120)

        self.size = random.randint(3, 6)

        self.hue = random.random()

    def update(self):

        global time

        dx = pygame.mouse.get_pos()[0] - self.x
        dy = pygame.mouse.get_pos()[1] - self.y
        dist = math.hypot(dx, dy)

        # 마우스 소용돌이 힘
        if dist < 120:
            force = 0.4
            angle = math.atan2(dy, dx) + math.pi/2
            self.vx += math.cos(angle) * force
            self.vy += math.sin(angle) * force

        self.x += self.vx
        self.y += self.vy

        self.vy += 0.05
        self.vx *= 0.99
        self.vy *= 0.99

        self.life -= 1
        self.hue += 0.01

    def draw(self, surf):

        if self.life <= 0:
            return

        rgb = colorsys.hsv_to_rgb(self.hue % 1, 1, 1)
        color = [int(c * 255) for c in rgb]

        # glow
        for i in range(3):
            pygame.draw.circle(
                surf,
                (*color, 40),
                (int(self.x), int(self.y)),
                self.size + i * 4
            )

        pygame.draw.circle(
            surf,
            color,
            (int(self.x), int(self.y)),
            self.size
        )

    def alive(self):
        return self.life > 0


running = True

while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # 폭발
        if event.type == pygame.MOUSEBUTTONDOWN:
            for _ in range(120):
                particles.append(Particle(*pygame.mouse.get_pos()))

    mouse = pygame.mouse.get_pos()
    buttons = pygame.mouse.get_pressed()

    if buttons[0]:
        for _ in range(12):
            particles.append(Particle(mouse[0], mouse[1]))

    time += 0.02

    # 배경 트레일
    trail.fill((0, 0, 0, 25))
    screen.blit(trail, (0, 0))

    for p in particles:
        p.update()
        p.draw(screen)

    particles = [p for p in particles if p.alive()]

    pygame.display.flip()
    clock.tick(60)

pygame.quit()