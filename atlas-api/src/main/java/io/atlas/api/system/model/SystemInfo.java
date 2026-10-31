package io.atlas.api.system.model;

import java.time.Instant;

public record SystemInfo(String application, String version, String stage,
                         int schemaGeneration, Instant initializedAt, Instant serverTime) { }
