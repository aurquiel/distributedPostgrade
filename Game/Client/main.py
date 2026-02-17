import pygame
import webbrowser
from pathlib import Path
from domain.Connection import Connection
from domain.Game import Game
from domain.Player import Player

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
TABLE_GREEN = (9, 82, 46)
PANEL_GREEN = (16, 110, 60)
HIGHLIGHT = (255, 215, 0)
FPS = 60
clock = pygame.time.Clock()
font = pygame.font.SysFont(["Arial", "Liberation Sans", "DejaVu Sans", "Sans"], 24)
title_font = pygame.font.SysFont(["Arial", "Liberation Sans", "DejaVu Sans", "Sans"], 32)
small_font = pygame.font.SysFont(["Arial", "Liberation Sans", "DejaVu Sans", "Sans"], 18)

# Window
screen = pygame.display.set_mode((WINDOWS_WIDTH, WINDOWS_HEIGHT))
pygame.display.set_caption("Cliente del Juego - Menú")
icon = pygame.image.load(str(Path(__file__).parent / "assets" / "blackjack.png"))
pygame.display.set_icon(icon)
menu_img = pygame.image.load(str(Path(__file__).parent / "assets" / "blackjack.png")).convert_alpha()
menu_img = pygame.transform.smoothscale(menu_img, (400, 400))

# UI state
runing = True
active_input = None
HOST_IP = "192.168.0.127"
HOST_PORT = "12345"
MAX_PLAYERS = 3

current_view = "menu"  # menu | config | video | rules
VIDEO_PATH = str(Path(__file__).parent / "assets" / "promo.mp4")
AUDIO_PATH = str(Path(__file__).parent / "assets" / "audio.mp3")

# Clases del juego
my_connection = Connection(HOST_IP, HOST_PORT)
my_game = Game(my_connection, MAX_PLAYERS)


# Buttons (menu)
menu_items = [
    "Iniciar Juego",
    "Ver Video Promocional",
    "Ver Reglas",
    "Configurar Conexión",
    "README"
]
menu_area = pygame.Rect(80, 120, 520, 520)
buttons = []
btn_w, btn_h = 480, 70

# Config panel
ip_rect = pygame.Rect(720, 260, 360, 50)
port_rect = pygame.Rect(720, 340, 360, 50)
back_rect = pygame.Rect(80, 710, 180, 50)
rules_back_rect = pygame.Rect(WINDOWS_WIDTH - 200, 50, 140, 44)
config_back_rect = pygame.Rect(WINDOWS_WIDTH - 200, 50, 140, 44)

# Video
video_rect = pygame.Rect(80, 140, 1040, 560)
video_cap = None
video_fps = 30
video_frame_ms = 33
video_last_tick = 0
video_last_surface = None
video_duration_ms = 0

# Cartas y UI de juego
CARD_SIZE = (90, 128)
card_cache = {}

