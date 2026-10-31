package io.atlas.client;

import com.mojang.logging.LogUtils;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.IntBuffer;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.client.Minecraft;
import org.lwjgl.BufferUtils;
import org.lwjgl.glfw.GLFW;
import org.lwjgl.glfw.GLFWImage;
import org.lwjgl.stb.STBImage;
import org.lwjgl.system.MemoryStack;

/** Sets the actual GLFW window icon, including the Windows taskbar entry. */
public final class AtlasWindowIcon {
    private AtlasWindowIcon() {}

    public static void apply(Minecraft client) {
        List<ByteBuffer> pixels = new ArrayList<>();
        try (MemoryStack stack = MemoryStack.stackPush()) {
            int[] sizes = {16, 32, 48, 256};
            GLFWImage.Buffer icons = GLFWImage.malloc(sizes.length, stack);
            for (int index = 0; index < sizes.length; index++) {
                String path = "/assets/atlas-interface/icons/icon_" + sizes[index] + ".png";
                byte[] png;
                try (InputStream stream = AtlasWindowIcon.class.getResourceAsStream(path)) {
                    if (stream == null) throw new IllegalStateException("Missing Atlas icon " + sizes[index]);
                    png = stream.readAllBytes();
                }
                ByteBuffer encoded = BufferUtils.createByteBuffer(png.length);
                encoded.put(png).flip();
                IntBuffer width = stack.mallocInt(1);
                IntBuffer height = stack.mallocInt(1);
                IntBuffer channels = stack.mallocInt(1);
                ByteBuffer decoded = STBImage.stbi_load_from_memory(encoded, width, height, channels, 4);
                if (decoded == null) throw new IllegalStateException("Invalid Atlas icon " + sizes[index]);
                pixels.add(decoded);
                icons.position(index).width(width.get(0)).height(height.get(0)).pixels(decoded);
            }
            icons.position(0);
            GLFW.glfwSetWindowIcon(client.getWindow().getWindow(), icons);
        } catch (Exception exception) {
            LogUtils.getLogger().warn("Could not apply Atlas window icon; keeping the default icon", exception);
        } finally {
            for (ByteBuffer decoded : pixels) STBImage.stbi_image_free(decoded);
        }
    }
}
