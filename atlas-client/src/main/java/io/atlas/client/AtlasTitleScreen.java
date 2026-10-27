package io.atlas.client;

import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.*;
import net.minecraft.client.gui.screens.multiplayer.JoinMultiplayerScreen;
import net.minecraft.client.gui.screens.worldselection.SelectWorldScreen;
import net.minecraft.client.gui.screens.options.OptionsScreen;
import net.minecraft.client.multiplayer.ServerData;
import net.minecraft.client.multiplayer.resolver.ServerAddress;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;

/** Real responsive menu controls, independent of the illustration. */
public final class AtlasTitleScreen extends Screen {
 private static final ResourceLocation BACKGROUND=ResourceLocation.fromNamespaceAndPath("atlas-interface","textures/gui/main-menu.png");
 private static final ResourceLocation LOGO=ResourceLocation.fromNamespaceAndPath("atlas-interface","textures/gui/atlas-logo.png");
 private int top,logoSize,buttonWidth,buttonX,buttonY,buttonHeight,gap;
 private int ticks;
 public AtlasTitleScreen(){super(Component.literal("Atlas Cobblemon"));}
 @Override protected void init(){
  logoSize=height<220?26:Math.max(32,Math.min(76,height/5));buttonHeight=height<230?16:22;gap=height<230?3:5;
  int header=height<260?44:60;
  int total=logoSize+header+4*buttonHeight+3*gap;
  top=Math.max(8,(height-32-total)/2);buttonWidth=Math.min(224,Math.max(140,width-64));buttonX=(width-buttonWidth)/2;buttonY=top+logoSize+header;
  addRenderableWidget(new MenuButton(buttonX,buttonY,buttonWidth,buttonHeight,"JOGAR AGORA",true,()->{
   if(!minecraft.allowsMultiplayer()){minecraft.setScreen(new AlertScreen(()->minecraft.setScreen(this),Component.literal("Multiplayer indisponível"),Component.literal("Confira as permissões de multiplayer da sua conta Minecraft.")));return;}
   ConnectScreen.startConnecting(this,minecraft,ServerAddress.parseString("stapling-gpo.tun.ply.gg"),new ServerData("Atlas Cobblemon","stapling-gpo.tun.ply.gg",ServerData.Type.OTHER),false,null);
  }));
  var servers=new MenuButton(buttonX,buttonY+buttonHeight+gap,buttonWidth,buttonHeight,"SERVIDORES",false,()->minecraft.setScreen(new JoinMultiplayerScreen(this)));servers.active=minecraft.allowsMultiplayer();addRenderableWidget(servers);
  addRenderableWidget(new MenuButton(buttonX,buttonY+2*(buttonHeight+gap),buttonWidth,buttonHeight,"OPÇÕES",false,()->minecraft.setScreen(new OptionsScreen(this,minecraft.options))));
  addRenderableWidget(new MenuButton(buttonX,buttonY+3*(buttonHeight+gap),buttonWidth,buttonHeight,"SAIR",false,()->minecraft.stop()));
  addRenderableWidget(new MenuButton(10,height-24,86,16,"Singleplayer",false,()->minecraft.setScreen(new SelectWorldScreen(this))));
 }
 @Override public void tick(){ticks++;}
 @Override public boolean shouldCloseOnEsc(){return false;}
 @Override public void renderBackground(GuiGraphics g,int mx,int my,float delta){}
 @Override public void render(GuiGraphics g,int mx,int my,float delta){
  // Crop-to-cover keeps the environment proportional at widescreen/ultrawide ratios.
  float scale=Math.max(width/1672f,height/941f);int bw=(int)Math.ceil(1672*scale),bh=(int)Math.ceil(941*scale);
  g.blit(BACKGROUND,(width-bw)/2,(height-bh)/2,0f,0f,bw,bh,bw,bh);
  g.fill(0,0,width,height,0x38020C1B);
  int cx=width/2;
  g.fill(cx-buttonWidth/2-18,top-5,cx+buttonWidth/2+18,buttonY+4*(buttonHeight+gap),0x50102032);
  // Thin frame and cut corner details echo the supplied reference.
  int edge=10;int cyan=0xAA3DA7C9;
  g.fill(edge,edge,width-edge,edge+1,cyan);g.fill(edge,height-edge-1,width-edge,height-edge,cyan);
  g.fill(edge,edge,edge+1,height-edge,cyan);g.fill(width-edge-1,edge,width-edge,height-edge,cyan);
  for(int i=0;i<10;i++){g.fill(edge+i,edge+10-i,edge+i+2,edge+12-i,0xFF77EAFF);g.fill(width-edge-i-2,edge+10-i,width-edge-i,edge+12-i,0xFF77EAFF);}
  // Reuse the authentic Atlas logo; preserve its artwork and original aspect ratio.
  g.blit(LOGO,cx-logoSize/2,top,0f,0f,logoSize,logoSize,logoSize,logoSize);
  float textScale=height<260?2.3f:3.2f;g.pose().pushPose();g.pose().translate(cx,top+logoSize+6,0);g.pose().scale(textScale,textScale,1);
  g.drawCenteredString(font,"ATLAS",0,0,0xFFEAFCFF);g.pose().popPose();
  String tagline="SUA PRÓXIMA AVENTURA COMEÇA AQUI";
  float small=Math.min(1f,(width-40f)/Math.max(1,font.width(tagline)));g.pose().pushPose();g.pose().translate(cx,top+logoSize+(height<260?27:37),0);g.pose().scale(small,small,1);g.drawCenteredString(font,tagline,0,0,0xFFD6F7FF);g.pose().popPose();
  g.fill(cx-65,buttonY-6,cx+65,buttonY-5,0x8871DFF5);
  // Sparse deterministic particles; no allocations, downloads or gameplay changes.
  {for(int i=0;i<22;i++){
   int px=Math.floorMod(i*83+17,Math.max(1,width-24))+12;int py=Math.floorMod((int)(i*47-(ticks+delta)*(.10+i%3*.035)),Math.max(1,height-26))+13;
   if(Math.abs(px-cx)>buttonWidth/2+12)g.fill(px,py,px+1,py+1,0x886EE6FF);
  }}
  g.drawString(font,"Atlas Interface 1.1.0",Math.max(110,width-font.width("Atlas Interface 1.1.0")-14),height-18,0xFF87ACBF,false);
  super.render(g,mx,my,delta);
 }
 private static final class MenuButton extends net.minecraft.client.gui.components.Button {
  private final boolean primary;
  MenuButton(int x,int y,int w,int h,String label,boolean primary,Runnable action){super(x,y,w,h,Component.literal(label),b->action.run(),DEFAULT_NARRATION);this.primary=primary;}
  @Override protected void renderWidget(GuiGraphics g,int mx,int my,float delta){
   boolean hover=isHoveredOrFocused()&&active;int border=active?(hover?0xFFBDFAFF:0xFF3EA9C8):0xFF344D5F;
   if(primary){g.fill(getX()-2,getY()-2,getX()+width+2,getY()+height+2,hover?0x665CF1FF:0x334BDAFF);g.fill(getX(),getY(),getX()+width,getY()+height,hover?0xFF8DF4FF:0xFF49D9F0);}
   else g.fill(getX(),getY(),getX()+width,getY()+height,hover?0xF0214F69:0xDA07192C);
   g.fill(getX(),getY(),getX()+width-4,getY()+1,border);g.fill(getX(),getY(),getX()+1,getY()+height,border);g.fill(getX()+1,getY()+height-1,getX()+width,getY()+height,border);g.fill(getX()+width-1,getY()+4,getX()+width,getY()+height,border);
   for(int i=0;i<4;i++)g.fill(getX()+width-5+i,getY()+i,getX()+width-3+i,getY()+i+1,border);
   g.drawCenteredString(net.minecraft.client.Minecraft.getInstance().font,getMessage(),getX()+width/2,getY()+(height-8)/2,!active?0xFF8195A4:primary?0xFF052033:0xFFEAFBFF);
  }
 }
}
