package io.atlas.client;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.network.chat.Component;
public final class AtlasButton extends Button {
 public AtlasButton(int x,int y,int w,int h,Component text,OnPress press){super(x,y,w,h,text,press,DEFAULT_NARRATION);}
 @Override protected void renderWidget(GuiGraphics g,int mx,int my,float delta){
  int edge=active?(isHoveredOrFocused()?0xFF9DF5FF:0xFF36869C):0xFF324354;
  int bg=active?(isHoveredOrFocused()?0xFF24536B:0xFF17374F):0xFF132337;
  g.fill(getX(),getY(),getX()+width,getY()+height,edge);g.fill(getX()+1,getY()+1,getX()+width-1,getY()+height-1,bg);
  g.drawCenteredString(Minecraft.getInstance().font,getMessage(),getX()+width/2,getY()+(height-8)/2,active?0xFFDFFAFF:0xFF829BAD);
 }
}
