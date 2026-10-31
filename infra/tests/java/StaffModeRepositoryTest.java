import io.atlas.modules.moderation.model.StaffModeSession;
import io.atlas.modules.moderation.repository.StaffModeRepository;
import io.atlas.modules.moderation.service.StaffModePolicy;
import java.sql.DriverManager;
import java.util.UUID;

public final class StaffModeRepositoryTest {
    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
    public static void main(String[] args) throws Exception {
        try (var connection = DriverManager.getConnection(System.getenv("ATLAS_TEST_JDBC"), "postgres", "")) {
            var repo = new StaffModeRepository(() -> connection);
            var alice = new StaffModeSession(UUID.randomUUID(), "survival", "atlas:survival_emerald",
                    -33.5, 70, 20.5, 90, -10, false, false, false, false, true, 0.05f, 0.1f);
            var bob = new StaffModeSession(UUID.randomUUID(), "creative", "minecraft:the_nether",
                    100, 80, -100, 180, 0, true, true, true, true, true, 0.1f, 0.2f);
            check(repo.findActive(alice.uuid()).isEmpty(), "New UUID must have no session");
            check(repo.begin(alice), "Initial snapshot must be saved");
            check(repo.begin(bob), "Other player must be independent");
            check(repo.findActive(alice.uuid()).orElseThrow().equals(alice), "All state fields must round-trip");
            var replacement = new StaffModeSession(alice.uuid(), bob.gameMode(), bob.world(), bob.x(), bob.y(), bob.z(),
                    bob.yaw(), bob.pitch(), bob.mayFly(), bob.flying(), bob.invulnerable(), bob.instantBuild(), bob.mayBuild(), bob.flySpeed(), bob.walkSpeed());
            check(!repo.begin(replacement), "An active snapshot must never be overwritten");
            check(repo.findActive(alice.uuid()).orElseThrow().equals(alice), "Original restore point must survive repeated activation");
            // A fresh repository/connection simulates process restart.
            try (var fresh = DriverManager.getConnection(System.getenv("ATLAS_TEST_JDBC"), "postgres", "")) {
                check(new StaffModeRepository(() -> fresh).findActive(alice.uuid()).orElseThrow().equals(alice), "Recovery after restart");
            }
            repo.complete(alice.uuid());
            repo.complete(alice.uuid());
            check(repo.findActive(alice.uuid()).isEmpty(), "Completion must be idempotent");
            check(repo.findActive(bob.uuid()).orElseThrow().equals(bob), "Completion cannot affect another player");
            check(repo.begin(replacement), "A completed session permits new activation");
            check(repo.findActive(alice.uuid()).orElseThrow().equals(replacement), "New activation gets current state");
            try (var query = connection.createStatement(); var rows = query.executeQuery("SELECT count(*) FROM staff_mode_sessions")) {
                rows.next(); check(rows.getInt(1) == 2, "Only one session record per player");
            }
            for (String command : new String[]{"staffmode off", "/staff tp Tester", "  /INVSEE Tester", "freeze Tester", "msg Tester Oi", "logout", "atlasban Tester 1h test"})
                check(StaffModePolicy.allows(command), "Allowed command rejected: " + command);
            for (String command : new String[]{"give @s diamond", "minecraft:give @s diamond", "execute run give @s diamond", "kit diario", "sethome base", "pay Tester 10", "fly", "", "/staffmodeevil"})
                check(!StaffModePolicy.allows(command), "Gameplay/namespace bypass: " + command);
            check(!StaffModePolicy.allows(null), "Null command must fail closed");
            System.out.println("StaffMode: persistence, restart recovery, isolation, duplicate activation and command boundaries passed.");
        }
    }
}
