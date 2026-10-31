package io.atlas.client.mixin;
import net.minecraft.client.gui.Gui;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.world.scores.Objective;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
@Mixin(Gui.class)
public class AtlasScoreboardMixin {
 @Inject(method="displayScoreboardSidebar",at=@At("HEAD"))
 private void atlas$lower(GuiGraphics graphics,Objective objective,CallbackInfo ci){
  if(objective.getName().equals("atlas_hud")){graphics.pose().pushPose();graphics.pose().translate(0,32,0);}
 }
 @Inject(method="displayScoreboardSidebar",at=@At("RETURN"))
 private void atlas$restore(GuiGraphics graphics,Objective objective,CallbackInfo ci){
  if(objective.getName().equals("atlas_hud"))graphics.pose().popPose();
 }
}