def draw_outcome_banner(text, color):
    banner_width = 520
    banner_height = 80
    rect = pygame.Rect((WINDOWS_WIDTH - banner_width) // 2, 40, banner_width, banner_height)
    pygame.draw.rect(screen, (20, 20, 20), rect, border_radius=10)
    pygame.draw.rect(screen, color, rect, 3, border_radius=10)
    label = title_font.render(text, True, color)
    label_pos = label.get_rect(center=rect.center)
    screen.blit(label, label_pos)

saldo_input_rect = pygame.Rect(800, WINDOWS_HEIGHT - 150, 150, 44)
apuesta_input_rect = pygame.Rect(980, WINDOWS_HEIGHT - 150, 150, 44)
btn_recargar_rect = pygame.Rect(800, WINDOWS_HEIGHT - 92, 150, 44)
btn_apostar_rect = pygame.Rect(980, WINDOWS_HEIGHT - 92, 150, 44)
btn_plantarse_rect = pygame.Rect(80, WINDOWS_HEIGHT - 92, 150, 44)
btn_hit_rect = pygame.Rect(250, WINDOWS_HEIGHT - 92, 150, 44)
saldo_input_text = ""
apuesta_input_text = ""
active_input_game = None
error_back_rect = pygame.Rect((WINDOWS_WIDTH - 240) // 2, (WINDOWS_HEIGHT // 2) + 60, 240, 50)
btn_leave_rect = pygame.Rect(WINDOWS_WIDTH - 220, 20, 180, 44)

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

def get_card_surface(card_code):
    if not card_code:
        return None
    if card_code in card_cache:
        return card_cache[card_code]
    try:
        suit = card_code.split("-")[0]
        img_path = Path(__file__).parent / "assets" / "playing_cards" / suit / f"{card_code}.png"
        surf = pygame.image.load(str(img_path)).convert_alpha()
        surf = pygame.transform.smoothscale(surf, CARD_SIZE)
        card_cache[card_code] = surf
        return surf
    except Exception:
        return None

def draw_hand(cards, center_pos, label, real_name, balance, bet, has_turn=False, is_me=False, is_dealer=False):
    cx, cy = center_pos
    panel_width = 350
    panel_height = CARD_SIZE[1] + 180
    panel_rect = pygame.Rect(cx - panel_width // 2, cy - panel_height // 2, panel_width, panel_height)
    pygame.draw.rect(screen, PANEL_GREEN, panel_rect, border_radius=10)
    pygame.draw.rect(screen, (30, 150, 90), panel_rect, 2 if not has_turn else 4, border_radius=10)

    hand_value = 0
    if real_name == "Crupier":
        hand_value = my_game.calculate_hand_value()
    else:
        hand_value = my_game.get_player_hand_value_by_name(real_name)
    value_label = "-" if hand_value is None else str(hand_value)

    label_text = title_font.render(label, True, HIGHLIGHT if has_turn else WHITE)
    screen.blit(label_text, (panel_rect.x + 12, panel_rect.y + 8))

    if not is_dealer:
        balance_text = small_font.render(f"Saldo: {balance}", True, WHITE)
        bet_text = small_font.render(f"Apuesta: {bet}", True, WHITE)
        value_text = small_font.render(f"Valor: {value_label}", True, WHITE)
        screen.blit(balance_text, (panel_rect.x + 12, panel_rect.y + 46))
        screen.blit(bet_text, (panel_rect.x + 12, panel_rect.y + 70))
        screen.blit(value_text, (panel_rect.x + 12, panel_rect.y + 94))
    else:
        dealer_text = small_font.render("Crupier", True, WHITE)
        value_text = small_font.render(f"Valor: {value_label}", True, WHITE)
        screen.blit(dealer_text, (panel_rect.x + 12, panel_rect.y + 46))
        screen.blit(value_text, (panel_rect.x + 12, panel_rect.y + 70))

    if cards:
        card_w, card_h = CARD_SIZE
        spacing = max(4, int(card_w * 0.5))
        start_x = panel_rect.x + 20
        y_cards = panel_rect.y + panel_height - card_h - 20

        for idx, card in enumerate(cards):
            surf = get_card_surface(card)
            offset_x = start_x + idx * spacing
            if surf:
                screen.blit(surf, (offset_x, y_cards))
            else:
                placeholder = pygame.Rect(offset_x, y_cards, card_w, card_h)
                pygame.draw.rect(screen, BLACK, placeholder, border_radius=8)
                pygame.draw.rect(screen, WHITE, placeholder, 2, border_radius=8)
    
    if is_me and has_turn and hand_value == 21:
        my_game.send_command(f"\\z {my_game.get_player_name()}")


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
                            my_game.start_game()
                            current_view = "game"
                        elif idx == 1:
                            current_view = "video"
                            open_video()
                        elif idx == 2:
                            current_view = "rules"
                        elif idx == 3:
                            current_view = "config"
                        elif idx == 4:
                            webbrowser.open("https://github.com/aurquiel/DistributedBlackjack")

            elif current_view == "config":
                if config_back_rect.collidepoint(event.pos):
                    current_view = "menu"

            elif current_view in ("video", "rules"):
                target_back_rect = rules_back_rect if current_view == "rules" else back_rect
                if target_back_rect.collidepoint(event.pos):
                    if current_view == "video":
                        close_video()
                    current_view = "menu"

            elif current_view == "game":
                # Si hay error de conexión, solo permitir regresar al menú
                if my_game.connection_error or my_game.lost_connection:
                    if error_back_rect.collidepoint(event.pos):
                        current_view = "menu"
                    continue

                if saldo_input_rect.collidepoint(event.pos):
                    active_input_game = "saldo"
                elif apuesta_input_rect.collidepoint(event.pos):
                    active_input_game = "apuesta"
                else:
                    active_input_game = None

                if my_game.is_my_turn:
                    main_player = my_game.get_player_by_name(my_connection.unique_name)
                    has_cards = bool(main_player and main_player.hand)
                    has_two_cards = bool(main_player and len(main_player.hand) == 2)
                    dealer_has_one_card = len(my_game.cards_on_table) == 1

                    if btn_recargar_rect.collidepoint(event.pos) and saldo_input_text.strip():
                        my_game.send_command(f"\\m {my_game.get_player_name()} {saldo_input_text}")
                    if dealer_has_one_card and has_two_cards:
                        if has_cards and btn_apostar_rect.collidepoint(event.pos):
                            my_game.send_command(f"\\c {my_game.get_player_name()}")
                            my_game.send_command(f"\\z {my_game.get_player_name()}")
                    else:
                        if btn_apostar_rect.collidepoint(event.pos) and apuesta_input_text.strip() and main_player:
                            if float(apuesta_input_text) <= main_player.get_balance():
                                my_game.send_command(f"\\a {my_game.get_player_name()} {apuesta_input_text}")
                                my_game.send_command(f"\\z {my_game.get_player_name()}")
                            else:
                                my_game.info_message = "No tienes suficiente saldo para esta apuesta."
                    if has_cards and btn_plantarse_rect.collidepoint(event.pos):
                        my_game.send_command(f"\\z {my_game.get_player_name()}")
                    if has_cards and btn_hit_rect.collidepoint(event.pos):
                        my_game.send_command(f"\\h {my_game.get_player_name()}")

                # Botón abandonar partida (si hay conexión activa)
                if btn_leave_rect.collidepoint(event.pos):
                    my_game.send_command(f"\\u {my_game.get_player_name()}")
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
                    HOST_IP = HOST_IP[:-1]
                elif active_input == "port":
                    HOST_PORT = HOST_PORT[:-1]
            else:
                if active_input == "ip":
                    if len(event.unicode) == 1 and (event.unicode.isdigit() or event.unicode == "."):
                        HOST_IP += event.unicode
                elif active_input == "port":
                    if len(event.unicode) == 1 and event.unicode.isdigit():
                        HOST_PORT += event.unicode
            my_game.set_host_ip(HOST_IP)
            my_game.set_host_port(HOST_PORT)

        if event.type == pygame.KEYDOWN and current_view == "game" and active_input_game:
            target = saldo_input_text if active_input_game == "saldo" else apuesta_input_text
            if event.key == pygame.K_BACKSPACE:
                target = target[:-1]
            elif len(event.unicode) == 1 and event.unicode.isdigit() and len(target) < 4:
                target += event.unicode

            target = target[:4]  # Limitar a 4 caracteres para evitar números muy grandes

            if active_input_game == "saldo":
                saldo_input_text = target
            else:
                apuesta_input_text = target

    screen.fill((15, 15, 15))

    if current_view == "menu":
        title = title_font.render("MENÚ PRINCIPAL", True, WHITE)
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

        img_x, img_y = 700, 180
        screen.blit(menu_img, (img_x, img_y))
        label = title_font.render("21 BlackJack", True, WHITE)
        screen.blit(label, (img_x + 100, img_y + menu_img.get_height() + 12))

    elif current_view == "config":
        title = title_font.render("CONFIGURAR CONEXIÓN", True, WHITE)
        screen.blit(title, (80, 50))

        draw_input(ip_rect, f"IP: {HOST_IP}", active_input == "ip")
        draw_input(port_rect, f"PORT: {HOST_PORT}", active_input == "port")
        draw_button(config_back_rect, "Volver", config_back_rect.collidepoint(mouse_pos))

    elif current_view == "video":
        title = title_font.render("VIDEO PROMOCIONAL", True, WHITE)
        screen.blit(title, (80, 50))

        pygame.draw.rect(screen, (20, 20, 20), video_rect, border_radius=8)
        pygame.draw.rect(screen, (60, 60, 60), video_rect, 2, border_radius=8)

        if CV2_AVAILABLE and video_cap is not None and video_cap.isOpened():
            audio_ms = pygame.mixer.music.get_pos()
            if audio_ms < 0:
                audio_ms = 0

            target_frame = int((audio_ms / 1000) * video_fps)
            if target_frame >= 0:
                video_cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

            ret, frame = video_cap.read()
            if not ret:
                close_video()
                current_view = "menu"
            else:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                surface = pygame.image.frombuffer(frame.tobytes(), frame.shape[1::-1], "RGB")
                video_last_surface = pygame.transform.smoothscale(surface, (video_rect.width, video_rect.height))

            if video_last_surface is not None:
                screen.blit(video_last_surface, (video_rect.x, video_rect.y))

        draw_button(back_rect, "Volver", back_rect.collidepoint(mouse_pos))

    elif current_view == "rules":
        title = title_font.render("REGLAS", True, WHITE)
        screen.blit(title, (80, 50))
        lines = [
            "1) El objetivo es llegar a 21 sin pasarse.",
            "2) Las figuras J, K , Q valen 10; el As vale 1 u 11. Las demas cartas valen su numero.",
            "3) El crupier se planta entre 17 o 21.",
            "4) Si empatas, recuperas tu apuesta; si ganas, la duplicas.",
            "5) Para apostar primero deberas recargar tu saldo, luego apostar y finalmente plantarte o pedir carta.",
            "6) Puedes doblar tu apuesta solo con dos cartas.",
            "7) El juego inicia con tres jugadores.",
            "  ",
            "--- Flujo de mensajes (alto nivel) ---",
            "\\n unirse; \\f lleno; \\y partida activa.",
            "\\a apuesta \\c doblar apuesta; \\x otorgar turno; \\h pedir carta; \\z fin de turno.",
            "Tras \\z de todos, crupier juega (\\s cartas del crupier, \\v valor de la mano del crupier)",
            "resultado \\w gana jugador, \\g empate, \\l pierde jugador.",
            "\\b limpia mesa para la siguiente ronda.",
            "  ",
            "--- Autoridad del servidor ---",
            "El servidor valida apuestas y saldo",
            "El servidor reparte cartas, asigna turnos (\\x) y calcula resultados.",
            "Los clientes solo muestran el estado recibido y envían comandos;",
            "La fuente de verdad siempre es el servidor central.",
        ]
        y = 140
        for line in lines:
            screen.blit(small_font.render(line, True, WHITE), (80, y))
            y += 32

        draw_button(rules_back_rect, "Volver", rules_back_rect.collidepoint(mouse_pos))

    elif current_view == "game":
        screen.fill(TABLE_GREEN)

        # Partida llena: mostrar mensaje y opción de volver
        if my_game.server_full and not my_game.acepted_in_game:
            msg = title_font.render(my_game.error_message or "Servidor Full", True, (255, 120, 120))
            msg_rect = msg.get_rect(center=(WINDOWS_WIDTH // 2, WINDOWS_HEIGHT // 2 - 40))
            screen.blit(msg, msg_rect)

            sub = font.render("Serás devuelto al menú", True, WHITE)
            sub_rect = sub.get_rect(center=(WINDOWS_WIDTH // 2, WINDOWS_HEIGHT // 2))
            screen.blit(sub, sub_rect)

            draw_button(error_back_rect, "Volver al menú", error_back_rect.collidepoint(mouse_pos))
            pygame.display.update()
            clock.tick(FPS)
            continue

        if my_game.connection_error or my_game.lost_connection:
            msg = my_game.error_message or "Error de conexión"
            info = title_font.render(msg, True, (255, 120, 120))
            info_rect = info.get_rect(center=(WINDOWS_WIDTH // 2, WINDOWS_HEIGHT // 2 - 40))
            screen.blit(info, info_rect)

            sub = font.render("Serás devuelto al menú", True, WHITE)
            sub_rect = sub.get_rect(center=(WINDOWS_WIDTH // 2, WINDOWS_HEIGHT // 2))
            screen.blit(sub, sub_rect)

            draw_button(error_back_rect, "Volver al menú", error_back_rect.collidepoint(mouse_pos))
            pygame.display.update()
            clock.tick(FPS)
            continue

        if not my_game.acepted_in_game:
            title = title_font.render("Conectando al juego...", True, WHITE)
            screen.blit(title, (80, 50))
        elif my_game.acepted_in_game and not my_game.gameready:
            title = title_font.render("Esperando a los demás jugadores", True, WHITE)
            screen.blit(title, (80, 50))
            players_text = f"Jugadores conectados: {len(my_game.players)} / {my_game.MAX_PLAYERS}"
            screen.blit(font.render(players_text, True, WHITE), (80, 100))
            if my_game.info_message:
                warn = font.render(my_game.info_message, True, (255, 140, 140))
                screen.blit(warn, (80, 140))
        else:
            # Botón abandonar partida (visible en juego)
            draw_button(btn_leave_rect, "Abandonar", btn_leave_rect.collidepoint(mouse_pos))

            dealer_center = (WINDOWS_WIDTH // 2, 180)
            main_center = (WINDOWS_WIDTH // 2, WINDOWS_HEIGHT - 200)
            left_center = (220, 400)
            right_center = (WINDOWS_WIDTH - 220, 400)

            main_player = my_game.get_player_by_name(my_connection.unique_name)
            other_players = [p for p in my_game.players if p.name != my_connection.unique_name]

            draw_hand(
                my_game.cards_on_table,
                dealer_center,
                "Crupier",
                "Crupier",
                balance="-",
                bet="-",
                has_turn=False,
                is_me=False,
                is_dealer=True,
            )

            if main_player:
                draw_hand(
                    main_player.hand,
                    main_center,
                    "Tú",
                    main_player.name,
                    balance=main_player.get_balance(),
                    bet=main_player.get_bet_balance(),
                    has_turn=my_game.is_my_turn,
                    is_me=True,
                )

            if other_players:
                p_left = other_players[0]
                draw_hand(
                    p_left.hand,
                    left_center,
                    "Jugador 2",
                    p_left.name,
                    balance=p_left.get_balance(),
                    bet=p_left.get_bet_balance(),
                    has_turn=p_left.get_has_turn(),
                )
            if len(other_players) > 1:
                p_right = other_players[1]
                draw_hand(
                    p_right.hand,
                    right_center,
                    "Jugador 3",
                    p_right.name,
                    balance=p_right.get_balance(),
                    bet=p_right.get_bet_balance(),
                    has_turn=p_right.get_has_turn(),
                )

            if my_game.info_message:
                # Mensaje informativo (ej: saldo insuficiente)
                info_color = (255, 140, 140)
                info_lbl = small_font.render(my_game.info_message, True, info_color)
                screen.blit(info_lbl, (80, WINDOWS_HEIGHT - 190))

            if my_game.is_my_turn:
                main_player = my_game.get_player_by_name(my_connection.unique_name)
                has_cards = bool(main_player and main_player.hand)
                has_two_cards = bool(main_player and len(main_player.hand) == 2)
                dealer_has_one_card = len(my_game.cards_on_table) == 1

                draw_input(saldo_input_rect, f"Saldo: {saldo_input_text}", active_input_game == "saldo")
                if not (dealer_has_one_card and has_two_cards):
                    draw_input(apuesta_input_rect, f"Apuesta: {apuesta_input_text}", active_input_game == "apuesta")

                draw_button(btn_recargar_rect, "Recargar", btn_recargar_rect.collidepoint(mouse_pos))
                if dealer_has_one_card and has_two_cards:
                    draw_button(btn_apostar_rect, "Doblar Apuesta", btn_apostar_rect.collidepoint(mouse_pos))
                else:
                    draw_button(btn_apostar_rect, "Apostar", btn_apostar_rect.collidepoint(mouse_pos))

                if has_cards:
                    draw_button(btn_plantarse_rect, "Plantarse", btn_plantarse_rect.collidepoint(mouse_pos))
                    draw_button(btn_hit_rect, "Pedir Carta", btn_hit_rect.collidepoint(mouse_pos))

            estado_turno = "Tu turno" if my_game.is_my_turn else "Esperando turno"
            turn_text = font.render(estado_turno, True, WHITE)
            screen.blit(turn_text, (80, WINDOWS_HEIGHT - 160))

            if main_player and len(main_player.hand) > 0:
                if my_game.win_game:
                    draw_outcome_banner(f"¡Ganaste! Nuevo saldo: {main_player.get_balance()}", (50, 200, 50))
                elif my_game.lose_game:
                    draw_outcome_banner(f"Perdiste. Saldo: {main_player.get_balance()}", (200, 50, 50))
                elif my_game.tide_game:
                    draw_outcome_banner(f"Empate. Saldo: {main_player.get_balance()}", (200, 180, 50))

    pygame.display.update()
    clock.tick(FPS)