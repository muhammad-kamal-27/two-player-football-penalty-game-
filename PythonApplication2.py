
import os
import sys
import math
import random
import time
try:
    import pygame
except ModuleNotFoundError:
    raise SystemExit("pygame not installed.  Run:  python -m pip install pygame")

WIDTH, HEIGHT = 960, 540
FPS = 60
GOAL_LINE = WIDTH - 180
BALL_START = (80, HEIGHT - 80)

GRAVITY = 0.30
MAX_POWER = 160.0
POWER_RATE = 240.0
MIN_POWER = 10.0
DEFAULT_AIM = 10.0
ANGLE_STEP = 45.0
MIN_ANGLE = -15.0
MAX_ANGLE = 45.0

GOAL_W, GOAL_H = 220, 260
MOTION_TRAIL = 8
SHOTS_PER_PLAYER = 5
# def
def safe_init_mixer():
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        return True
    except pygame.error:
        return False

def load_sound(name):
    if not os.path.exists(name) or not safe_init_mixer():
        return None
    try:
        return pygame.mixer.Sound(name)
    except pygame.error:
        return None

# VISUALS
def get_goal_mouth_rect():
    gx = GOAL_LINE - GOAL_W // 2
    gy = HEIGHT - GOAL_H - 20
    post = 18
    mouth = pygame.Rect(gx + post, gy + post, GOAL_W - post * 2, GOAL_H - post)
    return mouth, gx, gy, post

