package io.atlas.api.system.service;

import io.atlas.api.system.model.SystemInfo;
import io.atlas.api.system.repository.SystemMetadataRepository;
import java.time.Clock;
import org.springframework.boot.info.BuildProperties;
import org.springframework.stereotype.Service;

@Service
public class SystemService {
    private final SystemMetadataRepository repository;
    private final Clock clock;
    private final BuildProperties build;
    public SystemService(SystemMetadataRepository repository, Clock clock, BuildProperties build) {
        this.repository = repository;
        this.clock = clock;
        this.build = build;
    }
    public SystemInfo info() {
        var metadata = repository.read();
        return new SystemInfo("atlas-api", build.getVersion(), "M4_IDENTITY_ORDERS", metadata.schemaGeneration(), metadata.initializedAt(), clock.instant());
    }
}
