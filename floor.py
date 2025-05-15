import os
import ursina
from PIL import Image
import numpy as np

class Floor:
    def __init__(self):
        self.ground = ursina.Entity(
            model='plane', 
            scale=(2030/4, 1, 830/4), 
            texture=os.path.join("assets", "map.png"), 
            texture_scale=(1,1), 
            collider='box'
        )
        self.generate_walls_from_map()

    def generate_walls_from_map(self):
        try:
            img = Image.open("game/assets/map.png").convert('RGB')  # RGB режим
            # img = Image.open("assets/map.png").convert('RGB')  # RGB режим
            img_array = np.array(img)
            map_width, map_height = img.size
            
            plane_width = 2030 / 4
            plane_depth = 830 / 4
            scale_x = plane_width / map_width
            scale_z = plane_depth / map_height
            
            # Проверка на чисто чёрный пиксель (0,0,0)
            is_black = np.all(img_array == [0, 0, 0], axis=2)
            
            # 1. Горизонтальные линии
            for y in range(map_height):
                x = 0
                while x < map_width:
                    if is_black[y, x]:
                        start_x = x
                        while x < map_width and is_black[y, x]:
                            x += 1
                        end_x = x - 1
                        
                        if end_x > start_x:  # Линия длиной >1 пикселя
                            center_x = (start_x + end_x) / 2
                            pos_x = (center_x - map_width/2) * scale_x
                            pos_z = -(y - map_height/2) * scale_z
                            
                            ursina.Entity(
                                model='cube',
                                position=(pos_x, 1, pos_z),
                                scale=((end_x - start_x + 1) * scale_x, 6, scale_z),
                                texture='wall.png',
                                collider='box',
                                color=ursina.color.rgb(30, 30, 50),
                                texture_scale = ((end_x - start_x + 1) * scale_x / 2, 6 / 2)
                            )
                    else:
                        x += 1
            
            # 2. Вертикальные линии
            for x in range(map_width):
                y = 0
                while y < map_height:
                    if is_black[y, x]:
                        start_y = y
                        while y < map_height and is_black[y, x]:
                            y += 1
                        end_y = y - 1
                        
                        if end_y > start_y:
                            center_y = (start_y + end_y) / 2
                            pos_x = (x - map_width/2) * scale_x
                            pos_z = -(center_y - map_height/2) * scale_z
                            
                            ursina.Entity(
                                model='cube',
                                position=(pos_x, 1, pos_z),
                                scale=(scale_x, 6, (end_y - start_y + 1) * scale_z),
                                texture='wall.png',
                                collider='box',
                                color=ursina.color.rgb(30, 30, 50),
                                texture_scale = ((end_x - start_x + 1) * scale_x / 2, 6 / 2)
                            )
                    else:
                        y += 1

        except Exception as e:
            print(f"Ошибка: {e}")