def create_field():
    surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    top, mid, bottom = (72, 150, 215), (140, 200, 245), (210, 235, 255)
    for y in range(HEIGHT):
        t = y / HEIGHT
        if t < 0.45:
            c = tuple(int(top[i] * (1 - (t / 0.45)) + mid[i] * (t / 0.45)) for i in range(3))
        else:
            tt = (t - 0.45) / 0.55
            c = tuple(int(mid[i] * (1 - tt) + bottom[i] * tt) for i in range(3))
        pygame.draw.line(surf, c, (0, y), (WIDTH, y))
    grass_base = (24, 120, 36)
    surf.fill(grass_base, rect=pygame.Rect(0, HEIGHT // 3, WIDTH, HEIGHT - HEIGHT // 3))
    stripe_w = 96
    for x in range(0, WIDTH, stripe_w):
        shade = 6 if (x // stripe_w) % 2 == 0 else -6
        col = (max(0, grass_base[0] + shade), max(0, grass_base[1] + 20 + shade), max(0, grass_base[2] + shade))
        s = pygame.Surface((stripe_w, HEIGHT - HEIGHT // 3), pygame.SRCALPHA)
        s.fill(col + (24,))
        surf.blit(s, (x, HEIGHT // 3))
    white = (240, 240, 240)
    cx = WIDTH // 2
    pygame.draw.circle(surf, white, (cx, HEIGHT // 2), 72, 2)
    pygame.draw.line(surf, white, (cx, HEIGHT // 3), (cx, HEIGHT - 20), 3)
    pen_w, pen_h = 260, 200
    pen_left = GOAL_LINE - pen_w
    pen_top = HEIGHT - 20 - pen_h
    pygame.draw.rect(surf, white, (pen_left, pen_top, pen_w, pen_h), 2)
    dirt = pygame.Surface((GOAL_W + 60, 36), pygame.SRCALPHA)
    dirt.fill((28, 20, 12, 18))
    surf.blit(dirt, (GOAL_LINE - GOAL_W // 2 - 30, HEIGHT - 56))
    return surf

def soft_shadow(surf, x, y, radius, altitude):
    stretch = 1 + max(0.0, altitude) / max(1, (HEIGHT - y + 1)) * 2.0
    shadow_w = max(2, int(radius * stretch))
    shadow_h = max(2, int(radius * 0.5))
    shadow = pygame.Surface((shadow_w * 2, shadow_h * 2), pygame.SRCALPHA)
    for i in range(shadow_h, 0, -1):
        a = int(160 * (i / shadow_h) ** 2)
        pygame.draw.ellipse(shadow, (0, 0, 0, a), (shadow_w - i, 0, i * 2, shadow_h))
    offset_x = int(0.5 * altitude * 0.35)
    surf.blit(shadow, (x - shadow_w + offset_x, y + 6), special_flags=pygame.BLEND_PREMULTIPLIED)

def draw_goal_simple(surf, cam_x=0, y_offset=0):
    mouth, gx, gy, post = get_goal_mouth_rect()
    gx_s = int(gx - cam_x)
    gy_s = int(gy + y_offset)
    post_w = post
    white = (245, 245, 245)
    depth = 28
    pygame.draw.polygon(surf, (140, 140, 140), [(gx_s + depth, gy_s), (gx_s + depth + post_w, gy_s),
                                               (gx_s + post_w, gy_s + depth), (gx_s, gy_s + depth)])
    pygame.draw.polygon(surf, (140, 140, 140), [(gx_s + depth + GOAL_W - post_w, gy_s),
                                               (gx_s + depth + GOAL_W, gy_s),
                                               (gx_s + GOAL_W, gy_s + depth),
                                               (gx_s + GOAL_W - post_w, gy_s + depth)])
    pygame.draw.rect(surf, white, (gx_s, gy_s, post_w, GOAL_H))
    pygame.draw.rect(surf, white, (gx_s + GOAL_W - post_w, gy_s, post_w, GOAL_H))
    pygame.draw.rect(surf, white, (gx_s, gy_s, GOAL_W, post_w))
    net = pygame.Surface((mouth.w, mouth.h), pygame.SRCALPHA)
    cols, rows = 22, 16
    for i in range(1, cols):
        x = int(i * net.get_width() / cols)
        pygame.draw.line(net, (220, 220, 220, 90), (x, 0), (x, net.get_height()))
    for j in range(1, rows):
        y = int(j * net.get_height() / rows)
        pygame.draw.line(net, (220, 220, 220, 80), (0, y), (net.get_width(), y))
    surf.blit(net, (mouth.x - cam_x, mouth.y + y_offset))

# PARTICLES
class Particle:
    def __init__(self, x, y, color=None):
        self.x, self.y = x, y
        self.vx = random.uniform(-220, 220)
        self.vy = random.uniform(-420, -120)
        self.life = random.uniform(0.8, 2.2)
        self.size = random.randint(2, 7)
        self.color = color or random.choice([(240, 60, 60), (255, 200, 40), (60, 200, 80),
                                             (80, 160, 255), (200, 120, 255)])

    def update(self, dt):
        self.vy += 900 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self, surf, cam_x=0, y_offset=0):
        if self.life > 0:
            a = int(255 * max(0.0, min(1.0, self.life / 1.8)))
            pygame.draw.circle(surf, (*self.color, a), (int(self.x - cam_x), int(self.y + y_offset)), self.size)
#  POST-PROCESSING
def fast_bloom(screen, thresh=255, intensity=0.0):
    if intensity <= 0.0:
        return

def add_film_grain(screen, opacity=4):
    w, h = screen.get_size()
    if w == 0 or h == 0:                       # fix div-zero
        return
    rng = random.Random()
    count = max(2, (w * h) // 20000)
    for _ in range(count):
        x = rng.randrange(w)
        y = rng.randrange(h)
        c = rng.randint(0, opacity)
        screen.fill((c, c, c, c), (x, y, 1, 1))

def create_vignette(intensity=0.38, scale_down=6):
    w, h = WIDTH, HEIGHT
    sw, sh = max(1, w // scale_down), max(1, h // scale_down)
    surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
    cx, cy = (sw - 1) / 2.0, (sh - 1) / 2.0
    maxd = math.hypot(cx, cy)
    for yy in range(sh):
        for xx in range(sw):
            d = math.hypot(xx - cx, yy - cy) / maxd
            alpha = int(255 * max(0.0, min(1.0, (d ** 1.9) * intensity)))
            if alpha:
                surf.set_at((xx, yy), (0, 0, 0, alpha))
    vign = pygame.transform.smoothscale(surf, (w, h))
    return vign
#  BALL 
class Ball:
    def __init__(self):
        self.radius = 18
        self.surface = self._make_ball_surface()
        self.trail = []
        self.reset()

    def reset(self):
        self.x, self.y = float(BALL_START[0]), float(BALL_START[1])
        self.vx = self.vy = 0.0
        self.launched = self.scored = self.goal = self.blocked = False
        self.trail.clear()

    def _make_ball_surface(self):
        r = self.radius
        grad = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for iy in range(r * 2):
            for ix in range(r * 2):
                dx = ix - r
                dy = iy - r
                if dx * dx + dy * dy <= r * r:
                    nd = math.sqrt(dx * dx + (dy * 1.1) * (dy * 1.1))
                    t = nd / (r + 0.0001)
                    shade = int(220 - 60 * t)
                    grad.set_at((ix, iy), (shade, shade, shade, 255))
        pygame.draw.circle(grad, (200, 200, 200), (r, r), r, 2)
        pygame.draw.ellipse(grad, (255, 255, 255, 170), (int(r * 0.2), int(r * 0.12), int(r * 0.8), int(r * 0.5)))
        pts = [(r + r * 0.5 * math.cos(i * math.tau / 5 + math.pi / 2),
                r + r * 0.5 * math.sin(i * math.tau / 5 + math.pi / 2)) for i in range(5)]
        pygame.draw.polygon(grad, (40, 40, 40), pts, 2)
        return pygame.transform.smoothscale(grad, (r * 2, r * 2))

    def shoot(self, power, angle_deg, wind=0.0):
        ratio = max(0.0, min(1.0, (power - MIN_POWER) / (MAX_POWER - MIN_POWER)))
        speed = 8.0 + 50.0 * ratio
        a = math.radians(angle_deg)
        self.vx, self.vy = (speed * math.cos(a) + wind), -speed * math.sin(a)
        self.launched = True
        self.scored = self.goal = self.blocked = False
        self.trail.clear()

    def update(self, dt):
        if self.scored or not self.launched:
            return
        self.trail.append((self.x, self.y))
        if len(self.trail) > MOTION_TRAIL:
            self.trail.pop(0)
        drag = 1.0 - 0.01 * dt * 60.0
        self.vx *= drag
        self.x += self.vx * dt * 60.0
        self.vy += GRAVITY
        self.y += self.vy * dt * 60.0
        mouth, gx, gy, post = get_goal_mouth_rect()
        if not self.goal and mouth.left <= self.x <= mouth.right and mouth.top <= self.y <= mouth.bottom:
            self.goal = True
        ground_y = HEIGHT - 25
        if self.y > ground_y:
            self.y = ground_y
            if abs(self.vy) > 6.0:
                self.vy = -self.vy * 0.45
                self.vx *= 0.7
            else:
                self.vy = 0.0
                friction = 25.0 * dt
                if abs(self.vx) > 0.03:
                    self.vx -= math.copysign(friction, self.vx)
                else:
                    self.vx = 0.0
                    self.scored = True
        if self.x > WIDTH + 400 or self.x < -200:
            self.scored = True
            self.vx = self.vy = 0.0

    def draw(self, surf, cam_x=0, y_offset=0, scale=1.0):
        for idx, (tx, ty) in enumerate(self.trail):
            sx = int(tx - cam_x)
            sy = int(ty + y_offset)
            alpha = int(140 * (1 - idx / max(1, len(self.trail))))
            s = pygame.transform.rotozoom(self.surface, 0, scale * (1.0 - 0.06 * idx))
            s.set_alpha(alpha)
            surf.blit(s, s.get_rect(center=(sx, sy)))
        altitude = max(0, HEIGHT - self.y - 25)
        sx = int(self.x - cam_x)
        sy = int(self.y + y_offset)
        soft_shadow(surf, sx, sy, int(self.radius * scale), altitude)
        angle = -math.degrees(math.atan2(self.vy, max(1e-3, self.vx))) if self.vx or self.vy else 0
        rotated = pygame.transform.rotozoom(self.surface, angle, scale)
        surf.blit(rotated, rotated.get_rect(center=(sx, sy)))
#  GOAL TEXT ANIMATION 
def draw_goal_text(screen, font, text, elapsed, cam_x=0, y_offset=0):
    duration = 2.0
    if elapsed < 0 or elapsed > duration:
        return
    t = elapsed / duration
    ease = 1 - (1 - t) ** 3
    scale = 1.0 + 1.2 * (1 - t) * ease
    angle = math.sin(t * math.pi * 2) * 4 * (1 - t)
    txt_col = (255, 240, 80)
    base = font.render(text, True, txt_col)
    s = pygame.transform.rotozoom(base, angle, max(0.1, scale))
    shadow = font.render(text, True, (20, 20, 20))
    sh = pygame.transform.rotozoom(shadow, angle, max(0.1, scale))
    cx, cy = int(WIDTH // 2 - cam_x * 0.05), int(HEIGHT // 2 - 30 + y_offset * 0.6)
    screen.blit(sh, sh.get_rect(center=(cx + 3, cy + 4)), special_flags=0)
    screen.blit(s, s.get_rect(center=(cx, cy)), special_flags=0)

#  MAIN 
def main():
    pygame.init()
    pygame.font.init()
    safe_init_mixer()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Two-Player Penalty Duel")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 26, bold=True)
    font_small = pygame.font.SysFont("Arial", 16)
    font_goal = pygame.font.SysFont("Impact", 72, bold=True)
    if font_goal is None:                       # fix missing Impact
        font_goal = pygame.font.SysFont("Arial", 72, bold=True)

    kick_snd = load_sound("kick.wav")
    goal_snd = load_sound("goal.wav")

    field = create_field()
    ball = Ball()

    power = MIN_POWER
    charging = False
    aim_angle = DEFAULT_AIM
    particles = []
    goal_time = None

    current_player = 1
    scores = {1: 0, 2: 0}
    shots_left = {1: SHOTS_PER_PLAYER, 2: SHOTS_PER_PLAYER}
    prev_launched = False
    game_over = False
    wind = 0.0

    vignette = create_vignette(intensity=0.38, scale_down=6)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_SPACE:
                    ball.reset()
                    particles.clear()
                    power = MIN_POWER
                    charging = False
                    goal_time = None
                    prev_launched = False

        # ----- simple input / game logic -----------------------------------
        if not ball.launched and not game_over:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP]:
                aim_angle = max(MIN_ANGLE, aim_angle - ANGLE_STEP * dt)
            if keys[pygame.K_DOWN]:
                aim_angle = min(MAX_ANGLE, aim_angle + ANGLE_STEP * dt)
            if keys[pygame.K_RETURN]:
                if not charging:
                    charging = True
                    power = MIN_POWER
                else:
                    power = min(MAX_POWER, power + POWER_RATE * dt)
            else:
                if charging:
                    ball.shoot(power, aim_angle, wind)
                    if kick_snd:
                        kick_snd.play()
                    charging = False
                    power = MIN_POWER

        ball.update(dt)
        for p in particles:
            p.update(dt)
        particles = [p for p in particles if p.life > 0]

        if ball.goal and goal_time is None:
            goal_time = 0
            scores[current_player] += 1
            if goal_snd:
                goal_snd.play()
            for _ in range(60):
                particles.append(Particle(ball.x, ball.y))

        if ball.scored and prev_launched != ball.scored:
            shots_left[current_player] -= 1
            current_player = 2 if current_player == 1 else 1
            if shots_left[1] == 0 and shots_left[2] == 0:
                game_over = True
        prev_launched = ball.scored

        # ----- draw --------------------------------------------------------
        screen.blit(field, (0, 0))
        draw_goal_simple(screen)
        ball.draw(screen)

        for p in particles:
            p.draw(screen)

        if goal_time is not None:
            goal_time += dt
            draw_goal_text(screen, font_goal, "GOAL!", goal_time)

        # ----- HUD ---------------------------------------------------------
        hud_y = 10
        texts = [
            f"Player 1: {scores[1]}   ({shots_left[1]} shots left)",
            f"Player 2: {scores[2]}   ({shots_left[2]} shots left)",
            f"Wind: {wind:.1f}" if abs(wind) > 0.05 else "Wind: calm"
        ]
        for i, txt in enumerate(texts):
            t = font_small.render(txt, True, (40, 40, 40))
            screen.blit(t, (10, hud_y + i * 20))

        if not ball.launched and not game_over:
            angle_txt = f"Aim: {aim_angle:+.0f}°   Power: {power:.0f}"
            t = font.render(angle_txt, True, (220, 220, 220))
            screen.blit(t, t.get_rect(midbottom=(WIDTH // 2, HEIGHT - 10)))

        if game_over:
            winner = 1 if scores[1] > scores[2] else 2 if scores[2] > scores[1] else 0
            if winner == 0:
                msg = "It's a draw!"
            else:
                msg = f"Player {winner} wins!"
            t = font_goal.render(msg, True, (255, 220, 40))
            screen.blit(t, t.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

        add_film_grain(screen, opacity=4)
        screen.blit(vignette, (0, 0), special_flags=pygame.BLEND_PREMULTIPLIED)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()