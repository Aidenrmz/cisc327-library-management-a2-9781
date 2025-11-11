# tests/test_payment_service_direct.py

from services.payment_service import PaymentGateway


def test_payment_gateway_process_payment_success():
    """
    Basic happy-path test for the simulated payment gateway.
    This exercises the main success branch of process_payment().
    """
    gateway = PaymentGateway()

    success, txn_id, message = gateway.process_payment(
        patron_id="123456",
        amount=10.0,
        description="Late fees",
    )

    assert success is True
    assert txn_id.startswith("txn_123456_")
    assert "Payment of $10.00 processed successfully" in message


def test_payment_gateway_refund_invalid_transaction():
    """
    Invalid transaction_id should be rejected and return an error message.
    This exercises one of the early guard clauses in refund_payment().
    """
    gateway = PaymentGateway()

    success, message = gateway.refund_payment(
        transaction_id="",   # invalid
        amount=5.0,
    )

    assert success is False
    assert message == "Invalid transaction ID"
