# pylint: disable=no-member

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .chapa import verify_chapa_payment
from .models import Payment, PaymentStatus
from .payment_service import finalize_payment_from_verify


class ChapaWebhookAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        expected_secret = settings.CHAPA_WEBHOOK_SECRET
        if expected_secret:
            provided_secret = (
                request.headers.get("Chapa-Signature")
                or request.headers.get("X-Chapa-Signature")
                or ""
            )
            if provided_secret != expected_secret:
                raise ValidationError({"detail": "Invalid webhook signature."})

        tx_ref = request.data.get("tx_ref") or request.data.get("data", {}).get("tx_ref")
        if not tx_ref:
            raise ValidationError({"tx_ref": "Missing tx_ref in webhook payload."})

        payment = Payment.objects.filter(tx_ref=tx_ref).select_related("ticket").first()
        if payment is None:
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

        if payment.status == PaymentStatus.PAID:
            return Response({"detail": "Payment already finalized."}, status=status.HTTP_200_OK)

        verify_response = verify_chapa_payment(tx_ref)
        result = finalize_payment_from_verify(payment, verify_response)
        if result == "paid":
            return Response({"detail": "Payment verified."}, status=status.HTTP_200_OK)
        if result == "pending":
            return Response({"detail": "Payment still pending."}, status=status.HTTP_200_OK)
        return Response({"detail": "Payment failed."}, status=status.HTTP_200_OK)
