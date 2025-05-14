import os
import ursina


class Wall(ursina.Entity):
    def __init__(self, position):
        super().__init__(
            position=position,
            scale=2,
            model="cube",
            texture=os.path.join("assets", "wall.png"),
            origin_y=-0.5
        )
        self.texture.filtering = None
        self.collider = ursina.BoxCollider(self, size=ursina.Vec3(1, 2, 1))

class Barrier(ursina.Entity):
    def __init__(self, position):
        super().__init__(
            position=position,
            scale=2,
            model="cube",
            texture=os.path.join("assets", "barrier.png"),
            origin_y=-0.5
        )
        self.texture.filtering = None
        self.collider = ursina.BoxCollider(self, size=ursina.Vec3(1, 2, 1))


class Map:
    def __init__(self):
        for y in range(1, 4, 2):
            Wall(ursina.Vec3(6, y, 0))
            Wall(ursina.Vec3(6, y, 2))
            Wall(ursina.Vec3(6, y, 4))
            Wall(ursina.Vec3(6, y, 6))
            Wall(ursina.Vec3(6, y, 8))

            Wall(ursina.Vec3(4, y, 8))
            Wall(ursina.Vec3(2, y, 8))
            Wall(ursina.Vec3(0, y, 8))
            Wall(ursina.Vec3(-2, y, 8))

        
        for y in range(1, 4, 2):
            for i in range(-40,40,2):
                Barrier(ursina.Vec3(-42,y,i))   
                Barrier(ursina.Vec3(40,y,i))
                Barrier(ursina.Vec3(i,y,-42))
                Barrier(ursina.Vec3(i,y,40))
                # Wall(ursina.Vec3(-24,y,i))
                # Wall(ursina.Vec3(22,y,i))
                # Wall(ursina.Vec3(i,y,-24))
                # Wall(ursina.Vec3(i,y,22))


        
