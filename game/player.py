import ursina
from thirdpersoncontroller import FirstPersonController
from weapon import Weapon


class Player(FirstPersonController):
    def __init__(self, position: ursina.Vec3):
        super().__init__(
            position=position,
            model="cube",
            jump_height=2.5,
            jump_duration=0.4,
            origin_y=-2,
            collider="box",
            speed=7
        )
        self.cursor.color = ursina.color.rgba(255, 0, 0, 122)

        self.inventory = [Weapon("base"), Weapon("second", color=ursina.color.color(0.4, 0, 0))]

        self.hand = 0

        self.healthbar_pos = ursina.Vec2(0, 0.45)
        self.healthbar_size = ursina.Vec2(0.8, 0.04)
        self.healthbar_bg = ursina.Entity(
            parent=ursina.camera.ui,
            model="quad",
            color=ursina.color.rgb(255, 0, 0),
            position=self.healthbar_pos,
            scale=self.healthbar_size
        )
        self.healthbar = ursina.Entity(
            parent=ursina.camera.ui,
            model="quad",
            color=ursina.color.rgb(0, 255, 0),
            position=self.healthbar_pos,
            scale=self.healthbar_size
        )

        self.bullets_text_pos = ursina.Vec2(0.75, -0.45)
        self.bullets_text = ursina.Text(
            text = '20/20', 
            parent=ursina.camera.ui,
            position=self.bullets_text_pos, 
            scale=2.35
        )
        
        # Визуальный индикатор для BHOP
        self.bhop_indicator = ursina.Text(
            text='', 
            parent=ursina.camera.ui,
            position=ursina.Vec2(0, -0.35), 
            scale=1.5,
            color=ursina.color.rgb(100, 255, 100)
        )

        self.health = 100
        self.death_message_shown = False

        self.reloading = False

    def death(self):
        self.death_message_shown = True

        for i in self.inventory:
            ursina.destroy(i)
        self.rotation = 0
        self.camera_pivot.world_rotation_x = -45
        self.world_position = ursina.Vec3(0, 7, -35)
        self.cursor.color = ursina.color.rgba(0, 0, 0, 0)

        ursina.Text(
            text="You are dead!",
            origin=ursina.Vec2(0, 0),
            scale=3
        )

    def update(self):
        weapon = self.inventory[self.hand]
        self.bullets_text.text = f"{weapon.bullets}/{weapon.bulletsMax}"
        self.healthbar.scale_x = self.health / 100 * self.healthbar_size.x
        
        # Показываем информацию о BHOP
        if self.bhop_active:
            boost = min(self.bhop_boost + (self.consecutive_bhops * 0.1), self.max_bhop_boost)
            self.bhop_indicator.text = f"BHOP x{boost:.1f}"
            self.bhop_indicator.color = ursina.color.rgb(
                int(255 * min(1, boost/2)), 
                int(255 * (1 - min(1, (boost-1)/1))), 
                0
            )
        else:
            remaining_time = self.bhop_window - (ursina.time.time() - self.landing_time)
            if self.grounded and remaining_time > 0:
                self.bhop_indicator.text = f"BHOP READY {remaining_time:.2f}s"
                self.bhop_indicator.color = ursina.color.yellow
            else:
                self.bhop_indicator.text = ""
        
        for i in range(len(self.inventory)):
            weapon = self.inventory[i]
            if self.hand == i:
                weapon.enabled = True
            else:
                weapon.enabled = False

        if self.health <= 0 and not self.death_message_shown:
            self.death()
        else:
            super().update()
    
    def toggle_crouch(self):
        # Toggle crouch state
        if self.camera_pivot.y == self.height:
            self.camera_pivot.y = self.height * 0.75
        else:
            # Check if there's room to stand up
            head_ray = ursina.raycast(self.position+ursina.Vec3(0,self.height*0.75,0), self.up, 
                             distance=self.height * 0.25,
                             traverse_target=self.traverse_target, ignore=self.ignore_list)
            if not head_ray.hit:
                self.camera_pivot.y = self.height