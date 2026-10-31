package io.atlas.api.commerce.controller;

import io.atlas.api.auth.model.SessionIdentity;
import io.atlas.api.commerce.service.OrderReceiptService;
import java.util.UUID;
import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@RestController
public class OrderReceiptController {
    private final OrderReceiptService receipts;
    public OrderReceiptController(OrderReceiptService receipts) { this.receipts = receipts; }
    @GetMapping("/api/v1/orders/{id}/receipt")
    public ResponseEntity<OrderReceiptService.Receipt> receipt(
            @AuthenticationPrincipal SessionIdentity user, @PathVariable UUID id) {
        return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(receipts.receipt(user.id(), id));
    }
}
