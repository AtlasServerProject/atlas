package io.atlas.api.mail;

import java.util.regex.Pattern;

/** Presentation only: tokens, expiry and delivery remain in their existing services. */
public final class MailTemplate {
    private static final Pattern LINK = Pattern.compile("https?://[^\\s<>\"']+/(?:verificar-email|redefinir-senha)#token=[A-Za-z0-9_-]+");
    private MailTemplate() {}
    private static String escape(String value) {
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("\"", "&quot;").replace("'", "&#39;");
    }
    public static String html(MailOutbox.Message message) {
        var match = LINK.matcher(message.text());
        String link = null;
        while (match.find()) link = match.group();
        if (link == null) return "<html lang=\"pt-BR\"><body><pre>" + escape(message.text()) + "</pre></body></html>";
        boolean verification = link.contains("/verificar-email#token=");
        String title = verification ? "Sua jornada começa aqui." : "Vamos recuperar seu acesso.";
        String action = verification ? "Confirmar meu email" : "Redefinir minha senha";
        String description = verification
            ? "Falta só confirmar seu email para deixar sua conta pronta. Clique no botão abaixo e conclua a confirmação no site do Atlas."
            : "Recebemos uma solicitação para redefinir sua senha. Clique no botão abaixo para escolher uma nova senha no site do Atlas.";
        String greeting = message.text().lines().findFirst().orElse("Olá.");
        return """
            <!doctype html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
            <body style="margin:0;padding:24px 12px;background:#07140f;font-family:Arial,sans-serif;color:#edf5ec">
              <table role="presentation" width="100%%" cellpadding="0" cellspacing="0"><tr><td align="center">
                <table role="presentation" width="100%%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#10251c;border:1px solid #314b36;border-radius:20px">
                  <tr><td style="padding:36px 28px">
                    <p style="margin:0 0 28px;color:#c9ef8d;font-size:12px;font-weight:bold;letter-spacing:3px">ATLAS COBBLEMON</p>
                    <h1 style="margin:0 0 24px;font-size:30px;line-height:1.2;color:#edf5ec">%s</h1>
                    <p style="line-height:1.7;color:#edf5ec">%s</p>
                    <p style="line-height:1.7;color:#c2d1c4">%s</p>
                    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:28px 0"><tr><td bgcolor="#c9ef8d" style="border-radius:10px">
                      <a href="%s" style="display:inline-block;padding:16px 24px;color:#102013;font-size:15px;font-weight:bold;text-decoration:none">%s</a>
                    </td></tr></table>
                    <p style="padding:16px;background:#182f23;border-radius:10px;color:#c2d1c4;font-size:13px;line-height:1.6">Este link é pessoal e só pode ser usado uma vez. Se não funcionar, solicite um novo email pelo site.</p>
                    <p style="color:#a9bcae;font-size:12px;line-height:1.6">Se o botão não abrir, copie este endereço e cole no navegador:</p>
                    <p style="word-break:break-all;font-size:12px;line-height:1.6"><a href="%s" style="color:#c9ef8d">%s</a></p>
                    <p style="margin-top:28px;color:#a9bcae;font-size:12px;line-height:1.6">Se você não solicitou esta ação, ignore esta mensagem.</p>
                  </td></tr>
                </table>
                <p style="color:#91a697;font-size:12px;line-height:1.6">Atlas Cobblemon · Seu próximo capítulo começa aqui.</p>
              </td></tr></table>
            </body></html>
            """.formatted(title, escape(greeting), description, escape(link), action, escape(link), escape(link));
    }
}
