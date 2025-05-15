import ursina

class Weapon(ursina.Entity):
    def __init__(self, name: str, bulletsMax=20, reloadDelay=3, shootDelay=0.1, model="cube", texture="white_cube", scale=ursina.Vec3(0.1, 0.2, 0.65), rotation=ursina.Vec3(-20, -20, -5), color=ursina.color.color(0, 0, 0.4)):
        super().__init__(
            parent=ursina.camera.ui,  # важно для отображения в руках
            position=ursina.Vec2(0.6, -0.45),
            scale=scale,
            rotation=rotation,
            model=model,
            texture=texture,
            color=color
        )
        self.name = name
        self.bullets = bulletsMax
        self.bulletsMax = bulletsMax
        self.reloadDelay = reloadDelay
        self.reloadDelayMax = reloadDelay
        self.shootDelay = shootDelay
        self.reloading = False