package io.atlas.client;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientLifecycleEvents;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.screen.v1.ScreenEvents;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.client.gui.screens.PauseScreen;
import net.minecraft.client.gui.screens.inventory.ContainerScreen;

public final class AtlasClient implements ClientModInitializer {
 public void onInitializeClient(){
  ClientLifecycleEvents.CLIENT_STARTED.register(AtlasWindowIcon::apply);
  ClientTickEvents.END_CLIENT_TICK.register(client->{
   if(client.screen instanceof TitleScreen){client.setScreen(new AtlasTitleScreen());return;}
   if(client.player!=null && client.screen instanceof ContainerScreen screen && screen.getTitle().getString().startsWith("Atlas Mart • ") && screen.getMenu().slots.size()==90){
    client.setScreen(new AtlasShopScreen(screen.getMenu(),screen.getTitle()));
   }
  });
  ScreenEvents.AFTER_INIT.register((client,screen,w,h)->{
   if(screen instanceof net.minecraft.client.gui.screens.DisconnectedScreen) AtlasConnectionDiagnostic.report(screen.getNarrationMessage().getString());
   if(screen instanceof PauseScreen)
    ScreenEvents.afterRender(screen).register((s,g,mx,my,delta)->{
     g.fill(0,0,s.width,25,0xE6101B30);g.fill(0,24,s.width,25,0xFF52DEF2);
     g.drawCenteredString(client.font,"ATLAS COBBLEMON",s.width/2,5,0xFF6FE7FF);
     g.fill(0,s.height-15,s.width,s.height,0xE6101B30);
     g.drawCenteredString(client.font,"Explore • Capture • Conquiste",s.width/2,s.height-11,0xFFB4CBE2);
    });
  });
 }
}
