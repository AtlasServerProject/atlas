package io.atlas.api.commerce.service;

import io.atlas.api.commerce.model.CommerceModels.OrderView;
import io.atlas.api.payment.PaymentRepository;
import io.atlas.api.shared.error.ApiFailure;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OrderReceiptService {
    public record Receipt(OrderView order, List<PaymentRepository.ReceiptPayment> payments) {}
    private final OrderService orders;
    private final PaymentRepository payments;
    public OrderReceiptService(OrderService orders, PaymentRepository payments) {
        this.orders = orders;
        this.payments = payments;
    }
    @Transactional(readOnly = true)
    public Receipt receipt(UUID user, UUID id) {
        var order = orders.detail(user, id);
        var transactions = payments.receiptPayments(id);
        if (transactions.isEmpty()) throw new ApiFailure(HttpStatus.NOT_FOUND,
                "RECEIPT_NOT_AVAILABLE", "O comprovante estará disponível após a confirmação do pagamento.");
        return new Receipt(order, transactions);
    }
}
