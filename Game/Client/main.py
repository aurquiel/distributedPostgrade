import pygame
from pathlib import Path

try:
    import cv2
    CV2_AVAILABLE = True
except Exception:
    CV2_AVAILABLE = False

pygame.init()
pygame.mixer.init()

#=========CONTANTS GAME=========
WINDOWS_WIDTH = 1200
WINDOWS_HEIGHT = 800
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
FPS = 60
clock = pygame.time.Clock()
font = pygame.font.SysFont(["Arial", "Liberation Sans", "DejaVu Sans", "Sans"], 24)
title_font = pygame.font.SysFont(["Arial", "Liberation Sans", "DejaVu Sans", "Sans"], 32)

# Window
screen = pygame.display.set_mode((WINDOWS_WIDTH, WINDOWS_HEIGHT))
pygame.display.set_caption("Game Client Menu")

# UI state
runing = True
active_input = None
host_ip = "127.0.0.1"
host_port = "12345"

current_view = "menu"  # menu | config | video | rules
VIDEO_PATH = str(Path(__file__).parent / "assets" / "promo.mp4")
AUDIO_PATH = str(Path(__file__).parent / "assets" / "audio.mp3")

# Buttons (menu)
menu_items = [
    "Start Game",
    "Watch Promo Video",
    "View Rules",
    "Configure Connection"
]
menu_area = pygame.Rect(80, 120, 520, 520)
buttons = []
btn_w, btn_h = 480, 70

# Config panel
ip_rect = pygame.Rect(720, 260, 360, 50)
port_rect = pygame.Rect(720, 340, 360, 50)
back_rect = pygame.Rect(80, 710, 180, 50)

# Video
video_rect = pygame.Rect(80, 140, 1040, 560)
video_cap = None
video_fps = 30
video_frame_ms = 33
video_last_tick = 0
video_last_surface = None
video_duration_ms = 0

def draw_button(rect, text, hovered=False):
    bg = (40, 40, 40) if not hovered else (70, 70, 70)
    pygame.draw.rect(screen, bg, rect, border_radius=6)
    pygame.draw.rect(screen, (90, 90, 90), rect, 2, border_radius=6)
    label = font.render(text, True, WHITE)
    screen.blit(label, (rect.x + 16, rect.y + 14))

def draw_input(rect, text, active=False):
    bg = (30, 30, 30) if not active else (55, 55, 55)
    pygame.draw.rect(screen, bg, rect, border_radius=6)
    pygame.draw.rect(screen, (90, 90, 90), rect, 2, border_radius=6)
    label = font.render(text, True, WHITE)
    screen.blit(label, (rect.x + 12, rect.y + 12))

