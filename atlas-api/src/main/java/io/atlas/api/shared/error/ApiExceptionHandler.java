package io.atlas.api.shared.error;

import io.atlas.api.shared.web.RequestIdFilter;
import jakarta.servlet.http.HttpServletRequest;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.resource.NoResourceFoundException;

@RestControllerAdvice
public class ApiExceptionHandler {
    private static final Logger LOGGER = LoggerFactory.getLogger(ApiExceptionHandler.class);

    @ExceptionHandler(ApiFailure.class)
    ResponseEntity<ApiError> business(ApiFailure failure, HttpServletRequest request) {
        return response(request, failure.status(), failure.code(), failure.getMessage(), List.of());
    }
    @ExceptionHandler(MethodArgumentNotValidException.class)
    ResponseEntity<ApiError> validation(MethodArgumentNotValidException exception, HttpServletRequest request) {
        var fields = exception.getBindingResult().getFieldErrors().stream()
            .map(error -> new ApiError.FieldError(error.getField(), "Valor inválido.")).toList();
        return response(request, HttpStatus.UNPROCESSABLE_CONTENT, "VALIDATION_ERROR", "Confira os campos informados.", fields);
    }
    @ExceptionHandler(HttpMessageNotReadableException.class)
    ResponseEntity<ApiError> malformed(HttpServletRequest request) {
        return response(request, HttpStatus.BAD_REQUEST, "MALFORMED_REQUEST", "Requisição inválida.", List.of());
    }
    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    ResponseEntity<ApiError> method(HttpServletRequest request) {
        return response(request, HttpStatus.METHOD_NOT_ALLOWED, "METHOD_NOT_ALLOWED", "Método não permitido.", List.of());
    }
    @ExceptionHandler(org.springframework.web.method.annotation.MethodArgumentTypeMismatchException.class)
    ResponseEntity<ApiError> invalidParameter(HttpServletRequest request) {
        return response(request, HttpStatus.BAD_REQUEST, "INVALID_PARAMETER", "Parâmetro inválido.", List.of());
    }
    @ExceptionHandler(NoResourceFoundException.class)
    ResponseEntity<ApiError> missing(HttpServletRequest request) {
        return response(request, HttpStatus.NOT_FOUND, "NOT_FOUND", "Recurso não encontrado.", List.of());
    }
    @ExceptionHandler(org.springframework.dao.DataIntegrityViolationException.class)
    ResponseEntity<ApiError> conflict(HttpServletRequest request) {
        return request.getRequestURI().contains("catalog") || request.getRequestURI().contains("/admin/")
            ? response(request, HttpStatus.CONFLICT, "CATALOG_CONFLICT", "Já existe um produto com este identificador ou uma promoção neste intervalo.", List.of())
            : response(request, HttpStatus.CONFLICT, "RESOURCE_CONFLICT", "Os dados mudaram durante a operação. Atualize a página e confira o resultado.", List.of());
    }
    @ExceptionHandler(DataAccessException.class)
    ResponseEntity<ApiError> database(HttpServletRequest request) {
        LOGGER.error("Database operation unavailable");
        return response(request, HttpStatus.SERVICE_UNAVAILABLE, "DEPENDENCY_UNAVAILABLE", "Serviço temporariamente indisponível.", List.of());
    }
    @ExceptionHandler(Exception.class)
    ResponseEntity<ApiError> unexpected(HttpServletRequest request) {
        // Do not log exception text: JDBC/validation exceptions can contain private input.
        LOGGER.error("Unexpected API failure");
        return response(request, HttpStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "Não foi possível concluir a operação.", List.of());
    }
    private ResponseEntity<ApiError> response(HttpServletRequest request, HttpStatus status,
                                              String code, String message, List<ApiError.FieldError> fields) {
        return ResponseEntity.status(status).body(new ApiError(code, message,
            (String) request.getAttribute(RequestIdFilter.ATTRIBUTE), fields));
    }
}
