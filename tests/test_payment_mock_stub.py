# tests/test_payment_mock_stub.py

from unittest.mock import Mock
import pytest

from services.library_service import pay_late_fees, refund_late_fee_payment
from services.payment_service import PaymentGateway


# ============================
# Tests for pay_late_fees
# ============================

def test_pay_late_fees_successful_payment(mocker):
    """
    Happy path: late fee exists, payment gateway succeeds.
    - Stub DB functions (calculate_late_fee_for_book, get_book_by_id)
    - Mock payment_gateway.process_payment
    """

    # --- STUBS: fake database results ---
    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 5.0, "days_overdue": 3, "status": "ok"},
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"book_id": 1, "title": "Test Book"},
    )

    # --- MOCK: fake payment gateway object ---
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.return_value = (
        True,
        "txn_123",
        "Payment of $5.00 processed successfully",
    )

    # --- Call function under test ---
    success, message, transaction_id = pay_late_fees(
        patron_id="123456",
        book_id=1,
        payment_gateway=mock_gateway,
    )

    # --- Assertions on result ---
    assert success is True
    assert "Payment successful" in message
    assert "Payment of $5.00 processed successfully" in message
    assert transaction_id == "txn_123"

    # --- Verify mock interaction ---
    mock_gateway.process_payment.assert_called_once_with(
        patron_id="123456",
        amount=5.0,
        description="Late fees for 'Test Book'",
    )


def test_pay_late_fees_invalid_patron_does_not_call_gateway():
    """
    If patron_id is invalid, the payment gateway should NOT be called.
    No stubs needed because we fail early.
    """

    mock_gateway = Mock(spec=PaymentGateway)

    success, message, transaction_id = pay_late_fees(
        patron_id="123",  # invalid (not 6 digits)
        book_id=1,
        payment_gateway=mock_gateway,
    )

    assert success is False
    assert "Invalid patron ID" in message
    assert transaction_id is None

    # Verify that the payment gateway was never called
    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_payment_declined_by_gateway(mocker):
    """
    Gateway returns a declined payment.
    We still stub DB calls and mock the gateway, but the mock returns success=False.
    """

    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 7.5, "days_overdue": 5, "status": "ok"},
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"book_id": 2, "title": "Declined Book"},
    )

    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.return_value = (
        False,
        "",
        "Card declined",
    )

    success, message, transaction_id = pay_late_fees(
        patron_id="654321",
        book_id=2,
        payment_gateway=mock_gateway,
    )

    assert success is False
    assert message == "Payment failed: Card declined"
    assert transaction_id is None

    mock_gateway.process_payment.assert_called_once_with(
        patron_id="654321",
        amount=7.5,
        description="Late fees for 'Declined Book'",
    )


def test_pay_late_fees_zero_fee_does_not_call_gateway(mocker):
    """
    When the calculated late fee is zero or less, we should NOT call the gateway.
    """

    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 0.0, "days_overdue": 0, "status": "ok"},
    )
    # get_book_by_id is not needed here because we exit before using it

    mock_gateway = Mock(spec=PaymentGateway)

    success, message, transaction_id = pay_late_fees(
        patron_id="123456",
        book_id=1,
        payment_gateway=mock_gateway,
    )

    assert success is False
    assert "No late fees to pay" in message
    assert transaction_id is None

    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_handles_network_error_from_gateway(mocker):
    """
    If the payment gateway raises an exception (e.g. network error),
    pay_late_fees should catch it and return a safe error message.
    """

    mocker.patch(
        "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 5.0, "days_overdue": 2, "status": "ok"},
    )
    mocker.patch(
        "services.library_service.get_book_by_id",
        return_value={"book_id": 3, "title": "Network Book"},
    )

    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.process_payment.side_effect = Exception("Network error")

    success, message, transaction_id = pay_late_fees(
        patron_id="999999",
        book_id=3,
        payment_gateway=mock_gateway,
    )

    assert success is False
    assert "Payment processing error" in message
    assert "Network error" in message
    assert transaction_id is None

    mock_gateway.process_payment.assert_called_once_with(
        patron_id="999999",
        amount=5.0,
        description="Late fees for 'Network Book'",
    )


# ============================
# Tests for refund_late_fee_payment
# ============================

def test_refund_late_fee_payment_successful_refund():
    """
    Happy path: valid transaction ID and amount, gateway refund succeeds.
    """

    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = (
        True,
        "Refund of $5.00 processed successfully",
    )

    success, message = refund_late_fee_payment(
        transaction_id="txn_abc123",
        amount=5.0,
        payment_gateway=mock_gateway,
    )

    assert success is True
    assert "Refund of $5.00 processed successfully" in message

    mock_gateway.refund_payment.assert_called_once_with("txn_abc123", 5.0)


def test_refund_late_fee_payment_invalid_transaction_id_does_not_call_gateway():
    """
    Invalid transaction ID should be rejected before calling the payment gateway.
    """

    mock_gateway = Mock(spec=PaymentGateway)

    success, message = refund_late_fee_payment(
        transaction_id="abc123",  # does not start with "txn_"
        amount=5.0,
        payment_gateway=mock_gateway,
    )

    assert success is False
    assert message == "Invalid transaction ID."

    mock_gateway.refund_payment.assert_not_called()


@pytest.mark.parametrize(
    "amount, expected_message",
    [
        (-1.0, "Refund amount must be greater than 0."),
        (0.0, "Refund amount must be greater than 0."),
        (20.0, "Refund amount exceeds maximum late fee."),
    ],
)
def test_refund_late_fee_payment_invalid_amounts_do_not_call_gateway(amount, expected_message):
    """
    Negative, zero, or > $15 refund amounts should be rejected before calling the gateway.
    """

    mock_gateway = Mock(spec=PaymentGateway)

    success, message = refund_late_fee_payment(
        transaction_id="txn_valid_123",
        amount=amount,
        payment_gateway=mock_gateway,
    )

    assert success is False
    assert message == expected_message

    mock_gateway.refund_payment.assert_not_called()