def open_video():
    global video_cap, video_fps, video_frame_ms, video_last_tick, video_duration_ms, video_last_surface
    video_last_surface = None
    if CV2_AVAILABLE:
        video_cap = cv2.VideoCapture(VIDEO_PATH)
        fps = video_cap.get(cv2.CAP_PROP_FPS)
        video_fps = fps if fps and fps > 0 else 30
        video_frame_ms = int(1000 / video_fps)
        total_frames = int(video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_duration_ms = int((total_frames / video_fps) * 1000) if total_frames > 0 else 0
        video_last_tick = pygame.time.get_ticks()
    else:
        video_cap = None
    # Reproducir audio UNA sola vez
    if Path(AUDIO_PATH).exists():
        pygame.mixer.music.load(AUDIO_PATH)
        pygame.mixer.music.play(0)

def close_video():
    global video_cap
    if video_cap is not None:
        video_cap.release()
        video_cap = None
    pygame.mixer.music.stop()

while runing:
    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            runing = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if current_view == "menu":
                for idx, rect in enumerate(buttons):
                    if rect.collidepoint(event.pos):
                        if idx == 0:
                            # Start Game (placeholder)
                            pass
                        elif idx == 1:
                            current_view = "video"
                            open_video()
                        elif idx == 2:
                            current_view = "rules"
                        elif idx == 3:
                            current_view = "config"

            elif current_view in ("config", "video", "rules"):
                if back_rect.collidepoint(event.pos):
                    if current_view == "video":
                        close_video()
                    current_view = "menu"

            if current_view == "config":
                if ip_rect.collidepoint(event.pos):
                    active_input = "ip"
                elif port_rect.collidepoint(event.pos):
                    active_input = "port"
                else:
                    active_input = None

        if event.type == pygame.KEYDOWN and current_view == "config" and active_input:
            if event.key == pygame.K_BACKSPACE:
                if active_input == "ip":
                    host_ip = host_ip[:-1]
                elif active_input == "port":
                    host_port = host_port[:-1]
            else:
                if active_input == "ip":
                    if len(event.unicode) == 1 and (event.unicode.isdigit() or event.unicode == "."):
                        host_ip += event.unicode
                elif active_input == "port":
                    if len(event.unicode) == 1 and event.unicode.isdigit():
                        host_port += event.unicode

    # Draw background
    screen.fill((15, 15, 15))

    if current_view == "menu":
        title = title_font.render("MAIN MENU", True, WHITE)
        screen.blit(title, (80, 50))

        pygame.draw.rect(screen, (20, 20, 20), menu_area, border_radius=8)
        pygame.draw.rect(screen, (60, 60, 60), menu_area, 2, border_radius=8)

        buttons.clear()
        base_y = menu_area.y + 20
        for i, item in enumerate(menu_items):
            rect = pygame.Rect(menu_area.x + 20, base_y + i * (btn_h + 15), btn_w, btn_h)
            buttons.append(rect)
            hovered = rect.collidepoint(mouse_pos)
            draw_button(rect, item, hovered)

    elif current_view == "config":
        title = title_font.render("CONNECTION SETTINGS", True, WHITE)
        screen.blit(title, (80, 50))

        draw_input(ip_rect, f"IP: {host_ip}", active_input == "ip")
        draw_input(port_rect, f"PORT: {host_port}", active_input == "port")
        draw_button(back_rect, "Back", back_rect.collidepoint(mouse_pos))

    elif current_view == "video":
        title = title_font.render("PROMO VIDEO", True, WHITE)
        screen.blit(title, (80, 50))

        pygame.draw.rect(screen, (20, 20, 20), video_rect, border_radius=8)
        pygame.draw.rect(screen, (60, 60, 60), video_rect, 2, border_radius=8)

        if CV2_AVAILABLE and video_cap is not None and video_cap.isOpened():
            audio_ms = pygame.mixer.music.get_pos()
            if audio_ms < 0:
                audio_ms = 0

            # Sincronizar frame con el audio
            target_frame = int((audio_ms / 1000) * video_fps)
            if target_frame >= 0:
                video_cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

            ret, frame = video_cap.read()
            if not ret:
                # Fin: detener audio
                close_video()
                current_view = "menu"
            else:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                surface = pygame.image.frombuffer(frame.tobytes(), frame.shape[1::-1], "RGB")
                video_last_surface = pygame.transform.smoothscale(surface, (video_rect.width, video_rect.height))

            if video_last_surface is not None:
                screen.blit(video_last_surface, (video_rect.x, video_rect.y))

        draw_button(back_rect, "Back", back_rect.collidepoint(mouse_pos))

    elif current_view == "rules":
        title = title_font.render("RULES", True, WHITE)
        screen.blit(title, (80, 50))
        lines = [
            "1) The goal is to reach 21 without going over.",
            "2) Face cards are worth 10, Ace is 1 or 11.",
            "3) Dealer stands on 17.",
        ]
        y = 140
        for line in lines:
            screen.blit(font.render(line, True, WHITE), (80, y))
            y += 32

        draw_button(back_rect, "Back", back_rect.collidepoint(mouse_pos))

    pygame.display.update()
    clock.tick(FPS)
