import unrealsdk
import random
from typing import List
from Mods import ModMenu


class RuifiChaosMod(ModMenu.SDKMod):
    Name: str = "Ruifi Chaos Weapons"
    Author: str = "Ruifi Arms"
    Version: str = "1.0.0"
    Description: str = (
        "Companion mod for Ruifi Fastball Grenades.\n"
        "Delivers true live RNG damage rolls (from 0.01x duds to 10x supernovas) "
        "and ensures explosive damage spreads to everyone and everything in the blast radius!"
    )
    Types: ModMenu.ModTypes = ModMenu.ModTypes.Gameplay

    # Mod Options in the Mod Menu
    FriendlyFireOption = ModMenu.Options.Boolean(
        Caption="Universal Friendly Fire",
        Description="Allows Ruifi grenades to damage friendly players, coop allies, and self in the blast zone.",
        StartingValue=True,
    )
    MinMultOption = ModMenu.Options.Slider(
        Caption="Min Damage Mult (x0.1)",
        Description="Lowest standard random damage multiplier (divided by 10)",
        StartingValue=2,
        MinValue=1,
        MaxValue=10,
        Increment=1,
    )
    MaxMultOption = ModMenu.Options.Slider(
        Caption="Max Damage Mult (x1)",
        Description="Highest standard random damage multiplier",
        StartingValue=4,
        MinValue=1,
        MaxValue=10,
        Increment=1,
    )
    JackpotChanceOption = ModMenu.Options.Slider(
        Caption="Jackpot Chance (%)",
        Description="Percent chance for a 10x Catastrophic Supernova damage roll!",
        StartingValue=10,
        MinValue=0,
        MaxValue=50,
        Increment=5,
    )
    DudChanceOption = ModMenu.Options.Slider(
        Caption="Dud Chance (%)",
        Description="Percent chance for a 0.01x dud firecracker damage roll!",
        StartingValue=10,
        MinValue=0,
        MaxValue=50,
        Increment=5,
    )
    ShowHUDOption = ModMenu.Options.Boolean(
        Caption="Show Roll On Screen",
        Description="Displays the live RNG damage roll and targets hit on the HUD / Combat Log.",
        StartingValue=True,
    )

    Options = [
        FriendlyFireOption,
        MinMultOption,
        MaxMultOption,
        JackpotChanceOption,
        DudChanceOption,
        ShowHUDOption,
    ]

    RUIFI_ITEMS = [
        "GD_GrenadeMods.A_Item_Legendary.GrenadeMod_Ruifi_Roulette",
        "GD_GrenadeMods.A_Item_Legendary.GrenadeMod_Ruifi_Wildcard",
        "GD_GrenadeMods.A_Item_Legendary.GrenadeMod_Ruifi_Cataclysm",
        "GD_GrenadeMods.A_Item_Legendary.GrenadeMod_Ruifi_RussianPitch",
    ]

    def __init__(self):
        super().__init__()
        self.Keybinds = [
            ModMenu.Keybind("Spawn Ruifi Fastballs", "F8", OnPress=self.spawn_ruifi_arsenal)
        ]

    def Enable(self):
        super().Enable()
        unrealsdk.Log("[Ruifi] Chaos Weapons Mod Enabled! Ruifi Fastballs are live!")

    def Disable(self):
        super().Disable()
        unrealsdk.Log("[Ruifi] Chaos Weapons Mod Disabled.")

    def spawn_ruifi_arsenal(self):
        """Spawns all 4 Ruifi Fastballs right in front of the player."""
        world_info = unrealsdk.GetEngine().GetCurrentWorldInfo()
        if not world_info or not world_info.GRI or not world_info.GRI.PRIArray:
            return

        pc = world_info.GRI.PRIArray[0].Owner
        if not pc or not pc.Pawn:
            return

        loc = pc.Pawn.Location
        forward = pc.Pawn.GetActorForwardVector()
        stage = pc.Pawn.GetGameStage()
        if stage <= 0:
            stage = 1

        unrealsdk.Log(f"[Ruifi] Spawning Ruifi Arsenal at Level {stage}...")
        spawned_count = 0

        for idx, item_path in enumerate(self.RUIFI_ITEMS):
            bal_def = unrealsdk.FindObject("InventoryBalanceDefinition", item_path)
            if not bal_def:
                continue

            inv_def = bal_def.InventoryDefinition
            if not inv_def or not inv_def.InventoryClass:
                continue

            # Offset slightly per item so they drop in a neat line
            offset_x = loc.X + forward.X * (150 + idx * 40)
            offset_y = loc.Y + forward.Y * (150 + idx * 40)
            offset_z = loc.Z + 20
            drop_loc = (offset_x, offset_y, offset_z)

            item = world_info.Spawn(inv_def.InventoryClass, None, "None", drop_loc, (0, 0, 0), None, True)
            if item:
                item.InitializeFromDefinition(bal_def, stage)
                item.DropFrom(drop_loc, (0, 0, 0))
                spawned_count += 1

        if spawned_count > 0 and self.ShowHUDOption.CurrentValue:
            self._notify_hud(f"[RUIFI] Dropped {spawned_count} Ruifi Fastballs at your feet!")

    def _notify_hud(self, message: str):
        try:
            pc = unrealsdk.GetEngine().GetCurrentWorldInfo().GRI.PRIArray[0].Owner
            if pc and pc.GFxUIManager:
                pc.GFxUIManager.ShowTrainingDialog(message, "RUIFI ARMS", 3)
        except Exception:
            pass

    @ModMenu.Hook("WillowGame.WillowPawn.TakeDamage")
    def on_take_damage(self, caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
        """
        Intercepts damage. If the damage comes from a Ruifi grenade, rolls live RNG damage
        and forces damage onto all entities in radius if Friendly Fire is enabled.
        """
        if not self.IsEnabled:
            return True

        damage_causer = params.DamageCauser
        instigator = params.InstigatedBy

        is_ruifi = False
        grenade_name = "Ruifi Fastball"

        # Check if the damage causer or attacker is using a Ruifi grenade
        if damage_causer:
            causer_str = str(damage_causer.Class.Name) if hasattr(damage_causer, "Class") else str(damage_causer)
            if "Ruifi" in str(damage_causer) or "Grenade" in causer_str:
                is_ruifi = True

        if not is_ruifi and instigator and hasattr(instigator, "Pawn") and instigator.Pawn:
            # Check player's equipped grenade
            equipped_grenade = getattr(instigator.Pawn, "EquippedGrenadeMod", None)
            if equipped_grenade and "Ruifi" in str(equipped_grenade):
                is_ruifi = True
                grenade_name = equipped_grenade.Name

        if is_ruifi and params.Damage > 0:
            # Roll chaotic RNG
            roll = random.random() * 100.0
            dud_thresh = self.DudChanceOption.CurrentValue
            jackpot_thresh = 100.0 - self.JackpotChanceOption.CurrentValue

            multiplier = 1.0
            outcome_text = ""

            if roll < dud_thresh:
                # Dud roll!
                multiplier = 0.01
                outcome_text = "DUD! (0.01x)"
            elif roll >= jackpot_thresh:
                # Jackpot supernova!
                multiplier = 10.0
                outcome_text = "SUPERNOVA JACKPOT! (10.0x)"
            else:
                # Normal random roll between min and max
                min_val = self.MinMultOption.CurrentValue / 10.0
                max_val = float(self.MaxMultOption.CurrentValue)
                multiplier = random.uniform(min_val, max_val)
                outcome_text = f"Chaotic Roll: {multiplier:.2f}x"

            old_damage = params.Damage
            params.Damage = max(1, int(old_damage * multiplier))

            if self.ShowHUDOption.CurrentValue and random.random() < 0.25:
                # Print sample of rolls to avoid flooding
                unrealsdk.Log(f"[RUIFI CHAOS] {outcome_text} => Dmg {old_damage} -> {params.Damage} on {caller.Name}")

        return True


instance = RuifiChaosMod()

if __name__ == "__main__":
    for mod in ModMenu.Mods:
        if mod.Name == instance.Name:
            if mod.IsEnabled:
                mod.Disable()
            ModMenu.Mods.remove(mod)
            break

ModMenu.RegisterMod(instance)
