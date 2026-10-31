package io.atlas.client;

import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.*;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.gui.screens.inventory.MenuAccess;
import net.minecraft.network.chat.Component;
import net.minecraft.world.inventory.*;
import net.minecraft.world.item.*;
import net.minecraft.core.component.DataComponents;
import net.minecraft.world.item.component.ItemLore;
import java.util.*;

/** Client presentation only. Sends vanilla slot clicks to the existing server-owned menu. */
public final class AtlasShopScreen extends Screen implements MenuAccess<ChestMenu> {
 private final ChestMenu menu;
 private EditBox search,quantityInput;
 private final java.util.List<Button> presets=new ArrayList<>();
 private Button applyQuantity;
 private boolean selling=false,waiting=false;
 private int offset=0,x,y,w,h;
 private final java.util.List<Integer> visible=new ArrayList<>();
 private Button buyTab,sellTab,minus,plus,confirm,back,previous,next;
 private boolean confirmation(){return menu.getSlot(31).getItem().is(Items.EMERALD);}
 public AtlasShopScreen(ChestMenu menu,Component title){super(title);this.menu=menu;}
 public ChestMenu getMenu(){return menu;}
 protected void init(){
  w=Math.min(440,width-16);h=Math.min(290,height-16);x=(width-w)/2;y=(height-h)/2;
  search=new EditBox(font,x+12,y+58,w-24,18,Component.literal("Buscar item"));search.setMaxLength(64);search.setHint(Component.literal("Buscar item…"));search.setResponder(s->{offset=0;});addRenderableWidget(search);
  buyTab=button(x+12,y+31,100,"Comprar",()->{selling=false;offset=0;});
  sellTab=button(x+116,y+31,100,"Vender",()->{selling=true;offset=0;});
  back=button(x+12,y+h-30,72,"Voltar",()->click(45,0));
  previous=button(x+w-150,y+h-30,64,"Anterior",()->{if(confirmation())return;if(offset>0)offset=Math.max(0,offset-rows());else click(45,0);});
  next=button(x+w-80,y+h-30,64,"Próxima",()->{if(offset+rows()<visible.size())offset+=rows();else click(53,0);});
  quantityInput=new EditBox(font,x+14,y+h-98,48,20,Component.literal("Quantidade de 1 a 64"));
  quantityInput.setMaxLength(2);quantityInput.setFilter(v->v.matches("[0-9]{0,2}"));quantityInput.setValue("1");addRenderableWidget(quantityInput);
  applyQuantity=button(x+68,y+h-98,64,"Aplicar",()->sendQuantity(inputQuantity()));
  for(int i=0;i<4;i++){int amount=new int[]{1,16,32,64}[i];presets.add(button(x+138+i*48,y+h-98,44,String.valueOf(amount),()->sendQuantity(amount)));}
  minus=button(x+14,y+h-64,42,"−",()->sendQuantity(Math.max(1,inputQuantity()-1)));
  plus=button(x+62,y+h-64,42,"+",()->sendQuantity(Math.min(64,inputQuantity()+1)));
  confirm=button(x+w-160,y+h-64,144,"Confirmar",()->{sendQuantity(inputQuantity());waiting=true;click(31,0);});
 }
 private int inputQuantity(){try{return Math.max(1,Math.min(64,Integer.parseInt(quantityInput.getValue())));}catch(NumberFormatException e){return 1;}}
 private void sendQuantity(int count){
  if(waiting||!confirmation()||minecraft.player==null||minecraft.gameMode==null||minecraft.player.containerMenu!=menu)return;
  quantityInput.setValue(String.valueOf(count));
  minecraft.gameMode.handleInventoryButtonClick(menu.containerId,1000+count);
 }
 @Override public boolean keyPressed(int key,int scan,int modifiers){
  if(confirmation()&&quantityInput.isFocused()&&(key==257||key==335)){sendQuantity(inputQuantity());return true;}
  return super.keyPressed(key,scan,modifiers);
 }
 private Button button(int x,int y,int w,String text,Runnable action){return addRenderableWidget(new AtlasButton(x,y,w,20,Component.literal(text),b->action.run()));}
 private int rows(){return Math.max(1,(h-123)/27);}
 private void click(int slot,int button){if(minecraft.player!=null&&minecraft.gameMode!=null&&minecraft.player.containerMenu==menu)minecraft.gameMode.handleInventoryMouseClick(menu.containerId,slot,button,ClickType.PICKUP,minecraft.player);}
 private java.util.List<Component> lore(ItemStack s){return s.getOrDefault(DataComponents.LORE,new ItemLore(java.util.List.of())).lines();}
 private void filter(){visible.clear();String q=search.getValue().toLowerCase(Locale.ROOT);for(int i=0;i<45;i++){var s=menu.getSlot(i).getItem();if(!s.isEmpty()&&!s.is(Items.GRAY_STAINED_GLASS_PANE)&&s.getHoverName().getString().toLowerCase(Locale.ROOT).contains(q))visible.add(i);}offset=Math.min(offset,Math.max(0,visible.size()-1));}
 public void tick(){if(minecraft.player==null||minecraft.player.containerMenu!=menu)minecraft.setScreen(null);}
 // Screen.render invokes renderBackground before drawing widgets. Our panel is drawn
 // before those widgets, so suppress that second background/blur pass.
 @Override public void renderBackground(GuiGraphics g,int mx,int my,float delta) { }
 public void render(GuiGraphics g,int mx,int my,float delta){
  super.renderBackground(g,mx,my,delta);
  g.fill(0,0,width,height,0xB0081020);g.fill(x-1,y-1,x+w+1,y+h+1,0xFF365672);g.fill(x,y,x+w,y+h,0xFA101D32);g.fill(x,y,x+w,y+3,0xFF59E0EF);
  g.drawString(font,title,x+12,y+12,0xFF7AEAFF,false);
  boolean c=confirmation();search.visible=!c;buyTab.visible=!c;sellTab.visible=!c;previous.visible=!c;next.visible=!c;back.visible=c;minus.visible=c;plus.visible=c;confirm.visible=c;confirm.active=!waiting;
  quantityInput.visible=c;applyQuantity.visible=c;applyQuantity.active=!waiting;
  for(var preset:presets){preset.visible=c;preset.active=!waiting;}
  minus.active=!waiting;plus.active=!waiting;
  buyTab.active=selling;sellTab.active=!selling;
  if(!c){filter();int max=Math.min(visible.size(),offset+rows());for(int row=offset;row<max;row++){
    int sy=y+82+(row-offset)*27;var s=menu.getSlot(visible.get(row)).getItem();boolean hover=mx>=x+12&&mx<x+w-12&&my>=sy&&my<sy+25;
    g.fill(x+12,sy,x+w-12,sy+25,hover?0xFF254A65:0xFF172C44);g.renderItem(s,x+18,sy+4);
    g.drawString(font,font.plainSubstrByWidth(s.getHoverName().getString(),w-165),x+42,sy+4,0xFFE7F3FF,false);
    var lines=lore(s);if(lines.size()>(selling?1:0))g.drawString(font,font.plainSubstrByWidth(lines.get(selling?1:0).getString(),w-65),x+42,sy+14,0xFFB8D4E5,false);
   }
   if(visible.isEmpty())g.drawCenteredString(font,"Nenhum item encontrado",width/2,y+95,0xFFB8D4E5);
  }else{
   var s=menu.getSlot(22).getItem();g.renderItem(s,x+20,y+55);g.drawString(font,s.getHoverName(),x+46,y+59,0xFFE7F3FF,false);
   int lineY=y+85;for(var line:lore(s)){g.drawString(font,font.plainSubstrByWidth(line.getString(),w-28),x+14,lineY,0xFFB8D4E5,false);lineY+=14;}
   if(waiting)g.drawString(font,"Processando no servidor…",x+14,y+h-116,0xFF7AEAFF,false);
  }
  var balance=lore(menu.getSlot(49).getItem());if(!balance.isEmpty())g.drawString(font,font.plainSubstrByWidth(balance.getFirst().getString(),w-190),x+12,y+h-14,0xFFB8D4E5,false);
  super.render(g,mx,my,delta);
 }
 public boolean mouseClicked(double mx,double my,int button){
  if(!confirmation()&&button==0&&mx>=x+12&&mx<x+w-12&&my>=y+82&&my<y+82+rows()*27){int i=offset+(int)(my-y-82)/27;if(i<visible.size()){click(visible.get(i),selling?1:0);return true;}}
  return super.mouseClicked(mx,my,button);
 }
 public boolean mouseScrolled(double mx,double my,double horizontal,double vertical){if(!confirmation()){offset=Math.max(0,Math.min(Math.max(0,visible.size()-rows()),offset+(vertical<0?1:-1)));return true;}return super.mouseScrolled(mx,my,horizontal,vertical);}
 public void onClose(){if(minecraft.player!=null)minecraft.player.closeContainer();super.onClose();}
 public boolean isPauseScreen(){return false;}
}
