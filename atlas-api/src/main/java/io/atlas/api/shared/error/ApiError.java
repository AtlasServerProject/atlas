package io.atlas.api.shared.error;

import java.util.List;

public record ApiError(String code, String message, String requestId, List<FieldError> fieldErrors) {
    public record FieldError(String field, String message) { }
}
