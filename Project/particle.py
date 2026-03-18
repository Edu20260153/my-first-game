import pygame
import random
import math
import colorsys

pygame.init()

WIDTH, HEIGHT = 1100, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Optimized Ultra Particle Engine")

clock = pygame.time.Clock()

MAX_PARTICLES = 2000
particles = []
stars = []

trail = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

time = 0


# -------------------------
# STARFIELD
# -------------------------

class Star:

    def __init__(self):

        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)

        self.z = random.random() * 2 + 0.5

    def update(self):

        self.y += self.z

        if self.y > HEIGHT:
            self.y = 0
            self.x = random.randint(0, WIDTH)

    def draw(self):

        c = int(150 * self.z)

        # 색상 범위 보호
        c = max(0, min(255, c))

        radius = max(1, int(self.z * 2))

        pygame.draw.circle(
            screen,
            (c, c, c),
            (int(self.x), int(self.y)),
            radius
        )


# -------------------------
# PARTICLE
# -------------------------

class Particle:

    def __init__(self, x, y):

        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(2, 8)

        self.x = x
        self.y = y

        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed

        self.life = random.randint(120, 200)

        self.size = random.uniform(2, 5)

        self.hue = random.random()

        self.trail = []

    def update(self):

        global time

        mx, my = pygame.mouse.get_pos()

        dx = mx - self.x
        dy = my - self.y

        dist2 = dx * dx + dy * dy

        # 블랙홀
        if dist2 < 40000:

            force = 0.0005

            self.vx += dx * force
            self.vy += dy * force

        # 소용돌이
        angle = math.atan2(dy, dx) + math.pi / 2

        self.vx += math.cos(angle) * 0.2
        self.vy += math.sin(angle) * 0.2

        # 노이즈
        self.vx += math.sin(self.y * 0.01 + time) * 0.05
        self.vy += math.cos(self.x * 0.01 + time) * 0.05

        # 중력
        self.vy += 0.04

        # 이동
        self.x += self.vx
        self.y += self.vy

        # 마찰
        self.vx *= 0.99
        self.vy *= 0.99

        # 트레일
        self.trail.append((self.x, self.y))

        if len(self.trail) > 6:
            self.trail.pop(0)

        self.life -= 1
        self.hue += 0.01

    def draw(self):

        if self.life <= 0:
            return

        rgb = colorsys.hsv_to_rgb(self.hue % 1, 1, 1)

        color = (
            int(max(0, min(255, rgb[0] * 255))),
            int(max(0, min(255, rgb[1] * 255))),
            int(max(0, min(255, rgb[2] * 255)))
        )

        # trail
        for i, pos in enumerate(self.trail):

            alpha = int(100 * (i / len(self.trail)))

            pygame.draw.circle(
                glow,
                (*color, alpha),
                (int(pos[0]), int(pos[1])),
                int(self.size)
            )

        # glow
        for i in range(3):

            pygame.draw.circle(
                glow,
                (*color, 40),
                (int(self.x), int(self.y)),
                int(self.size + i * 3)
            )

        pygame.draw.circle(
            screen,
            color,
            (int(self.x), int(self.y)),
            int(self.size)
        )

    def alive(self):
        return self.life > 0


# -------------------------
# CREATE STARS
# -------------------------

for _ in range(120):
    stars.append(Star())


# -------------------------
# EXPLOSION
# -------------------------

def explosion(x, y):

    count = 200

    if len(particles) + count > MAX_PARTICLES:
        count = MAX_PARTICLES - len(particles)

    for _ in range(count):

        particles.append(Particle(x, y))


# -------------------------
# MAIN LOOP
# -------------------------

running = True

while running:

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:

            explosion(*pygame.mouse.get_pos())

    mouse = pygame.mouse.get_pos()
    buttons = pygame.mouse.get_pressed()

    if buttons[0]:

        for _ in range(15):

            if len(particles) < MAX_PARTICLES:

                particles.append(
                    Particle(mouse[0], mouse[1])
                )

    time += 0.03

    trail.fill((0, 0, 0, 35))
    screen.blit(trail, (0, 0))

    # stars
    for s in stars:
        s.update()
        s.draw()

    glow.fill((0, 0, 0, 0))

    # particles update
    alive_particles = []

    for p in particles:

        p.update()

        if p.alive():

            p.draw()
            alive_particles.append(p)

    particles = alive_particles

    # -------------------------
    # optimized particle lines
    # -------------------------

    step = 12

    for i in range(0, len(particles), step):

        p1 = particles[i]

        for j in range(i + step, len(particles), step):

            p2 = particles[j]

            dx = p1.x - p2.x
            dy = p1.y - p2.y

            if dx * dx + dy * dy < 9000:

                pygame.draw.line(
                    glow,
                    (120, 120, 255, 40),
                    (p1.x, p1.y),
                    (p2.x, p2.y),
                    1
                )

    # bloom
    screen.blit(glow, (0, 0), special_flags=pygame.BLEND_ADD)

    pygame.display.flip()

    clock.tick(60)

pygame.quit()