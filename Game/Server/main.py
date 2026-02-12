import pygame
from pathlib import Path
from domain.Connection import Connection
from domain.Game import Game
from domain.Deck import Deck
from domain.Player import Player

pygame.init()

#=========CONTANTS GAME=========
WINDOWS_WIDTH = 900
WINDOWS_HEIGHT = 600
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
FPS = 15
clock = pygame.time.Clock()
font = pygame.font.SysFont(["Arial", "Liberation Sans", "DejaVu Sans", "Sans"], 22)
title_font = pygame.font.SysFont(["Arial", "Liberation Sans", "DejaVu Sans", "Sans"], 18)
MAX_PLAYERS = 3
HOST_PORT = 12345

#create a game window 
display_surface = pygame.display.set_mode((WINDOWS_WIDTH, WINDOWS_HEIGHT))
pygame.display.set_caption("21 Black Jack Game SERVER")
icon = pygame.image.load(str(Path(__file__).parent / "assets" / "blackjack.png"))
pygame.display.set_icon(icon)

#=========MAIN=========

server_events = []

my_connection = Connection(MAX_PLAYERS, HOST_PORT)
my_deck = Deck()
my_game = Game(my_deck, my_connection, MAX_PLAYERS, server_events)

runing = True
game_started = False
while runing: #Aqui va pygame
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            runing = False
            my_game.end_game()
            break

    if not game_started:
        my_game.start_game()
        game_started = True

    HOST_IP = my_connection.get_host_ip()
    HOST_PORT = my_connection.get_host_port()

    #Fill the surface
    display_surface.fill(BLACK)

    # ---- Paneles superiores ----
    panel_bg = (25, 25, 25)
    panel_border = (80, 80, 80)

    host_rect = pygame.Rect(20, 20, 420, 70)
    port_rect = pygame.Rect(460, 20, 420, 70)
    
    pygame.draw.rect(display_surface, panel_bg, host_rect)
    pygame.draw.rect(display_surface, panel_bg, port_rect)

    pygame.draw.rect(display_surface, panel_border, host_rect, 2)
    pygame.draw.rect(display_surface, panel_border, port_rect, 2)

    host_title = title_font.render("HOST", True, WHITE)
    port_title = title_font.render("PUERTO", True, WHITE)

    host_value = font.render(f"{HOST_IP if HOST_IP else 'N/A'}", True, WHITE)
    port_value = font.render(f"{HOST_PORT if HOST_PORT else 'N/A'}", True, WHITE)

    display_surface.blit(host_title, (host_rect.x + 10, host_rect.y + 8))
    display_surface.blit(host_value, (host_rect.x + 10, host_rect.y + 32))

    display_surface.blit(port_title, (port_rect.x + 10, port_rect.y + 8))
    display_surface.blit(port_value, (port_rect.x + 10, port_rect.y + 32))

    # ---- Panel de eventos ----
    events_rect = pygame.Rect(20, 110, 860, 470)
    pygame.draw.rect(display_surface, panel_bg, events_rect)
    pygame.draw.rect(display_surface, panel_border, events_rect, 2)

    events_title = title_font.render("EVENTOS EN EL SERVIDOR", True, WHITE)
    display_surface.blit(events_title, (events_rect.x + 10, events_rect.y + 8))

    # Mostrar últimos N eventos
    max_events = 16
    start_y = events_rect.y + 35
    for i, msg in enumerate(server_events[-max_events:]):
        line = font.render(f"- {msg}", True, WHITE)
        display_surface.blit(line, (events_rect.x + 10, start_y + i * 26))

    #Update the display
    pygame.display.update()
    clock.tick(FPS)
