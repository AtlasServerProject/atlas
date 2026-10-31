import io.atlas.modules.moderation.repository.StaffNotesRepository;
import io.atlas.modules.moderation.service.StaffNotesPolicy;
import io.atlas.modules.moderation.service.StaffModePolicy;
import java.sql.*;
import java.util.*;

public final class StaffNotesRepositoryTest {
    static void check(boolean condition, String message) { if (!condition) throw new AssertionError(message); }
    static void rejects(Runnable action) {
        try { action.run(); } catch (IllegalArgumentException expected) { return; }
        throw new AssertionError("Expected rejection");
    }
    public static void main(String[] args) throws Exception {
        String url = System.getenv("ATLAS_TEST_JDBC");
        UUID actor = UUID.randomUUID();
        long note;
        try (Connection c = DriverManager.getConnection(url, "postgres", "")) {
            try (var s = c.createStatement()) {
                s.execute("INSERT INTO players(id,uuid,username) VALUES (1,'00000000-0000-0000-0000-000000000001','Target'), (2,'00000000-0000-0000-0000-000000000002','Other')");
            }
            var repo = new StaffNotesRepository(() -> c);
            note = repo.add(1, actor, "Moderator", "Observação: jogador cooperou; 'aspas' e Unicode ✓");
            check(repo.list(1, 1, false).getFirst().text().contains("'aspas'"), "Text round trip");
            check(repo.list(2, 1, true).isEmpty(), "Player isolation");
            check(!repo.archive(2, note, actor, "Moderator", "wrong target"), "Cannot archive another target's ID");
            check(repo.archive(1, note, null, "CONSOLE", "Informação corrigida"), "Archive succeeds");
            check(!repo.archive(1, note, actor, "Moderator", "overwrite"), "Archive is immutable");
            check(repo.list(1, 1, false).isEmpty(), "Archive hidden from active list");
            var history = repo.list(1, 1, true);
            check(history.size() == 2, "Archive preserves both events");
            check(history.stream().anyMatch(r -> r.type().equals("NOTA_ARQUIVADA") && r.actor().equals("CONSOLE") && r.text().equals("Informação corrigida")), "Archive attribution/reason");
            for (int i = 0; i < 11; i++) repo.add(2, null, "CONSOLE", "Note " + i);
            // Force equal timestamps: pagination must still use the unique ID as tie-breaker.
            try (var s = c.createStatement()) { s.execute("UPDATE staff_notes SET created_at='2026-01-01' WHERE target_player_id=2"); }
            var ids = new HashSet<Long>();
            for (int page = 1; page <= 3; page++) {
                var rows = repo.list(2, page, false);
                check(rows.size() == (page == 3 ? 1 : 6), "Lookahead pagination");
                rows.stream().limit(5).forEach(r -> check(ids.add(r.id()), "No duplicate pages"));
            }
            check(ids.size() == 11 && repo.list(2,4,false).isEmpty(), "All notes reachable");
            rejects(() -> repo.list(1,0,true));
            rejects(() -> repo.list(1,Integer.MAX_VALUE,true));
            try (var s = c.createStatement()) {
                s.execute("INSERT INTO moderation_punishments(type,target_player_id,target_name,actor_name,reason,expires_at,revoked_at,revoked_by_name,revoked_reason) VALUES ('WARN',1,'OldName','Admin','Aviso',NULL,NULL,NULL,NULL), ('MUTE',1,'OldName','Admin','Flood',NOW()+INTERVAL '1 day',NOW(),'Owner','Revisado'), ('MUTE',1,'OldName','Admin','Expirado',NOW()-INTERVAL '1 day',NULL,NULL,NULL), ('BAN',1,'OldName','Admin','Ban ativo',NULL,NULL,NULL,NULL), ('BAN_IP',NULL,'127.0.0.1','Admin','IP privado',NULL,NULL,NULL,NULL)");
                s.execute("UPDATE players SET username='Renamed' WHERE id=1");
            }
            var all = new ArrayList<io.atlas.modules.moderation.model.StaffRecord>();
            for (int page=1; page<=2; page++) repo.list(1,page,true).stream().limit(5).forEach(all::add);
            check(all.size()==7, "Notes and punishments survive rename; IP-only ban excluded");
            check(all.stream().anyMatch(r -> r.type().equals("WARN") && r.status().equals("registrada")), "Warn is an event, not active restriction");
            check(all.stream().anyMatch(r -> r.type().equals("MUTE") && r.status().equals("expirada")), "Expired punishment");
            check(all.stream().anyMatch(r -> r.type().equals("BAN") && r.status().equals("ativa")), "Active ban");
            check(all.stream().anyMatch(r -> r.type().equals("REVOGACAO_MUTE") && r.actor().equals("Owner") && r.text().equals("Revisado")), "Revocation actor/reason");
        }
        try (Connection c = DriverManager.getConnection(url, "postgres", "")) {
            check(new StaffNotesRepository(() -> c).list(1,1,true).size()==6, "Fresh connection persistence");
        }
        check(StaffNotesPolicy.mayAccess(true,false,false,0,100), "Console access");
        check(StaffNotesPolicy.mayAccess(false,true,true,100,10), "Staff higher rank");
        check(!StaffNotesPolicy.mayAccess(false,false,true,100,10), "Unauthenticated denied");
        check(!StaffNotesPolicy.mayAccess(false,true,false,100,10), "Non-staff denied");
        check(!StaffNotesPolicy.mayAccess(false,true,true,100,100), "Equal rank denied");
        check(!StaffNotesPolicy.mayAccess(false,true,true,10,100), "Higher target denied");
        check(StaffNotesPolicy.text("  válida  ").equals("válida"), "Trim text");
        check(StaffNotesPolicy.text("a".repeat(500)).length()==500, "Max length");
        for (String value : Arrays.asList(null," ","a".repeat(501),"linha\nquebrada","§cspoof","x\u202Ey")) rejects(() -> StaffNotesPolicy.text(value));
        check(StaffModePolicy.allows("/staffnotes add Target nota"), "Notes in StaffMode");
        check(StaffModePolicy.allows("history Target 2"), "History in StaffMode");
        check(!StaffModePolicy.allows("historyevil Target"), "No prefix bypass");
        System.out.println("PASS: Staff Notes persistence, archive, pagination, history, permissions and validation");
    }
}
