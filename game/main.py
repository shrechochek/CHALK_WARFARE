import os
import sys
import socket
import threading
import asyncio
import ursina
import time
import mouse
from network import Network

from floor import Floor
from map import Map
from player import Player
from enemy import Enemy
from bullet import Bullet


username = input("Enter your username: ")

while True:
    server_addr = input("Enter server IP: ")
    n = Network(server_addr, 8000, username)
    n.settimeout(5)

    error_occurred = False

    try:
        n.connect()
    except ConnectionRefusedError:
        print("\nConnection refused! This can be because server hasn't started or has reached it's player limit.")
        error_occurred = True
    except socket.timeout:
        print("\nServer took too long to respond, please try again...")
        error_occurred = True
    except socket.gaierror:
        print("\nThe IP address you entered is invalid, please try again with a valid address...")
        error_occurred = True
    finally:
        n.settimeout(None)

    if not error_occurred:
        break

app = ursina.Ursina()
ursina.window.borderless = False
ursina.window.title = "Ursina FPS"
ursina.window.exit_button.visible = False

floor = Floor()
map = Map()
sky = ursina.Entity(
    model="sphere",
    texture=os.path.join("assets", "sky.png"),
    scale=9999,
    double_sided=True
)
player = Player(ursina.Vec3(0, 1, 0))
prev_pos = player.world_position
prev_dir = player.world_rotation_y
enemies = []

# Reload indicator
reload_indicator = ursina.Entity(
    parent=ursina.camera.ui,
    model='circle',
    texture='white_cube',
    color=ursina.color.gray,
    scale=0.03,
    position=ursina.Vec2(0, 0),
    alpha=0.7
)
reload_indicator.visible = False

def update_reload_indicator(progress):
    """Update the reload indicator with current progress (0-1)"""
    if progress <= 0:
        reload_indicator.visible = False
    else:
        reload_indicator.visible = True
        reload_indicator.scale_x = 0.3 * progress
        reload_indicator.scale_y = 0.3 * progress

def receive():
    while True:
        try:
            info = n.receive_info()
        except Exception as e:
            print(e)
            continue

        if not info:
            print("Server has stopped! Exiting...")
            sys.exit()

        if info["object"] == "player":
            enemy_id = info["id"]

            if info["joined"]:
                new_enemy = Enemy(ursina.Vec3(*info["position"]), enemy_id, info["username"])
                new_enemy.health = info["health"]
                enemies.append(new_enemy)
                continue

            enemy = None

            for e in enemies:
                if e.id == enemy_id:
                    enemy = e
                    break

            if not enemy:
                continue

            if info["left"]:
                enemies.remove(enemy)
                ursina.destroy(enemy)
                continue

            enemy.world_position = ursina.Vec3(*info["position"])
            enemy.rotation_y = info["rotation"]

        elif info["object"] == "bullet":
            b_pos = ursina.Vec3(*info["position"])
            b_dir = info["direction"]
            b_x_dir = info["x_direction"]
            b_damage = info["damage"]
            new_bullet = Bullet(b_pos, b_dir, b_x_dir, n, b_damage, slave=True)
            ursina.destroy(new_bullet, delay=2)

        elif info["object"] == "health_update":
            enemy_id = info["id"]

            enemy = None

            if enemy_id == n.id:
                enemy = player
            else:
                for e in enemies:
                    if e.id == enemy_id:
                        enemy = e
                        break

            if not enemy:
                continue

            enemy.health = info["health"]

def update():
    if player.health > 0:
        global prev_pos, prev_dir

        if prev_pos != player.world_position or prev_dir != player.world_rotation_y:
            n.send_player(player)

        prev_pos = player.world_position
        prev_dir = player.world_rotation_y

        # Update reload indicator for current weapon
        weapon = player.inventory[player.hand]
        if weapon.reloadDelay > 0:
            progress = 1 - (weapon.reloadDelay / weapon.reloadDelayMax)
            update_reload_indicator(progress)
        else:
            update_reload_indicator(0)

def reload_weapon(weapon):
    """Handle weapon reloading in a separate thread"""
    weapon.reloading = True
    weapon.reloadDelay = weapon.reloadDelayMax
    
    while weapon.reloadDelay > 0:
        time.sleep(0.1)
        weapon.reloadDelay -= 0.1
        if weapon != player.inventory[player.hand]:  # If switched weapon
            weapon.reloading = False
            weapon.reloadDelay = weapon.reloadDelayMax
            # return
    
    weapon.bullets = weapon.bulletsMax
    weapon.reloading = False

def input(key):
    if key == "left mouse down" and player.health > 0:
        weapon = player.inventory[player.hand]
        if weapon.bullets > 0 and not weapon.reloading:
            b_pos = player.position + ursina.Vec3(0, 2, 0)
            weapon.bullets -= 1
            bullet = Bullet(b_pos, player.world_rotation_y, -player.camera_pivot.world_rotation_x, n)
            n.send_bullet(bullet)
            ursina.destroy(bullet, delay=2)
        if weapon.bullets <= 0 and not weapon.reloading:
            reload_thread = threading.Thread(target=reload_weapon, args=(weapon,), daemon=True)
            reload_thread.start()
            
    elif key in ["1", "2", "3", "4", "5"]:
        # Reset reload indicator when switching weapons
        update_reload_indicator(0)
        player.hand = int(key)-1
    elif key in ["c"]:
        player.toggle_crouch()
        

def main():
    msg_thread = threading.Thread(target=receive, daemon=True)
    msg_thread.start()
    app.run()

if __name__ == "__main__":
    main()